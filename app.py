from dotenv import load_dotenv
from flask import Flask, jsonify, request, current_app, render_template
import os
import time
import hashlib
import hmac
import datetime
import jwt
import psycopg2
from functools import wraps

import qa_report
from ratelimit import RateLimiter
from repositories import (
    categories as categories_repo,
    orders as orders_repo,
    products as products_repo,
    users as users_repo,
)


load_dotenv()


def hash_password(password):
    salt = os.getenv("PASSWORD_SALT", "mgstreet_salt").encode("utf-8")
    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000)
    return derived.hex()


def verify_password(password, hashed_password):
    salt = os.getenv("PASSWORD_SALT", "mgstreet_salt").encode("utf-8")
    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000)
    return hmac.compare_digest(derived.hex(), hashed_password)


def calculate_cart_total(items):
    """Soma price * quantity dos itens do carrinho, ignorando itens malformados."""
    total = 0
    for item in items:
        try:
            total += float(item.get("price", 0)) * int(item.get("quantity", 1))
        except (TypeError, ValueError):
            continue
    return total


def serialize_products(rows):
    """Converte linhas de produto (id, name, description, price, image_url, category)."""
    return [
        {
            "id": row[0],
            "name": row[1],
            "description": row[2],
            "price": float(row[3]) if row[3] is not None else None,
            "image_url": row[4],
            "category": row[5],
            "options": row[6] if len(row) > 6 else {},
        }
        for row in rows
    ]


def token_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "Token não fornecido."}), 401

        token = auth_header.split(" ", 1)[1]
        try:
            payload = jwt.decode(
                token,
                current_app.config["JWT_SECRET"],
                algorithms=["HS256"],
            )
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expirado."}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Token inválido."}), 401

        return f(payload, *args, **kwargs)

    return decorated_function


def admin_required(f):
    @wraps(f)
    @token_required
    def decorated(payload, *args, **kwargs):
        if payload.get("role") != "admin":
            return jsonify({"error": "Acesso admin necessário."}), 403
        return f(payload, *args, **kwargs)

    return decorated


def init_db_connection(app):
    base_config = {
        "dbname": app.config["POSTGRES_DB"],
        "user": app.config["POSTGRES_USER"],
        "password": app.config["POSTGRES_PASSWORD"],
        "port": int(os.getenv("POSTGRES_PORT", 5432)),
    }

    configured_host = app.config["POSTGRES_HOST"]
    host_candidates = []
    for host in (configured_host, "localhost", "127.0.0.1", "db"):
        if host not in host_candidates:
            host_candidates.append(host)

    last_error = None
    for host in host_candidates:
        db_config = dict(base_config)
        db_config["host"] = host

        masked = dict(db_config)
        if masked.get("password"):
            masked["password"] = "***"
        app.logger.info("Tentando conectar ao Postgres com config: %s", masked)

        for attempt in range(1, 11):
            try:
                conn = psycopg2.connect(**db_config)
                conn.autocommit = True
                app.db_conn = conn
                app.logger.info("PostgreSQL conectado com sucesso em %s:%s.", host, db_config["port"])
                return
            except Exception as exc:
                last_error = exc
                app.logger.warning(
                    "Tentativa %s/10 falhou ao conectar no Postgres em %s:%s: %s",
                    attempt,
                    host,
                    db_config["port"],
                    exc,
                )
                if attempt < 10:
                    time.sleep(3)

    app.logger.error("Falha ao conectar ao Postgres após várias tentativas: %s", last_error)
    app.logger.error(
        "Verifique se o serviço PostgreSQL está ativo e se as variáveis em .env estão corretas."
    )
    raise last_error


def create_users_table(app):
    with app.db_conn.cursor() as cursor:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user' CHECK (role IN ('admin', 'user')),
                created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
            );
            """
        )
        admin_email = os.getenv("ADMIN_EMAIL", "admin@mgstreet.com")
        admin_password_hash = hash_password(os.getenv("ADMIN_PASSWORD", "admin"))
        cursor.execute(
            """
            INSERT INTO users (name, email, password_hash, role)
            SELECT %s, %s, %s, %s
            WHERE NOT EXISTS (
                SELECT 1 FROM users WHERE email = %s
            );
            """,
            ('Admin MG Street', admin_email, admin_password_hash, 'admin', admin_email),
        )
        # Usuário comprador de exemplo para preview/demo, se ainda não existir.
        demo_email = os.getenv("DEMO_EMAIL", "cliente@mgstreet.com")
        demo_password_hash = hash_password(os.getenv("DEMO_PASSWORD", "cliente"))
        cursor.execute(
            """
            INSERT INTO users (name, email, password_hash, role)
            SELECT %s, %s, %s, %s
            WHERE NOT EXISTS (
                SELECT 1 FROM users WHERE email = %s
            );
            """,
            ('Cliente Demo', demo_email, demo_password_hash, 'user', demo_email),
        )
    app.db_conn.commit()
    app.logger.info("Tabela users garantida e admin padrão inserido, se necessário.")


def create_categories_table(app):
    with app.db_conn.cursor() as cursor:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS categories (
                id SERIAL PRIMARY KEY,
                name TEXT UNIQUE NOT NULL
            );
            """
        )
        for category_name in ('camisetas', 'calcas', 'meias'):
            cursor.execute(
                "INSERT INTO categories (name) VALUES (%s) ON CONFLICT (name) DO NOTHING;",
                (category_name,),
            )
    app.db_conn.commit()
    app.logger.info("Tabela categories garantida no banco.")


def create_products_table(app):
    with app.db_conn.cursor() as cursor:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS products (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                price NUMERIC(10, 2) NOT NULL CHECK (price >= 0),
                image_url TEXT,
                category_id INTEGER REFERENCES categories(id) ON DELETE SET NULL,
                options JSONB NOT NULL DEFAULT '{}'::jsonb,
                created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
            );
            """
        )
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_products_category_id ON products (category_id);")
        # Opções/variações do produto (cor, tamanho, ...) — idempotente para schema existente.
        cursor.execute("ALTER TABLE products ADD COLUMN IF NOT EXISTS options JSONB NOT NULL DEFAULT '{}'::jsonb;")
        # Popula produtos de exemplo para dar contexto à UI do admin.
        cursor.execute('SELECT COUNT(1) FROM products')
        count = cursor.fetchone()[0]
        if count == 0:
            app.logger.info('Sem produtos, inserindo amostra para contexto UI.')
            cursor.execute('SELECT name, id FROM categories')
            category_ids = {name: category_id for name, category_id in cursor.fetchall()}
            sample = [
                ('Camiseta Básica - Preto', 'Camiseta 100% algodão, corte reto.', 49.9, '', 'camisetas'),
                ('Camiseta Estampada - Branco', 'Camiseta com estampa exclusiva MG Street.', 59.9, '', 'camisetas'),
                ('Calça Jeans Slim', 'Calça jeans slim fit, confortável.', 129.9, '', 'calcas'),
                ('Meias Esportivas (Par)', 'Par de meias esportivas, tamanhos M-L.', 19.9, '', 'meias')
            ]
            for name, description, price, image_url, category_name in sample:
                cursor.execute(
                    "INSERT INTO products (name, description, price, image_url, category_id) VALUES (%s, %s, %s, %s, %s)",
                    (name, description, price, image_url, category_ids.get(category_name)),
                )
    app.db_conn.commit()
    app.logger.info("Tabela products garantida no banco.")


def create_orders_table(app):
    with app.db_conn.cursor() as cursor:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS orders (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
                total NUMERIC(10, 2) NOT NULL CHECK (total >= 0),
                created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
            );
            """
        )
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_user_id ON orders (user_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders (created_at DESC);")
    app.db_conn.commit()
    app.logger.info("Tabela orders garantida no banco.")


def create_order_items_table(app):
    with app.db_conn.cursor() as cursor:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS order_items (
                id SERIAL PRIMARY KEY,
                order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
                product_id INTEGER REFERENCES products(id) ON DELETE SET NULL,
                product_name TEXT NOT NULL,
                unit_price NUMERIC(10, 2) NOT NULL CHECK (unit_price >= 0),
                quantity INTEGER NOT NULL CHECK (quantity > 0),
                selected_options JSONB NOT NULL DEFAULT '{}'::jsonb
            );
            """
        )
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_order_items_order_id ON order_items (order_id);")
        # Opções escolhidas no momento da compra (snapshot) — idempotente.
        cursor.execute("ALTER TABLE order_items ADD COLUMN IF NOT EXISTS selected_options JSONB NOT NULL DEFAULT '{}'::jsonb;")
    app.db_conn.commit()
    app.logger.info("Tabela order_items garantida no banco.")


def initialize_database(app):
    create_users_table(app)
    create_categories_table(app)
    create_products_table(app)
    create_orders_table(app)
    create_order_items_table(app)


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "mgstreet_secret_key")
    app.config["POSTGRES_USER"] = os.getenv("POSTGRES_USER", "mgstreet_user")
    app.config["POSTGRES_PASSWORD"] = os.getenv("POSTGRES_PASSWORD", "mgstreet_pass")
    app.config["POSTGRES_DB"] = os.getenv("POSTGRES_DB", "mgstreet_db")
    app.config["POSTGRES_HOST"] = os.getenv("POSTGRES_HOST", "db")
    app.config["JWT_SECRET"] = os.getenv("JWT_SECRET", "mgstreet_jwt_secret")
    app.config["JWT_EXP_HOURS"] = int(os.getenv("JWT_EXP_HOURS", 12))

    # Rate limiting do login (in-memory, por IP+email) para mitigar brute-force.
    app.login_limiter = RateLimiter(
        max_attempts=int(os.getenv("LOGIN_RATE_LIMIT", 5)),
        window_seconds=int(os.getenv("LOGIN_RATE_WINDOW", 60)),
    )

    @app.route("/ping", methods=["GET"])
    def ping():
        return jsonify({"status": "ok", "message": "pong"})

    @app.route("/tests/report", methods=["GET"])
    def tests_report():
        # Diagnóstico de desenvolvimento: roda a suíte e mostra um relatório HTML.
        if os.getenv("FLASK_ENV") != "development":
            return jsonify({"error": "Relatório disponível apenas em desenvolvimento."}), 403
        try:
            summary, cases, raw_tail = qa_report.run_pytest()
            # Container roda em UTC; mostra o horário local (BRT/UTC-3 por padrão).
            tz = datetime.timezone(datetime.timedelta(hours=int(os.getenv("REPORT_TZ_OFFSET", -3))))
            generated_at = datetime.datetime.now(tz).strftime("%d/%m/%Y %H:%M:%S")
            page = qa_report.render_html(summary, cases, raw_tail, generated_at)
            return page, 200, {"Content-Type": "text/html; charset=utf-8"}
        except Exception as exc:
            app.logger.error("Falha ao gerar relatório de testes: %s", exc)
            return jsonify({"error": "Falha ao rodar os testes."}), 500

    @app.route("/api/register", methods=["POST"])
    def register():
        payload = request.get_json() or {}
        name = payload.get("name")
        email = payload.get("email")
        password = payload.get("password")

        if not name or not email or not password:
            return jsonify({"error": "Dados incompletos."}), 400

        try:
            users_repo.create(app.db_conn, name, email, hash_password(password))
            return jsonify({"message": "Registro criado com sucesso."}), 201
        except Exception as exc:
            app.logger.error("Falha no registro: %s", exc)
            return jsonify({"error": "Falha ao criar usuário."}), 400

    @app.route("/api/login", methods=["POST"])
    def login():
        payload = request.get_json() or {}
        email = payload.get("email")
        password = payload.get("password")

        if not email or not password:
            return jsonify({"error": "Dados incompletos."}), 400

        limiter_key = f"{request.remote_addr}:{email}"
        if not app.login_limiter.is_allowed(limiter_key):
            return jsonify({"error": "Muitas tentativas. Tente novamente em instantes."}), 429

        try:
            row = users_repo.get_credentials_by_email(app.db_conn, email)
            if not row:
                return jsonify({"error": "Credenciais inválidas."}), 401

            user_id, password_hash, role = row
            if not verify_password(password, password_hash):
                return jsonify({"error": "Credenciais inválidas."}), 401

            expires_at = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(
                hours=app.config["JWT_EXP_HOURS"]
            )
            token = jwt.encode(
                {"id": user_id, "role": role, "exp": expires_at},
                app.config["JWT_SECRET"],
                algorithm="HS256",
            )
            return jsonify({"token": token, "role": role}), 200
        except Exception as exc:
            app.logger.error("Falha no login: %s", exc)
            return jsonify({"error": "Falha ao autenticar."}), 500

    @app.route("/")
    def landing_page():
        return render_template("landing.html")

    @app.route("/login")
    def login_page():
        return render_template("login.html")

    @app.route("/admin")
    def admin_page():
        return render_template("admin.html")

    @app.route("/shop")
    def shop_page():
        return render_template("shop.html")

    @app.route("/api/public/products", methods=["GET"])
    def public_products():
        # Catálogo público para a landing (sem autenticação).
        try:
            rows = products_repo.list_all(app.db_conn)
            return jsonify({"products": serialize_products(rows)}), 200
        except Exception as exc:
            app.logger.error("Erro ao listar produtos (público): %s", exc)
            return jsonify({"error": "Falha ao listar produtos."}), 500

    @app.route('/api/products', methods=['POST'])
    @admin_required
    def create_product(payload):
        data = request.get_json() or {}
        name = data.get('name')
        description = data.get('description', '')
        price = data.get('price')
        image_url = data.get('image_url')
        category = data.get('category')
        options = data.get('options') or {}

        if not name or price is None:
            return jsonify({'error': 'Dados incompletos para produto.'}), 400

        try:
            category_id = categories_repo.resolve_id(app.db_conn, category)
            product_id = products_repo.create(app.db_conn, name, description, price, image_url, category_id, options)
            return jsonify({'message': 'Produto criado.', 'id': product_id}), 201
        except Exception as exc:
            app.logger.error('Erro ao criar produto: %s', exc)
            return jsonify({'error': 'Falha ao criar produto.'}), 500

    @app.route('/api/products', methods=['GET'])
    @token_required
    def list_products(payload):
        try:
            rows = products_repo.list_all(app.db_conn)
            return jsonify({'products': serialize_products(rows)}), 200
        except Exception as exc:
            app.logger.error('Erro ao listar produtos: %s', exc)
            return jsonify({'error': 'Falha ao listar produtos.'}), 500

    @app.route('/api/products/<int:product_id>', methods=['DELETE'])
    @admin_required
    def delete_product(payload, product_id):
        try:
            deleted_id = products_repo.delete(app.db_conn, product_id)
            if deleted_id is None:
                return jsonify({'error': 'Produto não encontrado.'}), 404
            return jsonify({'message': 'Produto removido.'}), 200
        except Exception as exc:
            app.logger.error('Erro ao deletar produto: %s', exc)
            return jsonify({'error': 'Falha ao deletar produto.'}), 500

    @app.route('/api/products/<int:product_id>', methods=['PUT'])
    @admin_required
    def update_product(payload, product_id):
        data = request.get_json() or {}
        name = data.get('name')
        description = data.get('description', '')
        price = data.get('price')
        image_url = data.get('image_url')
        category = data.get('category')
        options = data.get('options') or {}

        if not name or price is None:
            return jsonify({'error': 'Dados incompletos para produto.'}), 400

        try:
            category_id = categories_repo.resolve_id(app.db_conn, category)
            updated_id = products_repo.update(
                app.db_conn, product_id, name, description, price, image_url, category_id, options
            )
            if updated_id is None:
                return jsonify({'error': 'Produto não encontrado.'}), 404
            return jsonify({'message': 'Produto atualizado.', 'id': updated_id}), 200
        except Exception as exc:
            app.logger.error('Erro ao atualizar produto: %s', exc)
            return jsonify({'error': 'Falha ao atualizar produto.'}), 500

    @app.route('/api/orders', methods=['GET'])
    @admin_required
    def list_orders(payload):
        try:
            rows = orders_repo.list_with_items(app.db_conn)
            result = [
                {
                    'id': row[0],
                    'user_id': row[1],
                    'total': float(row[2]) if row[2] is not None else 0,
                    'created_at': row[3].isoformat() if row[3] is not None else None,
                    'items': row[4] if row[4] is not None else []
                }
                for row in rows
            ]
            return jsonify({'orders': result}), 200
        except Exception as exc:
            app.logger.error('Erro ao listar pedidos: %s', exc)
            return jsonify({'error': 'Falha ao listar pedidos.'}), 500

    @app.route('/api/orders/stats', methods=['GET'])
    @admin_required
    def orders_stats(payload):
        try:
            row = orders_repo.stats(app.db_conn)
            total_orders = int(row[0])
            total_revenue = float(row[1])
            return jsonify({'total_orders': total_orders, 'total_revenue': total_revenue}), 200
        except Exception as exc:
            app.logger.error('Erro ao calcular estatísticas de pedidos: %s', exc)
            return jsonify({'error': 'Falha ao calcular estatísticas.'}), 500

    @app.route('/api/checkout', methods=['POST'])
    @token_required
    def checkout(payload):
        data = request.get_json() or {}
        items = data.get('items') or []
        if not isinstance(items, list) or len(items) == 0:
            return jsonify({'error': 'Carrinho vazio.'}), 400

        total = calculate_cart_total(items)

        try:
            order_id = orders_repo.create_with_items(app.db_conn, payload.get('id'), items, total)
            return jsonify({'message': 'Pedido registrado.', 'order_id': order_id}), 201
        except Exception as exc:
            app.logger.error('Falha ao criar pedido: %s', exc)
            return jsonify({'error': 'Falha ao criar pedido.'}), 500

    @app.route('/api/preview_token', methods=['GET'])
    @admin_required
    def preview_token(payload):
        """Gera um JWT do cliente-demo para o admin pré-visualizar a loja como esse usuário."""
        try:
            demo_email = os.getenv('DEMO_EMAIL', 'cliente@mgstreet.com')
            row = users_repo.get_by_email(app.db_conn, demo_email)
            if not row:
                return jsonify({'error': 'Usuário de exemplo não encontrado.'}), 404
            user_id, name, email, role = row
            expires_at = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(
                hours=app.config['JWT_EXP_HOURS']
            )
            token = jwt.encode({'id': user_id, 'role': role, 'exp': expires_at}, app.config['JWT_SECRET'], algorithm='HS256')
            return jsonify({'token': token, 'user': {'id': user_id, 'name': name, 'email': email, 'role': role}}), 200
        except Exception as exc:
            app.logger.error('Falha ao gerar token de preview: %s', exc)
            return jsonify({'error': 'Falha ao gerar token de preview.'}), 500

    return app


app = create_app()


if __name__ == "__main__":
    init_db_connection(app)
    initialize_database(app)
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5001)), debug=True)

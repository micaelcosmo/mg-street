from dotenv import load_dotenv
from flask import Flask, jsonify, request, current_app, render_template
import os
import time
import hashlib
import hmac
import datetime
import uuid
import jwt
import psycopg2
from functools import wraps
from werkzeug.utils import secure_filename

import qa_report
import payments
import emailer
from logging_setup import configure_logging
from ratelimit import RateLimiter
from validation import is_valid_email
from repositories import (
    cart as cart_repo,
    categories as categories_repo,
    orders as orders_repo,
    products as products_repo,
    users as users_repo,
)


load_dotenv()


UPLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "uploads")
ALLOWED_IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


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
            "stock": row[7] if len(row) > 7 else None,
        }
        for row in rows
    ]


def serialize_orders(rows):
    """Converte linhas de pedido (id, user_id, total, created_at, status, items)."""
    result = []
    for row in rows:
        if len(row) >= 6:
            status, items = row[4], row[5]
        else:
            status, items = "pending", row[4]
        result.append(
            {
                "id": row[0],
                "user_id": row[1],
                "total": float(row[2]) if row[2] is not None else 0,
                "created_at": row[3].isoformat() if row[3] is not None else None,
                "status": status,
                "items": items if items is not None else [],
            }
        )
    return result


def send_order_confirmation(conn, order_id):
    """Envia (best-effort) o e-mail de confirmação do pedido pago."""
    try:
        email = orders_repo.get_user_email(conn, order_id)
        if email:
            emailer.send_email(
                email,
                f"Pedido #{order_id} confirmado — MG Street",
                f"Recebemos o pagamento do seu pedido #{order_id}. Obrigado pela compra!",
            )
    except Exception:
        pass


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

    # Bancos gerenciados (Neon/Supabase/Render etc.) exigem SSL; habilita via env
    # quando definido (ex.: POSTGRES_SSLMODE=require). Sem a variável, mantém o
    # comportamento local (sem SSL).
    sslmode = os.getenv("POSTGRES_SSLMODE")
    if sslmode:
        base_config["sslmode"] = sslmode

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
                stock INTEGER NOT NULL DEFAULT 100 CHECK (stock >= 0),
                created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
            );
            """
        )
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_products_category_id ON products (category_id);")
        # Opções/variações e estoque — idempotente para schema existente.
        cursor.execute("ALTER TABLE products ADD COLUMN IF NOT EXISTS options JSONB NOT NULL DEFAULT '{}'::jsonb;")
        cursor.execute("ALTER TABLE products ADD COLUMN IF NOT EXISTS stock INTEGER NOT NULL DEFAULT 100;")
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
                status TEXT NOT NULL DEFAULT 'pending'
                    CHECK (status IN ('pending', 'paid', 'failed', 'cancelled')),
                payment_id TEXT,
                created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
            );
            """
        )
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_user_id ON orders (user_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders (created_at DESC);")
        # Status do pagamento — idempotente para schema existente.
        cursor.execute(
            "ALTER TABLE orders ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'pending';"
        )
        cursor.execute("ALTER TABLE orders ADD COLUMN IF NOT EXISTS payment_id TEXT;")
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


def create_carts_table(app):
    with app.db_conn.cursor() as cursor:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS carts (
                user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
                items JSONB NOT NULL DEFAULT '[]'::jsonb,
                updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
            );
            """
        )
    app.db_conn.commit()
    app.logger.info("Tabela carts garantida no banco.")


def initialize_database(app):
    create_users_table(app)
    create_categories_table(app)
    create_products_table(app)
    create_orders_table(app)
    create_order_items_table(app)
    create_carts_table(app)


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "mgstreet_secret_key")
    app.config["POSTGRES_USER"] = os.getenv("POSTGRES_USER", "mgstreet_user")
    app.config["POSTGRES_PASSWORD"] = os.getenv("POSTGRES_PASSWORD", "mgstreet_pass")
    app.config["POSTGRES_DB"] = os.getenv("POSTGRES_DB", "mgstreet_db")
    app.config["POSTGRES_HOST"] = os.getenv("POSTGRES_HOST", "db")
    app.config["JWT_SECRET"] = os.getenv("JWT_SECRET", "mgstreet_jwt_secret")
    app.config["JWT_EXP_HOURS"] = int(os.getenv("JWT_EXP_HOURS", 12))
    app.config["MAX_CONTENT_LENGTH"] = int(os.getenv("MAX_UPLOAD_BYTES", 5 * 1024 * 1024))
    app.config["PUBLIC_BASE_URL"] = os.getenv("PUBLIC_BASE_URL", "http://localhost:5001")

    configure_logging(app)

    # Rate limiting in-memory para mitigar abuso (login/registro/checkout).
    app.login_limiter = RateLimiter(
        max_attempts=int(os.getenv("LOGIN_RATE_LIMIT", 5)),
        window_seconds=int(os.getenv("LOGIN_RATE_WINDOW", 60)),
    )
    app.register_limiter = RateLimiter(
        max_attempts=int(os.getenv("REGISTER_RATE_LIMIT", 5)),
        window_seconds=int(os.getenv("REGISTER_RATE_WINDOW", 60)),
    )
    app.checkout_limiter = RateLimiter(
        max_attempts=int(os.getenv("CHECKOUT_RATE_LIMIT", 10)),
        window_seconds=int(os.getenv("CHECKOUT_RATE_WINDOW", 60)),
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

        if not app.register_limiter.is_allowed(request.remote_addr or "?"):
            return jsonify({"error": "Muitas tentativas. Tente novamente em instantes."}), 429
        if not name or not email or not password:
            return jsonify({"error": "Dados incompletos."}), 400
        if not is_valid_email(email):
            return jsonify({"error": "E-mail inválido."}), 400
        if len(password) < 4:
            return jsonify({"error": "A senha deve ter ao menos 4 caracteres."}), 400

        try:
            users_repo.create(app.db_conn, name, email, hash_password(password))
            try:
                emailer.send_email(email, "Bem-vindo à MG Street", f"Olá {name}, sua conta foi criada!")
            except Exception:
                pass
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

    @app.route("/register")
    def register_page():
        return render_template("register.html")

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
        stock = data.get('stock', 0)

        if not name or price is None:
            return jsonify({'error': 'Dados incompletos para produto.'}), 400
        try:
            price = float(price)
        except (TypeError, ValueError):
            return jsonify({'error': 'Preço deve ser um número.'}), 400
        if price < 0:
            return jsonify({'error': 'Preço não pode ser negativo.'}), 400

        try:
            category_id = categories_repo.resolve_id(app.db_conn, category)
            product_id = products_repo.create(app.db_conn, name, description, price, image_url, category_id, options, stock)
            return jsonify({'message': 'Produto criado.', 'id': product_id}), 201
        except Exception as exc:
            app.logger.error('Erro ao criar produto: %s', exc)
            return jsonify({'error': 'Falha ao criar produto.'}), 500

    @app.route('/api/upload', methods=['POST'])
    @admin_required
    def upload_image(payload):
        uploaded = request.files.get('file')
        if not uploaded or not uploaded.filename:
            return jsonify({'error': 'Nenhum arquivo enviado.'}), 400
        ext = os.path.splitext(uploaded.filename)[1].lower()
        if ext not in ALLOWED_IMAGE_EXT:
            return jsonify({'error': 'Formato não suportado (jpg, png, webp, gif).'}), 400
        try:
            os.makedirs(UPLOAD_DIR, exist_ok=True)
            filename = uuid.uuid4().hex[:8] + "_" + secure_filename(uploaded.filename)
            uploaded.save(os.path.join(UPLOAD_DIR, filename))
            return jsonify({'url': f'/static/uploads/{filename}'}), 201
        except Exception as exc:
            app.logger.error('Falha no upload de imagem: %s', exc)
            return jsonify({'error': 'Falha ao salvar a imagem.'}), 500

    @app.route('/api/products', methods=['GET'])
    @token_required
    def list_products(payload):
        q = request.args.get('q') or None
        limit = None
        offset = 0
        per_page = request.args.get('per_page')
        if per_page:
            try:
                limit = max(1, min(100, int(per_page)))
                offset = max(0, (int(request.args.get('page', 1) or 1) - 1) * limit)
            except (TypeError, ValueError):
                limit = None
        try:
            rows = products_repo.search(app.db_conn, q, limit, offset)
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
        stock = data.get('stock', 0)

        if not name or price is None:
            return jsonify({'error': 'Dados incompletos para produto.'}), 400
        try:
            price = float(price)
        except (TypeError, ValueError):
            return jsonify({'error': 'Preço deve ser um número.'}), 400
        if price < 0:
            return jsonify({'error': 'Preço não pode ser negativo.'}), 400

        try:
            category_id = categories_repo.resolve_id(app.db_conn, category)
            updated_id = products_repo.update(
                app.db_conn, product_id, name, description, price, image_url, category_id, options, stock
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
            return jsonify({'orders': serialize_orders(rows)}), 200
        except Exception as exc:
            app.logger.error('Erro ao listar pedidos: %s', exc)
            return jsonify({'error': 'Falha ao listar pedidos.'}), 500

    @app.route('/api/orders/me', methods=['GET'])
    @token_required
    def my_orders(payload):
        try:
            rows = orders_repo.list_with_items(app.db_conn, payload.get('id'))
            return jsonify({'orders': serialize_orders(rows)}), 200
        except Exception as exc:
            app.logger.error('Erro ao listar meus pedidos: %s', exc)
            return jsonify({'error': 'Falha ao listar pedidos.'}), 500

    @app.route('/api/cart', methods=['GET'])
    @token_required
    def get_cart(payload):
        try:
            items = cart_repo.get_items(app.db_conn, payload.get('id'))
            return jsonify({'items': items}), 200
        except Exception as exc:
            app.logger.error('Erro ao carregar carrinho: %s', exc)
            return jsonify({'error': 'Falha ao carregar carrinho.'}), 500

    @app.route('/api/cart', methods=['PUT'])
    @token_required
    def save_cart(payload):
        data = request.get_json() or {}
        items = data.get('items')
        if not isinstance(items, list):
            return jsonify({'error': 'Itens inválidos.'}), 400
        try:
            cart_repo.save_items(app.db_conn, payload.get('id'), items)
            return jsonify({'message': 'Carrinho salvo.'}), 200
        except Exception as exc:
            app.logger.error('Erro ao salvar carrinho: %s', exc)
            return jsonify({'error': 'Falha ao salvar carrinho.'}), 500

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
        if not app.checkout_limiter.is_allowed(str(payload.get('id'))):
            return jsonify({'error': 'Muitas tentativas. Tente novamente em instantes.'}), 429

        data = request.get_json() or {}
        items = data.get('items') or []
        if not isinstance(items, list) or len(items) == 0:
            return jsonify({'error': 'Carrinho vazio.'}), 400

        total = calculate_cart_total(items)

        try:
            order_id = orders_repo.create_with_items(app.db_conn, payload.get('id'), items, total)
        except orders_repo.OutOfStockError as exc:
            return jsonify({'error': f'Estoque insuficiente para "{exc}".'}), 409
        except Exception as exc:
            app.logger.error('Falha ao criar pedido: %s', exc)
            return jsonify({'error': 'Falha ao criar pedido.'}), 500

        # Pagamento configurado? Gera a preferência (Checkout Pro) e devolve o init_point.
        if payments.is_enabled():
            try:
                pref = payments.create_preference(order_id, items, app.config['PUBLIC_BASE_URL'])
            except Exception as exc:
                app.logger.error('Falha ao criar preferência de pagamento: %s', exc)
                pref = None
            if pref and pref.get('init_point'):
                return jsonify({
                    'message': 'Pedido criado. Redirecionando para o pagamento.',
                    'order_id': order_id,
                    'init_point': pref['init_point'],
                    'sandbox_init_point': pref.get('sandbox_init_point'),
                }), 201

        return jsonify({'message': 'Pedido registrado.', 'order_id': order_id}), 201

    @app.route('/api/payments/confirm', methods=['POST'])
    @token_required
    def confirm_payment(payload):
        data = request.get_json() or {}
        payment_id = data.get('payment_id')
        if not payment_id:
            return jsonify({'error': 'payment_id ausente.'}), 400
        try:
            info = payments.get_payment(payment_id)
            if not info:
                return jsonify({'error': 'Pagamento indisponível.'}), 400
            if info.get('status') == 'approved' and info.get('external_reference'):
                order_id = int(info['external_reference'])
                orders_repo.mark_paid(app.db_conn, order_id, str(payment_id))
                send_order_confirmation(app.db_conn, order_id)
                return jsonify({'status': 'paid'}), 200
            return jsonify({'status': info.get('status') or 'unknown'}), 200
        except Exception as exc:
            app.logger.error('Erro ao confirmar pagamento: %s', exc)
            return jsonify({'error': 'Falha ao confirmar pagamento.'}), 500

    @app.route('/api/payments/webhook', methods=['POST'])
    def payment_webhook():
        # MP notifica via corpo {type, data:{id}} ou querystring; respondemos 200 sempre.
        data = request.get_json(silent=True) or {}
        payment_id = (data.get('data') or {}).get('id') or request.args.get('data.id') or request.args.get('id')
        if payment_id:
            try:
                info = payments.get_payment(payment_id)
                if info and info.get('status') == 'approved' and info.get('external_reference'):
                    order_id = int(info['external_reference'])
                    orders_repo.mark_paid(app.db_conn, order_id, str(payment_id))
                    send_order_confirmation(app.db_conn, order_id)
            except Exception as exc:
                app.logger.error('Erro no webhook de pagamento: %s', exc)
        return '', 200

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

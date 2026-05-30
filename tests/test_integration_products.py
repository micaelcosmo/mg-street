import jwt


def _admin_token(application):
    return jwt.encode(
        {"id": 1, "role": "admin"},
        application.config["JWT_SECRET"],
        algorithm="HS256",
    )


def _user_token(application):
    return jwt.encode(
        {"id": 2, "role": "user"},
        application.config["JWT_SECRET"],
        algorithm="HS256",
    )


# ---- POST /api/products ----

def test_create_product_requires_token(client):
    resp = client.post("/api/products", json={"name": "X", "price": 10})
    assert resp.status_code == 401


def test_create_product_requires_admin(client, application):
    token = _user_token(application)
    resp = client.post(
        "/api/products",
        json={"name": "X", "price": 10},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


def test_create_product_missing_fields(client, application):
    token = _admin_token(application)
    resp = client.post(
        "/api/products",
        json={"name": "Sem preco"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400


def test_create_product_success(client, application, set_cursor):
    # fetchone -> id retornado por "INSERT ... RETURNING id".
    set_cursor(fetchone=(42,))
    token = _admin_token(application)
    resp = client.post(
        "/api/products",
        json={"name": "Camiseta", "description": "algodao", "price": 49.9, "image_url": ""},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    assert resp.get_json()["id"] == 42


def test_create_product_with_category_succeeds(client, application, set_cursor):
    # mesmo fetchone serve para resolve_category_id e para o id do produto.
    set_cursor(fetchone=(7,))
    token = _admin_token(application)
    resp = client.post(
        "/api/products",
        json={"name": "Camiseta", "price": 49.9, "category": "camisetas"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201


# ---- GET /api/products ----

def test_list_products_requires_token(client):
    resp = client.get("/api/products")
    assert resp.status_code == 401


def test_list_products_returns_catalog(client, application, set_cursor):
    set_cursor(fetchall=[
        (1, "Camiseta", "algodao", 49.9, "", "camisetas"),
        (2, "Meias", "par", 19.9, "", "meias"),
    ])
    token = _user_token(application)
    resp = client.get("/api/products", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data["products"]) == 2
    primeiro = data["products"][0]
    assert primeiro["name"] == "Camiseta"
    assert primeiro["price"] == 49.9
    assert primeiro["category"] == "camisetas"


# ---- DELETE /api/products/<id> ----

def test_delete_product_requires_token(client):
    resp = client.delete("/api/products/1")
    assert resp.status_code == 401


def test_delete_product_requires_admin(client, application):
    token = _user_token(application)
    resp = client.delete("/api/products/1", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403


def test_delete_product_success(client, application, set_cursor):
    # fetchone com valor -> "RETURNING id" achou a linha.
    set_cursor(fetchone=(1,))
    token = _admin_token(application)
    resp = client.delete("/api/products/1", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200


def test_delete_product_not_found(client, application, set_cursor):
    # fetchone None -> nada removido -> 404.
    set_cursor(fetchone=None)
    token = _admin_token(application)
    resp = client.delete("/api/products/999", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 404


# ---- Variações de produto (options) ----

def test_create_product_with_options(client, application, set_cursor):
    set_cursor(fetchone=(8,))
    token = _admin_token(application)
    resp = client.post(
        "/api/products",
        json={
            "name": "Camiseta",
            "price": 49.9,
            "options": {"Cor": ["Preto", "Roxo"], "Tamanho": ["P", "M"]},
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201


def test_list_products_includes_options(client, application, set_cursor):
    set_cursor(fetchall=[(1, "Camiseta", "algodao", 49.9, "", "camisetas", {"Cor": ["Preto", "Roxo"]})])
    token = _user_token(application)
    resp = client.get("/api/products", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.get_json()["products"][0]["options"] == {"Cor": ["Preto", "Roxo"]}


# ---- PUT /api/products/<id> ----

def test_update_product_requires_admin(client, application):
    token = _user_token(application)
    resp = client.put(
        "/api/products/1",
        json={"name": "X", "price": 10},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


def test_update_product_success(client, application, set_cursor):
    set_cursor(fetchone=(5,))
    token = _admin_token(application)
    resp = client.put(
        "/api/products/5",
        json={"name": "Camiseta Nova", "price": 59.9},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.get_json()["id"] == 5


def test_update_product_not_found(client, application, set_cursor):
    set_cursor(fetchone=None)
    token = _admin_token(application)
    resp = client.put(
        "/api/products/999",
        json={"name": "X", "price": 10},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404

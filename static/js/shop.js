/* shop.js — loja do cliente (vanilla). Usa showToast (toast.js). Mantém resolvedor de token
   próprio por causa do modo preview (admin vê a loja com um token de cliente). */
const PREVIEW_TOKEN_KEY = "mgstreet_preview_token";
const TOKEN_KEY = "mgstreet_token";

(function checkAuthAndSetupButton() {
    const previewToken = localStorage.getItem(PREVIEW_TOKEN_KEY);
    const token = previewToken || localStorage.getItem(TOKEN_KEY);
    const logoutBtn = document.getElementById("logout-btn");

    if (!token) {
        window.location.href = "/login";
        return;
    }

    if (previewToken) {
        logoutBtn.textContent = "Voltar";
        logoutBtn.onclick = function () {
            localStorage.removeItem(PREVIEW_TOKEN_KEY);
            window.location.href = "/admin";
        };
    } else {
        logoutBtn.textContent = "Sair";
        logoutBtn.onclick = function () {
            localStorage.removeItem(TOKEN_KEY);
            window.location.href = "/";
        };
    }
})();

const catalogSections = document.getElementById("catalog-sections");
const categoryFilters = document.getElementById("category-filters");
const productCount = document.getElementById("product-count");
let allProducts = [];
let activeCategory = "todos";

function getToken() {
    return localStorage.getItem(PREVIEW_TOKEN_KEY) || localStorage.getItem(TOKEN_KEY);
}

function authHeaders(extra) {
    return Object.assign({ Authorization: "Bearer " + getToken() }, extra || {});
}

function normalizeCategory(category) {
    return (category || "sem-categoria").toString().trim().toLowerCase();
}

function getCategoryLabel(category) {
    const labels = {
        todos: "Todos",
        camisetas: "Camisetas",
        calcas: "Calças",
        meias: "Meias",
        "sem-categoria": "Sem categoria",
    };
    return labels[category] || category.charAt(0).toUpperCase() + category.slice(1);
}

function buildCategoryFilters(products) {
    const categories = Array.from(new Set(products.map(function (product) {
        return normalizeCategory(product.category);
    }))).filter(Boolean).sort();

    const options = ["todos"].concat(categories);
    categoryFilters.innerHTML = "";

    options.forEach(function (category) {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "filter-chip " + (category === activeCategory ? "active" : "");
        button.textContent = getCategoryLabel(category);
        button.dataset.category = category;
        button.addEventListener("click", function () {
            activeCategory = category;
            buildCategoryFilters(allProducts);
            renderCatalog();
        });
        categoryFilters.appendChild(button);
    });
}

function createProductCard(product) {
    const card = document.createElement("article");
    card.className = "product-card";
    const options = product.options || {};
    const optionsHtml = Object.keys(options).map(function (key) {
        const opts = (options[key] || []).map(function (value) {
            return '<option value="' + value + '">' + value + "</option>";
        }).join("");
        return '<label class="product-option"><span>' + key + '</span><select data-opt="' + key + '">' + opts + "</select></label>";
    }).join("");
    const soldOut = product.stock != null && product.stock <= 0;
    card.innerHTML =
        '<div class="product-img">' +
        '<img src="' + (product.image_url || "") + '" alt="' + product.name + '" loading="lazy"/>' +
        "</div>" +
        '<div class="product-body">' +
        '<span class="product-tag">' + getCategoryLabel(normalizeCategory(product.category)) + "</span>" +
        "<h4>" + product.name + "</h4>" +
        '<p class="muted">' + (product.description || "") + "</p>" +
        (optionsHtml ? '<div class="product-options">' + optionsHtml + "</div>" : "") +
        '<div class="product-footer">' +
        "<strong>R$ " + (product.price != null ? Number(product.price).toFixed(2) : "0.00") + "</strong>" +
        (soldOut
            ? '<span class="muted">Esgotado</span>'
            : '<button class="btn buy-btn" data-id="' + product.id + '" data-name="' + product.name + '" data-price="' + product.price + '">Comprar</button>') +
        "</div>" +
        "</div>";
    // Fallback de imagem: se a URL falhar/faltar, mostra o placeholder do container.
    const img = card.querySelector(".product-img img");
    if (img) {
        img.addEventListener("error", function () {
            img.classList.add("product-img--broken");
        });
        if (!product.image_url) {
            img.classList.add("product-img--broken");
        }
    }
    return card;
}

function renderCatalog() {
    const productsToRender = activeCategory === "todos"
        ? allProducts
        : allProducts.filter(function (product) {
            return normalizeCategory(product.category) === activeCategory;
        });

    productCount.textContent = productsToRender.length;
    catalogSections.innerHTML = "";

    if (productsToRender.length === 0) {
        const empty = document.createElement("section");
        empty.className = "catalog-empty card";
        empty.innerHTML = "<h3>Nenhum produto encontrado.</h3><p class=\"muted\">Tente outra categoria.</p>";
        catalogSections.appendChild(empty);
        return;
    }

    const groupedProducts = {};
    productsToRender.forEach(function (product) {
        const category = normalizeCategory(product.category);
        if (!groupedProducts[category]) {
            groupedProducts[category] = [];
        }
        groupedProducts[category].push(product);
    });

    Object.keys(groupedProducts).sort().forEach(function (category) {
        const section = document.createElement("section");
        section.className = "catalog-group card";
        section.innerHTML =
            '<div class="catalog-group-header">' +
            "<div>" +
            '<span class="section-kicker">' + getCategoryLabel(category) + "</span>" +
            "<h3>" + getCategoryLabel(category) + "</h3>" +
            "</div>" +
            '<span class="group-count">' + groupedProducts[category].length + " produto(s)</span>" +
            "</div>";

        const grid = document.createElement("div");
        grid.className = "products-grid";
        groupedProducts[category].forEach(function (product) {
            grid.appendChild(createProductCard(product));
        });
        section.appendChild(grid);
        catalogSections.appendChild(section);
    });
}

async function loadProducts() {
    catalogSections.innerHTML = '<div class="products-grid">' + skeletonCards(6) + "</div>";
    try {
        const response = await fetch("/api/products", { headers: authHeaders() });
        if (!response.ok) {
            showToast("Não foi possível carregar os produtos.");
            return;
        }
        const data = await response.json();
        allProducts = data.products || [];
        productCount.textContent = allProducts.length;
        buildCategoryFilters(allProducts);
        renderCatalog();
    } catch (error) {
        console.error("Erro ao carregar produtos", error);
        showToast("Erro ao carregar produtos.");
    }
}

document.addEventListener("click", function (event) {
    const button = event.target.closest("button.buy-btn");
    if (!button) {
        return;
    }
    const id = button.getAttribute("data-id");
    const name = button.getAttribute("data-name");
    const price = parseFloat(button.getAttribute("data-price")) || 0;

    const selected = {};
    const card = button.closest(".product-card");
    if (card) {
        card.querySelectorAll("select[data-opt]").forEach(function (select) {
            selected[select.getAttribute("data-opt")] = select.value;
        });
    }

    const cart = JSON.parse(sessionStorage.getItem("mg_cart") || "[]");
    const key = id + "|" + JSON.stringify(selected);
    const existing = cart.find(function (item) {
        return (item.id + "|" + JSON.stringify(item.options || {})) === key;
    });
    if (existing) {
        existing.quantity = (existing.quantity || 1) + 1;
    } else {
        cart.push({ id: id, name: name, price: price, quantity: 1, options: selected });
    }
    persistCart(cart);
    showToast("Item adicionado ao carrinho");
    updateCartUI();
});

const cartButton = document.getElementById("cart-button");
const cartCount = document.getElementById("cart-count");
const cartPanel = document.getElementById("cart-panel");
const cartItemsEl = document.getElementById("cart-items");
const cartTotalEl = document.getElementById("cart-total");
const closeCart = document.getElementById("close-cart");

function updateCartUI() {
    const cart = JSON.parse(sessionStorage.getItem("mg_cart") || "[]");
    cartItemsEl.innerHTML = "";
    let total = 0;
    let count = 0;

    if (cart.length === 0) {
        cartItemsEl.innerHTML = '<p class="muted">Seu carrinho está vazio.</p>';
    }

    cart.forEach(function (item, index) {
        const qty = parseInt(item.quantity || 1, 10);
        count += qty;
        const opts = item.options || {};
        const optsText = Object.keys(opts).map(function (key) {
            return key + ": " + opts[key];
        }).join(" · ");
        const row = document.createElement("div");
        row.className = "cart-item";
        row.innerHTML =
            "<div>" +
            "<strong>" + item.name + "</strong>" +
            (optsText ? '<div class="muted">' + optsText + "</div>" : "") +
            '<div class="cart-qty">' +
            '<button class="qty-btn" data-act="dec" data-index="' + index + '" aria-label="Diminuir">−</button>' +
            "<span>" + qty + "</span>" +
            '<button class="qty-btn" data-act="inc" data-index="' + index + '" aria-label="Aumentar">+</button>' +
            '<button class="qty-btn remove" data-act="rm" data-index="' + index + '">remover</button>' +
            "</div>" +
            "</div>" +
            "<div>R$ " + (item.price != null ? (Number(item.price) * qty).toFixed(2) : "0.00") + "</div>";
        cartItemsEl.appendChild(row);
        total += parseFloat(item.price || 0) * qty;
    });

    cartCount.textContent = count;
    cartTotalEl.textContent = total.toFixed(2);
}

cartItemsEl.addEventListener("click", function (event) {
    const button = event.target.closest(".qty-btn");
    if (!button) {
        return;
    }
    const index = parseInt(button.getAttribute("data-index"), 10);
    const action = button.getAttribute("data-act");
    const cart = JSON.parse(sessionStorage.getItem("mg_cart") || "[]");
    if (!cart[index]) {
        return;
    }
    if (action === "inc") {
        cart[index].quantity = (cart[index].quantity || 1) + 1;
    } else if (action === "dec") {
        cart[index].quantity = Math.max(1, (cart[index].quantity || 1) - 1);
    } else if (action === "rm") {
        cart.splice(index, 1);
    }
    persistCart(cart);
    updateCartUI();
});

cartButton.addEventListener("click", function () {
    cartPanel.setAttribute("aria-hidden", "false");
    updateCartUI();
});

closeCart.addEventListener("click", function () {
    cartPanel.setAttribute("aria-hidden", "true");
});

document.getElementById("checkout-btn").addEventListener("click", async function () {
    const cart = JSON.parse(sessionStorage.getItem("mg_cart") || "[]");
    if (!cart || cart.length === 0) {
        showToast("Carrinho vazio.");
        return;
    }

    const token = localStorage.getItem(TOKEN_KEY);
    try {
        const response = await fetch("/api/checkout", {
            method: "POST",
            headers: { "Content-Type": "application/json", Authorization: "Bearer " + token },
            body: JSON.stringify({ items: cart }),
        });
        const data = await response.json().catch(function () { return {}; });
        if (!response.ok) {
            showToast(data.error || "Falha no checkout");
            return;
        }
        if (data.init_point) {
            window.location.href = data.init_point;
            return;
        }
        showToast("Pedido registrado. ID: " + (data.order_id || "N/A"));
        persistCart([]);
        updateCartUI();
        cartPanel.setAttribute("aria-hidden", "true");
    } catch (error) {
        showToast("Erro de rede ao enviar pedido.");
    }
});

const ordersPanel = document.getElementById("orders-panel");
const ordersList = document.getElementById("orders-list");
document.getElementById("close-orders").addEventListener("click", function () {
    ordersPanel.setAttribute("aria-hidden", "true");
});
document.getElementById("orders-btn").addEventListener("click", async function () {
    ordersPanel.setAttribute("aria-hidden", "false");
    ordersList.innerHTML = '<p class="muted">Carregando...</p>';
    try {
        const response = await fetch("/api/orders/me", { headers: authHeaders() });
        if (!response.ok) {
            ordersList.innerHTML = '<p class="muted">Não foi possível carregar.</p>';
            return;
        }
        const orders = (await response.json()).orders || [];
        if (!orders.length) {
            ordersList.innerHTML = '<p class="muted">Você ainda não tem pedidos.</p>';
            return;
        }
        ordersList.innerHTML = "";
        orders.forEach(function (order) {
            const itemsText = (order.items || []).map(function (item) {
                return item.name + " x" + (item.quantity || 1);
            }).join(", ");
            const when = order.created_at ? new Date(order.created_at).toLocaleString("pt-BR") : "";
            const div = document.createElement("div");
            div.className = "cart-item";
            div.innerHTML =
                "<div>" +
                "<strong>Pedido #" + order.id + "</strong>" +
                '<div class="muted">' + itemsText + "</div>" +
                '<div class="muted">' + when + "</div>" +
                "</div>" +
                "<div>R$ " + Number(order.total).toFixed(2) + "</div>";
            ordersList.appendChild(div);
        });
    } catch (error) {
        ordersList.innerHTML = '<p class="muted">Erro de rede.</p>';
    }
});

function persistCart(cart) {
    sessionStorage.setItem("mg_cart", JSON.stringify(cart));
    fetch("/api/cart", {
        method: "PUT",
        headers: authHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify({ items: cart }),
    }).catch(function () { /* best-effort */ });
}

async function loadServerCart() {
    try {
        const response = await fetch("/api/cart", { headers: authHeaders() });
        if (response.ok) {
            const items = (await response.json()).items || [];
            const local = JSON.parse(sessionStorage.getItem("mg_cart") || "[]");
            if (local.length === 0 && items.length > 0) {
                sessionStorage.setItem("mg_cart", JSON.stringify(items));
            }
        }
    } catch (error) {
        /* best-effort */
    }
    updateCartUI();
}

async function handlePaymentReturn() {
    const params = new URLSearchParams(window.location.search);
    const payment = params.get("payment");
    if (!payment) {
        return;
    }
    const paymentId = params.get("payment_id") || params.get("collection_id");
    if (payment === "success" && paymentId) {
        try {
            const response = await fetch("/api/payments/confirm", {
                method: "POST",
                headers: authHeaders({ "Content-Type": "application/json" }),
                body: JSON.stringify({ payment_id: paymentId }),
            });
            const data = await response.json().catch(function () { return {}; });
            if (response.ok && data.status === "paid") {
                showToast("Pagamento aprovado! Pedido confirmado.");
                persistCart([]);
            } else {
                showToast("Pagamento " + (data.status || "pendente") + ".");
            }
        } catch (error) {
            showToast("Não foi possível confirmar o pagamento.");
        }
    } else if (payment === "failure") {
        showToast("Pagamento não concluído.");
    } else if (payment === "pending") {
        showToast("Pagamento pendente.");
    }
    window.history.replaceState({}, "", "/shop");
    updateCartUI();
}

loadProducts();
loadServerCart();
handlePaymentReturn();

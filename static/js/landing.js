/* landing.js — vitrine pública (sem login). Usa showToast (toast.js) e skeletonCards (ui.js). */
const catalog = document.getElementById("catalog");
const productCount = document.getElementById("product-count");

function createCard(product) {
    const card = document.createElement("article");
    card.className = "product-card";
    card.innerHTML =
        '<div class="product-img">' +
        '<img src="' + (product.image_url || "") + '" alt="' + product.name + '" loading="lazy"/>' +
        "</div>" +
        '<div class="product-body">' +
        (product.category ? '<span class="product-tag">' + product.category + "</span>" : "") +
        "<h4>" + product.name + "</h4>" +
        '<p class="muted">' + (product.description || "") + "</p>" +
        '<div class="product-footer">' +
        "<strong>R$ " + (product.price != null ? Number(product.price).toFixed(2) : "0.00") + "</strong>" +
        '<a class="btn" href="/login">Entrar para comprar</a>' +
        "</div>" +
        "</div>";
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

async function loadPublicProducts() {
    catalog.innerHTML = skeletonCards(6);
    try {
        const response = await fetch("/api/public/products");
        if (!response.ok) {
            showToast("Não foi possível carregar os produtos.");
            return;
        }
        const data = await response.json();
        const products = data.products || [];
        productCount.textContent = products.length;
        catalog.innerHTML = "";
        if (products.length === 0) {
            catalog.innerHTML = '<p class="muted">Em breve, novos produtos por aqui.</p>';
            return;
        }
        products.forEach(function (product) {
            catalog.appendChild(createCard(product));
        });
    } catch (error) {
        console.error("Erro ao carregar produtos", error);
        showToast("Erro ao carregar os produtos.");
    }
}

loadPublicProducts();

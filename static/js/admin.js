/* admin.js — painel administrativo (vanilla). Usa apiFetch (api.js), showToast (toast.js)
   e trapFocus (ui.js). Substitui alert() por toast; mantém confirm() na remoção. */
(function checkAuth() {
    if (!mgToken()) {
        window.location.href = "/login";
    }
})();

const tbody = document.querySelector(".products-table tbody");
const emptyState = document.getElementById("empty-state");
const productsCount = document.getElementById("products-count");
const modal = document.getElementById("product-modal");
const productForm = document.getElementById("product-form");
const cancelBtn = document.getElementById("cancel-product");
const modalTitle = document.getElementById("modal-title");
let currentProducts = [];
let editingId = null;
let releaseFocus = null;

document.getElementById("logout-btn").addEventListener("click", function () {
    mgClearToken();
    window.location.href = "/";
});

function renderProductRow(product) {
    const tr = document.createElement("tr");
    tr.innerHTML =
        "<td>" + product.id + "</td>" +
        "<td>" + product.name + "</td>" +
        "<td>" + (product.description || "") + "</td>" +
        "<td>R$ " + (product.price != null ? Number(product.price).toFixed(2) : "") + "</td>" +
        "<td>" + (product.image_url ? '<img src="' + product.image_url + '" alt="" class="tbl-img"/>' : "") + "</td>" +
        "<td>" +
        '<button class="btn btn-ghost edit-btn" data-id="' + product.id + '">Editar</button> ' +
        '<button class="btn btn-danger" data-id="' + product.id + '">Deletar</button>' +
        "</td>";
    return tr;
}

async function fetchAndRenderProducts(query) {
    tbody.innerHTML = "";
    emptyState.style.display = "none";
    try {
        const url = "/api/products" + (query ? "?q=" + encodeURIComponent(query) : "");
        const data = await apiFetch(url);
        const products = data.products || [];
        currentProducts = products;
        productsCount.textContent = products.length;
        if (products.length === 0) {
            emptyState.textContent = 'Nenhum produto encontrado. Clique em "Novo Produto" para adicionar.';
            emptyState.style.display = "block";
            return;
        }
        products.forEach(function (product) {
            tbody.appendChild(renderProductRow(product));
        });
    } catch (error) {
        console.error(error);
        emptyState.textContent = "Erro ao carregar produtos.";
        emptyState.style.display = "block";
    }
}

/* Converte { Cor: ["Preto","Roxo"] } para "Cor: Preto, Roxo" (uma por linha). */
function optionsToText(options) {
    return Object.keys(options || {})
        .map(function (key) {
            return key + ": " + (options[key] || []).join(", ");
        })
        .join("\n");
}

/* Converte "Cor: Preto, Roxo" (uma por linha) em { Cor: ["Preto","Roxo"] }. */
function parseOptions(text) {
    const options = {};
    (text || "").split("\n").forEach(function (line) {
        const idx = line.indexOf(":");
        if (idx === -1) {
            return;
        }
        const key = line.slice(0, idx).trim();
        const values = line.slice(idx + 1).split(",").map(function (value) {
            return value.trim();
        }).filter(Boolean);
        if (key && values.length) {
            options[key] = values;
        }
    });
    return options;
}

function openModal() {
    modal.setAttribute("aria-hidden", "false");
    releaseFocus = trapFocus(modal, closeModal);
}

function openModalForNew() {
    editingId = null;
    productForm.reset();
    modalTitle.textContent = "Novo Produto";
    openModal();
}

function openModalForEdit(product) {
    editingId = product.id;
    modalTitle.textContent = "Editar Produto";
    productForm.name.value = product.name || "";
    productForm.description.value = product.description || "";
    productForm.price.value = product.price != null ? product.price : "";
    productForm.image_url.value = product.image_url || "";
    productForm.category.value = product.category || "";
    productForm.stock.value = product.stock != null ? product.stock : 0;
    productForm.options.value = optionsToText(product.options);
    openModal();
}

function closeModal() {
    modal.setAttribute("aria-hidden", "true");
    productForm.reset();
    editingId = null;
    if (releaseFocus) {
        releaseFocus();
        releaseFocus = null;
    }
}

document.getElementById("new-product-btn").addEventListener("click", openModalForNew);
cancelBtn.addEventListener("click", closeModal);

document.getElementById("image-file").addEventListener("change", async function (event) {
    const file = event.target.files[0];
    if (!file) {
        return;
    }
    const formData = new FormData();
    formData.append("file", file);
    try {
        const data = await apiFetch("/api/upload", { method: "POST", body: formData });
        productForm.image_url.value = data.url;
        showToast("Imagem enviada!");
    } catch (error) {
        showToast(error.message || "Erro de rede no upload.");
    }
});

productForm.addEventListener("submit", async function (event) {
    event.preventDefault();
    const form = new FormData(productForm);
    const payload = {
        name: form.get("name"),
        description: form.get("description"),
        price: parseFloat(form.get("price")),
        image_url: form.get("image_url"),
        category: form.get("category"),
        options: parseOptions(form.get("options")),
        stock: parseInt(form.get("stock"), 10) || 0,
    };
    const method = editingId ? "PUT" : "POST";
    const url = editingId ? "/api/products/" + editingId : "/api/products";
    try {
        await apiFetch(url, {
            method: method,
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });
        closeModal();
        fetchAndRenderProducts();
        showToast("Produto salvo.");
    } catch (error) {
        showToast(error.message || "Falha ao salvar produto.");
    }
});

async function deleteProduct(id) {
    try {
        await apiFetch("/api/products/" + id, { method: "DELETE" });
        fetchAndRenderProducts();
        showToast("Produto removido.");
    } catch (error) {
        showToast(error.message || "Falha ao deletar produto.");
    }
}

tbody.addEventListener("click", function (event) {
    const button = event.target.closest("button");
    if (!button) {
        return;
    }
    const id = button.getAttribute("data-id");
    if (!id) {
        return;
    }
    if (button.classList.contains("edit-btn")) {
        const product = currentProducts.find(function (item) {
            return String(item.id) === String(id);
        });
        if (product) {
            openModalForEdit(product);
        }
        return;
    }
    if (button.classList.contains("btn-danger")) {
        if (confirm("Confirmar remoção do produto?")) {
            deleteProduct(id);
        }
    }
});

let searchTimer = null;
document.getElementById("search-products").addEventListener("input", function (event) {
    clearTimeout(searchTimer);
    const query = event.target.value.trim();
    searchTimer = setTimeout(function () {
        fetchAndRenderProducts(query);
    }, 300);
});

document.getElementById("preview-open-loja").addEventListener("click", async function () {
    if (!mgToken()) {
        showToast("Você precisa estar logado como admin para gerar o preview.");
        return;
    }
    try {
        const data = await apiFetch("/api/preview_token");
        localStorage.setItem("mgstreet_preview_token", data.token);
        window.open("/shop", "_blank");
    } catch (error) {
        showToast(error.message || "Erro ao solicitar token de preview.");
    }
});

async function fetchOrdersAndStats() {
    try {
        const stats = await apiFetch("/api/orders/stats");
        document.getElementById("stat-total-revenue").textContent =
            "R$ " + Number(stats.total_revenue || 0).toFixed(2);
        document.getElementById("stat-total-orders").textContent = stats.total_orders || 0;
    } catch (error) {
        console.error("Erro ao carregar estatísticas", error);
    }
    try {
        const data = await apiFetch("/api/orders");
        const ordersTbody = document.querySelector("#orders-table tbody");
        ordersTbody.innerHTML = "";
        (data.orders || []).forEach(function (order) {
            const itemsText = (order.items || []).map(function (item) {
                return item.name + " x" + (item.quantity || 1);
            }).join(", ");
            const tr = document.createElement("tr");
            tr.innerHTML =
                "<td>" + order.id + "</td>" +
                "<td>" + order.user_id + "</td>" +
                "<td>" + itemsText + "</td>" +
                "<td>R$ " + Number(order.total).toFixed(2) + "</td>" +
                "<td>" + (order.status || "pending") + "</td>" +
                "<td>" + (order.created_at || "") + "</td>";
            ordersTbody.appendChild(tr);
        });
    } catch (error) {
        console.error("Erro ao carregar pedidos", error);
    }
}

document.getElementById("refresh-orders").addEventListener("click", fetchOrdersAndStats);

fetchAndRenderProducts();
fetchOrdersAndStats();

/* api.js — wrapper único de fetch para o front (vanilla, sem libs).
   Injeta o token JWT (Authorization), parseia JSON e lança Error em status != 2xx.
   Carregar como <script> clássico antes dos módulos de página. */
function mgToken() {
    return localStorage.getItem("mgstreet_token");
}

function mgSetToken(token) {
    localStorage.setItem("mgstreet_token", token);
}

function mgClearToken() {
    localStorage.removeItem("mgstreet_token");
}

/* Faz a requisição com token e tratamento de erro padronizado.
   Lança Error (com .status e .data) quando a resposta não é 2xx. */
async function apiFetch(url, options) {
    options = options || {};
    const headers = Object.assign({}, options.headers || {});
    const token = mgToken();
    if (token) {
        headers["Authorization"] = "Bearer " + token;
    }
    const response = await fetch(url, Object.assign({}, options, { headers: headers }));
    let data = null;
    try {
        data = await response.json();
    } catch (parseError) {
        data = null;
    }
    if (!response.ok) {
        const error = new Error((data && data.error) || ("Erro " + response.status));
        error.status = response.status;
        error.data = data;
        throw error;
    }
    return data;
}

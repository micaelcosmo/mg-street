/* register.js — criação de conta. Usa apiFetch/showToast. */
document.getElementById("register-form").addEventListener("submit", async function (event) {
    event.preventDefault();
    const payload = {
        name: document.getElementById("name").value,
        email: document.getElementById("email").value,
        password: document.getElementById("password").value,
    };
    try {
        await apiFetch("/api/register", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });
        showToast("Conta criada! Redirecionando para o login...");
        setTimeout(function () {
            window.location.href = "/login";
        }, 900);
    } catch (error) {
        showToast(error.message || "Falha ao criar conta.");
    }
});

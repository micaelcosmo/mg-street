/* login.js — autenticação + carrossel + botões sociais (placeholder). Usa apiFetch/showToast. */
document.getElementById("login-form").addEventListener("submit", async function (event) {
    event.preventDefault();
    const email = document.getElementById("email").value;
    const password = document.getElementById("password").value;
    try {
        const data = await apiFetch("/api/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email: email, password: password }),
        });
        mgSetToken(data.token);
        const role = data.role || "user";
        window.location.href = role === "admin" ? "/admin" : "/shop";
    } catch (error) {
        showToast(error.message || "Falha na autenticação.");
    }
});

document.querySelectorAll(".social-btn").forEach(function (button) {
    button.addEventListener("click", function () {
        showToast("Integração em breve!");
    });
});

(function initCarousel() {
    const track = document.querySelector(".carousel-track");
    const slides = Array.prototype.slice.call(document.querySelectorAll(".carousel-slide"));
    const dotsContainer = document.querySelector(".carousel-dots");
    if (!track || slides.length === 0 || !dotsContainer) {
        return;
    }

    let current = 0;
    let timer = null;

    function update() {
        track.style.transform = "translateX(-" + current * 100 + "%)";
        const dots = Array.prototype.slice.call(dotsContainer.children);
        dots.forEach(function (dot, index) {
            dot.classList.toggle("active", index === current);
        });
    }

    function next() {
        current = (current + 1) % slides.length;
        update();
    }

    function restartTimer() {
        if (timer) {
            clearInterval(timer);
        }
        timer = setInterval(next, 3500);
    }

    function goTo(index) {
        current = index % slides.length;
        update();
        restartTimer();
    }

    slides.forEach(function (_, index) {
        const dot = document.createElement("button");
        if (index === 0) {
            dot.classList.add("active");
        }
        dot.addEventListener("click", function () {
            goTo(index);
        });
        dotsContainer.appendChild(dot);
    });

    update();
    restartTimer();
})();

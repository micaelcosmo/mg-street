/* ui.js — helpers de UI (vanilla). showToast vem de toast.js (carregado antes).
   Skeleton e foco preso em modal, usados pelos módulos de página. */

/* Marca de produtos "fantasma" para o estado de carregamento do catálogo. */
function skeletonCards(count) {
    const total = count || 6;
    let html = "";
    for (let i = 0; i < total; i += 1) {
        html +=
            '<div class="product-card product-card--skeleton" aria-hidden="true">' +
            '<div class="product-card__media skeleton"></div>' +
            '<div class="skeleton skeleton--line"></div>' +
            '<div class="skeleton skeleton--line skeleton--short"></div>' +
            "</div>";
    }
    return html;
}

/* Prende o foco do teclado dentro de um modal aberto e fecha no Esc.
   Retorna uma função para desligar o aprisionamento ao fechar. */
function trapFocus(modal, onClose) {
    const selector =
        'a[href], button:not([disabled]), input:not([disabled]), select, textarea, [tabindex]:not([tabindex="-1"])';

    function handleKeydown(event) {
        if (event.key === "Escape") {
            onClose();
            return;
        }
        if (event.key !== "Tab") {
            return;
        }
        const focusable = Array.prototype.slice.call(modal.querySelectorAll(selector));
        if (focusable.length === 0) {
            return;
        }
        const first = focusable[0];
        const last = focusable[focusable.length - 1];
        if (event.shiftKey && document.activeElement === first) {
            event.preventDefault();
            last.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
            event.preventDefault();
            first.focus();
        }
    }

    modal.addEventListener("keydown", handleKeydown);
    const firstField = modal.querySelector(selector);
    if (firstField) {
        firstField.focus();
    }
    return function release() {
        modal.removeEventListener("keydown", handleKeydown);
    };
}

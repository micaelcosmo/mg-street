// Toast compartilhado (usado por login.html e shop.html).
function showToast(message) {
    const existing = document.querySelector('.mg-toast');
    if (existing) existing.remove();

    const div = document.createElement('div');
    div.className = 'mg-toast';
    div.setAttribute('role', 'status');
    div.setAttribute('aria-live', 'polite');
    div.textContent = message;
    document.body.appendChild(div);
    setTimeout(() => div.classList.add('visible'), 10);
    setTimeout(() => div.classList.remove('visible'), 2600);
    setTimeout(() => div.remove(), 3000);
}

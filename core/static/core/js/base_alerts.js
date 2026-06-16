(() => {
    const alerts = Array.from(document.querySelectorAll('[data-alert]'));
    if (!alerts.length) return;

    alerts.forEach(alertEl => {
        const btn = alertEl.querySelector('[data-alert-dismiss]');
        if (!btn) return;
        btn.addEventListener('click', () => {
            alertEl.remove();
        });
    });
})();

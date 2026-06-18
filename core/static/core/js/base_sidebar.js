(() => {
    const sidebar = document.getElementById('appSidebar');
    const toggleBtn = document.getElementById('sidebarToggle');
    if (!sidebar || !toggleBtn) return;

    const userMeta = document.getElementById('sidebarUserMeta');
    const iconEl = toggleBtn.querySelector('[data-sidebar-toggle-icon]');
    const labels = Array.from(sidebar.querySelectorAll('.sidebar-label'));
    const sections = Array.from(sidebar.querySelectorAll('.sidebar-section'));
    const links = Array.from(sidebar.querySelectorAll('.sidebar-link'));
    const submenus = Array.from(sidebar.querySelectorAll('.sidebar-submenu'));

    // Set a title tooltip for collapsed mode (once)
    links.forEach(el => {
        if (!(el instanceof HTMLAnchorElement)) return;
        const label = el.querySelector('.sidebar-label');
        const text = (label ? label.textContent : el.textContent || '').trim();
        if (text && !el.getAttribute('title')) el.setAttribute('title', text);
    });

    const KEY = 'tbsm.sidebarCollapsed';
    const readCollapsed = () => {
        try { return localStorage.getItem(KEY) === '1'; } catch { return false; }
    };
    const writeCollapsed = (v) => {
        try { localStorage.setItem(KEY, v ? '1' : '0'); } catch {}
    };

    const apply = (collapsed) => {
        if (collapsed) {
            sidebar.classList.remove('w-72');
            sidebar.classList.add('w-20');
            if (userMeta) userMeta.classList.add('hidden');
            labels.forEach(el => el.classList.add('hidden'));
            sections.forEach(el => el.classList.add('hidden'));
            submenus.forEach(el => {
                el.classList.remove('pl-6', 'ml-4', 'border-l');
            });
            links.forEach(a => {
                a.classList.add('justify-center');
                a.classList.remove('gap-2');
            });
            if (iconEl) iconEl.textContent = '›';
            toggleBtn.setAttribute('aria-pressed', 'true');
        } else {
            sidebar.classList.remove('w-20');
            sidebar.classList.add('w-72');
            if (userMeta) userMeta.classList.remove('hidden');
            labels.forEach(el => el.classList.remove('hidden'));
            sections.forEach(el => el.classList.remove('hidden'));
            submenus.forEach(el => {
                el.classList.add('pl-6', 'ml-4', 'border-l', 'border-slate-800');
            });
            links.forEach(a => {
                a.classList.remove('justify-center');
                a.classList.add('gap-2');
            });
            if (iconEl) iconEl.textContent = '‹';
            toggleBtn.setAttribute('aria-pressed', 'false');
        }
    };

    apply(readCollapsed());

    toggleBtn.addEventListener('click', () => {
        const collapsed = sidebar.classList.contains('w-20');
        const next = !collapsed;
        writeCollapsed(next);
        apply(next);
    });
})();

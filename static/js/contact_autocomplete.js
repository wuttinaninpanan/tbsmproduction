(() => {
	const cfg = window.CONTACT_AUTOCOMPLETE || {};
	const SEARCH_URL = cfg.searchUrl || '';

	const debounce = (fn, ms) => {
		let t;
		return (...args) => {
			clearTimeout(t);
			t = setTimeout(() => fn.apply(null, args), ms);
		};
	};

	const escapeHtml = (s) => String(s || '').replace(/[&<>"']/g, (c) => ({
		'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
	}[c]));

	const initWidget = (root) => {
		const type = root.dataset.type || 'item';
		const idField = root.querySelector('[data-ac-id]');
		const input = root.querySelector('[data-ac-input]');
		const results = root.querySelector('[data-ac-results]');
		const hint = root.querySelector('[data-ac-hint]');
		if (!idField || !input || !results) return;

		const closeResults = () => {
			results.classList.add('hidden');
			results.innerHTML = '';
		};

		const setHint = (text, ok) => {
			if (!hint) return;
			hint.textContent = text;
			hint.classList.toggle('text-emerald-600', !!ok);
			hint.classList.toggle('text-gray-500', !ok);
		};

		const renderResults = (items) => {
			if (!items.length) {
				results.innerHTML = '<div class="px-3 py-2 text-sm text-gray-500">ไม่พบรายการ</div>';
				results.classList.remove('hidden');
				return;
			}
			results.innerHTML = items.map(it => type === 'line' ? `
				<button type="button" data-id="${escapeHtml(it.id)}"
					data-label="${escapeHtml(it.line_name)}"
					class="w-full text-left px-3 py-2 hover:bg-gray-100 border-b border-gray-100 last:border-b-0">
					<div class="text-sm font-semibold text-gray-900">${escapeHtml(it.line_name || '-')}</div>
				</button>
			` : `
				<button type="button" data-id="${escapeHtml(it.id)}"
					data-sd="${escapeHtml(it.sd_code)}"
					data-pn="${escapeHtml(it.part_number)}"
					data-name="${escapeHtml(it.part_name)}"
					data-code="${escapeHtml(it.item_code)}"
					class="w-full text-left px-3 py-2 hover:bg-gray-100 border-b border-gray-100 last:border-b-0">
					<div class="text-sm font-semibold text-gray-900">${escapeHtml(it.sd_code || it.part_number || '-')} <span class="text-gray-500 font-normal">— ${escapeHtml(it.part_number || '-')}</span></div>
					<div class="text-xs text-gray-600">${escapeHtml(it.part_name || '')}${it.item_code ? ' · ' + escapeHtml(it.item_code) : ''}</div>
				</button>
			`).join('');
			results.classList.remove('hidden');
			results.querySelectorAll('button[data-id]').forEach(btn => {
				btn.addEventListener('click', () => {
					idField.value = btn.dataset.id || '';
					if (type === 'line') {
						input.value = btn.dataset.label || '';
					} else {
						const parts = [btn.dataset.sd, btn.dataset.pn, btn.dataset.name].filter(Boolean);
						input.value = parts.join(' — ');
					}
					setHint('เลือกแล้ว', true);
					closeResults();
				});
			});
		};

		const doSearch = debounce(async (q) => {
			if (!q) { closeResults(); return; }
			try {
				const url = new URL(SEARCH_URL, window.location.origin);
				url.searchParams.set('q', q);
				url.searchParams.set('type', type);
				const res = await fetch(url.toString(), { headers: { 'X-Requested-With': 'XMLHttpRequest' } });
				if (!res.ok) { closeResults(); return; }
				const data = await res.json();
				renderResults(data.results || []);
			} catch (e) {
				closeResults();
			}
		}, 200);

		input.addEventListener('input', () => {
			idField.value = '';
			setHint('พิมพ์เพื่อค้นหา', false);
			doSearch(input.value.trim());
		});
		input.addEventListener('focus', () => {
			if (input.value.trim() && results.innerHTML) results.classList.remove('hidden');
		});
		document.addEventListener('click', (e) => {
			if (!root.contains(e.target)) closeResults();
		});
	};

	const init = () => {
		document.querySelectorAll('[data-autocomplete]').forEach(initWidget);
	};

	if (document.readyState === 'loading') {
		document.addEventListener('DOMContentLoaded', init);
	} else {
		init();
	}
})();

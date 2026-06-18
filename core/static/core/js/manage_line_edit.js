(() => {
	const cfg = window.MANAGE_LINE_EDIT || {};
	const SEARCH_URL = cfg.searchUrl || '';
	const LINE_ID = cfg.lineId || '';

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

	const init = () => {
		// ---------- Item autocomplete ----------
		const input = document.getElementById('itemSearchInput');
		const results = document.getElementById('itemSearchResults');
		const hint = document.getElementById('itemSearchHint');
		const itemIdField = document.getElementById('addItemId');
		const stageSelect = document.getElementById('addStageId');
		const submitBtn = document.getElementById('addItemSubmit');

		const updateSubmitState = () => {
			const ok = !!(itemIdField.value && stageSelect.value);
			submitBtn.disabled = !ok;
		};

		const closeResults = () => {
			results.classList.add('hidden');
			results.innerHTML = '';
		};

		const renderResults = (items) => {
			if (!items.length) {
				results.innerHTML = '<div class="px-3 py-2 text-sm text-slate-500">ไม่พบรายการ</div>';
				results.classList.remove('hidden');
				return;
			}
			results.innerHTML = items.map(it => `
				<button type="button" data-id="${escapeHtml(it.id)}"
					data-label="${escapeHtml(it.sd_code || it.part_number || it.part_name)}"
					data-sd="${escapeHtml(it.sd_code)}"
					data-pn="${escapeHtml(it.part_number)}"
					data-name="${escapeHtml(it.part_name)}"
					class="w-full text-left px-3 py-2 hover:bg-slate-100 border-b border-slate-100 last:border-b-0">
					<div class="text-sm font-semibold text-slate-900">${escapeHtml(it.sd_code || '-')} <span class="text-slate-500 font-normal">— ${escapeHtml(it.part_number || '-')}</span></div>
					<div class="text-xs text-slate-600">${escapeHtml(it.part_name || '')}${it.item_code ? ' · ' + escapeHtml(it.item_code) : ''}</div>
				</button>
			`).join('');
			results.classList.remove('hidden');
			results.querySelectorAll('button[data-id]').forEach(btn => {
				btn.addEventListener('click', () => {
					itemIdField.value = btn.dataset.id || '';
					const sd = btn.dataset.sd || '';
					const pn = btn.dataset.pn || '';
					const nm = btn.dataset.name || '';
					input.value = [sd, pn, nm].filter(Boolean).join(' — ');
					hint.textContent = 'เลือกแล้ว';
					hint.classList.remove('text-slate-500');
					hint.classList.add('text-emerald-600');
					closeResults();
					updateSubmitState();
				});
			});
		};

		const doSearch = debounce(async (q) => {
			if (!q) {
				closeResults();
				return;
			}
			try {
				const url = new URL(SEARCH_URL, window.location.origin);
				url.searchParams.set('q', q);
				if (LINE_ID) url.searchParams.set('line_id', LINE_ID);
				const res = await fetch(url.toString(), { headers: { 'X-Requested-With': 'XMLHttpRequest' } });
				if (!res.ok) {
					closeResults();
					return;
				}
				const data = await res.json();
				renderResults(data.results || []);
			} catch (e) {
				closeResults();
			}
		}, 200);

		if (input) {
			input.addEventListener('input', () => {
				const q = input.value.trim();
				// User started typing again — clear previously selected item
				itemIdField.value = '';
				hint.textContent = 'พิมพ์อย่างน้อย 1 ตัวอักษรเพื่อค้นหา';
				hint.classList.remove('text-emerald-600');
				hint.classList.add('text-slate-500');
				updateSubmitState();
				doSearch(q);
			});
			input.addEventListener('focus', () => {
				const q = input.value.trim();
				if (q && results.innerHTML) {
					results.classList.remove('hidden');
				}
			});
			document.addEventListener('click', (e) => {
				if (!results.contains(e.target) && e.target !== input) {
					closeResults();
				}
			});
		}
		if (stageSelect) {
			stageSelect.addEventListener('change', updateSubmitState);
		}
		updateSubmitState();

		// ---------- Inline stage edit ----------
		document.querySelectorAll('.stageEditForm').forEach(form => {
			const select = form.querySelector('.stageSelect');
			const saveBtn = form.querySelector('.stageSaveBtn');
			if (!select || !saveBtn) return;
			select.addEventListener('change', () => {
				const changed = select.value !== select.dataset.original;
				saveBtn.classList.toggle('hidden', !changed);
			});
		});

		// ---------- Delete item modal ----------
		const deleteModal = document.getElementById('deleteItemModal');
		const deleteLabel = document.getElementById('deleteItemLabel');
		const deleteIdField = document.getElementById('deleteItemLineId');

		const openModal = (el) => {
			if (!el) return;
			el.classList.remove('hidden');
			el.classList.add('flex');
		};
		const closeModal = (el) => {
			if (!el) return;
			el.classList.add('hidden');
			el.classList.remove('flex');
		};

		document.querySelectorAll('[data-open-delete-item]').forEach(btn => {
			btn.addEventListener('click', () => {
				deleteIdField.value = btn.dataset.id || '';
				deleteLabel.textContent = btn.dataset.label || '';
				openModal(deleteModal);
			});
		});
		document.querySelectorAll('[data-modal-close]').forEach(btn => {
			btn.addEventListener('click', () => closeModal(deleteModal));
		});
		document.querySelectorAll('[data-modal-backdrop]').forEach(bg => {
			bg.addEventListener('click', () => closeModal(deleteModal));
		});
	};

	if (document.readyState === 'loading') {
		document.addEventListener('DOMContentLoaded', init);
	} else {
		init();
	}
})();

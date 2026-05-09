(() => {
	const init = () => {
		const csrfForm = document.getElementById('bomTemplateCsrf');
		const csrfToken = csrfForm ? csrfForm.querySelector('input[name="csrfmiddlewaretoken"]').value : '';

		function getRowValues(row) {
			return {
				category_id: (row.querySelector('select[data-field="category_id"]') || {}).value || '',
				stage_id: (row.querySelector('select[data-field="stage_id"]') || {}).value || '',
				line_id: (row.querySelector('select[data-field="line_id"]') || {}).value || '',
			};
		}

		function flashRow(row, ok) {
			const bg = ok ? 'bg-emerald-50' : 'bg-rose-50';
			row.classList.add(bg);
			setTimeout(() => row.classList.remove(bg), 1200);
		}

		async function saveRow(btn) {
			const itemId = btn.dataset.itemId || '';
			if (!itemId) {
				alert('ไม่พบ Item ID');
				return;
			}
			const row = btn.closest('tr');
			const values = getRowValues(row);

			const fd = new FormData();
			fd.append('csrfmiddlewaretoken', csrfToken);
			fd.append('action', 'save_row');
			fd.append('item_id', itemId);
			fd.append('category_id', values.category_id);
			fd.append('stage_id', values.stage_id);
			fd.append('line_id', values.line_id);

			const original = btn.textContent;
			btn.disabled = true;
			btn.textContent = 'Saving...';

			try {
				const res = await fetch(window.location.pathname, {
					method: 'POST',
					body: fd,
					headers: { 'X-Requested-With': 'XMLHttpRequest' },
					credentials: 'same-origin',
				});
				let data;
				try {
					data = await res.json();
				} catch {
					data = { ok: false, error: 'Invalid server response' };
				}
				if (res.ok && data && data.ok) {
					flashRow(row, true);
					const codeCell = row.querySelector('[data-row-cell="item_code"]');
					if (codeCell && typeof data.item_code === 'string') {
						codeCell.textContent = data.item_code || '-';
					}
					btn.textContent = 'Saved';
					setTimeout(() => {
						btn.textContent = original;
						btn.disabled = false;
					}, 1200);
				} else {
					flashRow(row, false);
					btn.textContent = original;
					btn.disabled = false;
					alert((data && data.error) || 'บันทึกไม่สำเร็จ');
				}
			} catch (err) {
				flashRow(row, false);
				btn.textContent = original;
				btn.disabled = false;
				alert('เกิดข้อผิดพลาด: ' + (err && err.message ? err.message : err));
			}
		}

		document.addEventListener('click', (e) => {
			const btn = e.target.closest('[data-save-row]');
			if (!btn) return;
			e.preventDefault();
			saveRow(btn);
		});

		// Excel import: hidden file input, triggered by visible button.
		const importBtn = document.getElementById('bomImportBtn');
		const importFile = document.getElementById('bomImportFile');
		const importForm = document.getElementById('bomImportForm');
		if (importBtn && importFile && importForm) {
			importBtn.addEventListener('click', () => importFile.click());
			importFile.addEventListener('change', () => {
				if (importFile.files && importFile.files.length > 0) {
					importForm.submit();
				}
			});
		}
	};

	if (document.readyState === 'loading') {
		document.addEventListener('DOMContentLoaded', init);
	} else {
		init();
	}
})();

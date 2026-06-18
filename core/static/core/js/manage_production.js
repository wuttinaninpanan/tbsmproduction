(() => {
	const init = () => {
		const actionForm = document.getElementById('actionForm');
		const actionField = document.getElementById('actionField');
		const idField = document.getElementById('idField');
		const deleteModal = document.getElementById('deleteModal');
		const deleteLabel = document.getElementById('deleteLabel');

		function openModal(el) {
			if (!el) return;
			el.classList.remove('hidden');
			el.classList.add('flex');
		}
		function closeModal(el) {
			if (!el) return;
			el.classList.add('hidden');
			el.classList.remove('flex');
		}
		document.querySelectorAll('[data-modal-close]').forEach(btn => btn.addEventListener('click', () => closeModal(deleteModal)));
		document.querySelectorAll('[data-modal-backdrop]').forEach(bg => bg.addEventListener('click', () => closeModal(deleteModal)));
		document.addEventListener('keydown', (e) => { if (e.key === 'Escape') closeModal(deleteModal); });

		// Expand / collapse detail rows. Ignore clicks on interactive controls.
		document.querySelectorAll('tr[data-row-toggle]').forEach(tr => {
			tr.addEventListener('click', (e) => {
				if (e.target.closest('a, button, input, label, select, textarea')) return;
				const target = document.getElementById(tr.dataset.target);
				if (!target) return;
				target.classList.toggle('hidden');
				const chevron = tr.querySelector('[data-chevron]');
				if (chevron) chevron.classList.toggle('rotate-90');
			});
		});

		// Bulk selection
		const selectAll = document.getElementById('selectAllRows');
		const bulkDeleteBtn = document.getElementById('bulkDeleteBtn');
		function updateBulkState() {
			const checked = Array.from(document.querySelectorAll('.rowCheckbox')).filter(cb => cb.checked);
			if (bulkDeleteBtn) bulkDeleteBtn.disabled = checked.length === 0;
		}
		if (selectAll) {
			selectAll.addEventListener('change', () => {
				document.querySelectorAll('.rowCheckbox').forEach(cb => cb.checked = selectAll.checked);
				updateBulkState();
			});
		}
		document.querySelectorAll('.rowCheckbox').forEach(cb => cb.addEventListener('change', updateBulkState));
		updateBulkState();

		if (bulkDeleteBtn) {
			bulkDeleteBtn.addEventListener('click', () => {
				const ids = Array.from(document.querySelectorAll('.rowCheckbox')).filter(cb => cb.checked).map(cb => cb.dataset.id);
				if (!ids.length) return;
				if (!confirm(`ต้องการลบ ${ids.length} รายการ (รวม Defect/Scrap ที่เกี่ยวข้อง) หรือไม่?`)) return;
				actionField.value = 'bulk_delete';
				Array.from(actionForm.querySelectorAll('input[name="bulk_id"]')).forEach(n => n.remove());
				ids.forEach(id => {
					const inp = document.createElement('input');
					inp.type = 'hidden';
					inp.name = 'bulk_id';
					inp.value = id;
					actionForm.appendChild(inp);
				});
				actionForm.submit();
			});
		}

		// Single delete
		document.querySelectorAll('[data-open-delete]').forEach(btn => {
			btn.addEventListener('click', () => {
				idField.value = btn.dataset.id || '';
				if (deleteLabel) deleteLabel.textContent = btn.dataset.label || '';
				openModal(deleteModal);
			});
		});
		const deleteSubmit = document.getElementById('deleteSubmit');
		if (deleteSubmit) {
			deleteSubmit.addEventListener('click', () => {
				actionField.value = 'delete';
				actionForm.submit();
			});
		}

		// Date range pickers (start / end)
		if (typeof flatpickr !== 'undefined') {
			flatpickr('#date_from_picker', { locale: 'th', dateFormat: 'Y-m-d', allowInput: true, wrap: false });
			flatpickr('#date_to_picker', { locale: 'th', dateFormat: 'Y-m-d', allowInput: true, wrap: false });
		}
	};

	if (document.readyState === 'loading') {
		document.addEventListener('DOMContentLoaded', init);
	} else {
		init();
	}
})();

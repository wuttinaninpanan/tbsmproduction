(() => {
	const init = () => {
		const actionForm = document.getElementById('actionForm');
		const actionField = document.getElementById('actionField');
		const idField = document.getElementById('idField');
		const nameThField = document.getElementById('nameThField');
		const nameEnField = document.getElementById('nameEnField');
		const nameJpField = document.getElementById('nameJpField');
		const descThField = document.getElementById('descThField');
		const descEnField = document.getElementById('descEnField');
		const descJpField = document.getElementById('descJpField');

		const addModal = document.getElementById('addModal');
		const editModal = document.getElementById('editModal');
		const deleteModal = document.getElementById('deleteModal');
		const deleteLabel = document.getElementById('deleteLabel');

		// Toolbar: import + bulk delete
		const importBtn = document.getElementById('importBtn');
		const importFile = document.getElementById('importFile');
		const importForm = document.getElementById('importForm');
		if (importBtn && importFile && importForm) {
			importBtn.addEventListener('click', () => importFile.click());
			importFile.addEventListener('change', () => {
				if (importFile.files && importFile.files.length > 0) {
					importForm.submit();
				}
			});
		}

		const selectAllRows = document.getElementById('selectAllRows');
		const bulkDeleteBtn = document.getElementById('bulkDeleteBtn');
		const rowCheckboxes = Array.from(document.querySelectorAll('.rowCheckbox'));

		function selectedIds() {
			return rowCheckboxes.filter(cb => cb.checked).map(cb => cb.dataset.id).filter(Boolean);
		}
		function syncBulkState() {
			if (!bulkDeleteBtn) return;
			bulkDeleteBtn.disabled = selectedIds().length === 0;
		}
		if (selectAllRows) {
			selectAllRows.addEventListener('change', () => {
				rowCheckboxes.forEach(cb => { cb.checked = !!selectAllRows.checked; });
				syncBulkState();
			});
		}
		rowCheckboxes.forEach(cb => cb.addEventListener('change', syncBulkState));
		if (bulkDeleteBtn) {
			bulkDeleteBtn.addEventListener('click', () => {
				const ids = selectedIds();
				if (ids.length === 0) return;
				// Clear previous bulk inputs
				Array.from(actionForm.querySelectorAll('input[name="bulk_id"]')).forEach(n => n.remove());
				actionField.value = 'bulk_delete_defects';
				idField.value = '';
				nameThField.value = '';
				nameEnField.value = '';
				nameJpField.value = '';
				descThField.value = '';
				descEnField.value = '';
				descJpField.value = '';
				ids.forEach(id => {
					const input = document.createElement('input');
					input.type = 'hidden';
					input.name = 'bulk_id';
					input.value = String(id);
					actionForm.appendChild(input);
				});
				actionForm.submit();
				setTimeout(function(){ window.location.reload(); }, 1200);
			});
		}

		function openModal(el){ el.classList.remove('hidden'); el.classList.add('flex'); }
		function closeModal(el){ el.classList.add('hidden'); el.classList.remove('flex'); }

		const addNameTh = document.getElementById('addNameTh');
		const addNameEn = document.getElementById('addNameEn');
		const addNameJp = document.getElementById('addNameJp');
		const addDescTh = document.getElementById('addDescTh');
		const addDescEn = document.getElementById('addDescEn');
		const addDescJp = document.getElementById('addDescJp');

		const editNameTh = document.getElementById('editNameTh');
		const editNameEn = document.getElementById('editNameEn');
		const editNameJp = document.getElementById('editNameJp');
		const editDescTh = document.getElementById('editDescTh');
		const editDescEn = document.getElementById('editDescEn');
		const editDescJp = document.getElementById('editDescJp');

		document.getElementById('openAddModal').addEventListener('click', () => {
			addNameTh.value = '';
			addNameEn.value = '';
			addNameJp.value = '';
			addDescTh.value = '';
			addDescEn.value = '';
			addDescJp.value = '';
			openModal(addModal);
			setTimeout(() => addNameEn.focus(), 0);
		});

		document.querySelectorAll('[data-open-edit]').forEach(btn => {
			btn.addEventListener('click', () => {
				idField.value = btn.dataset.id || '';
				editNameTh.value = btn.dataset.nameTh || '';
				editNameEn.value = btn.dataset.nameEn || '';
				editNameJp.value = btn.dataset.nameJp || '';
				editDescTh.value = btn.dataset.descriptionTh || '';
				editDescEn.value = btn.dataset.descriptionEn || '';
				editDescJp.value = btn.dataset.descriptionJp || '';
				openModal(editModal);
				setTimeout(() => editNameEn.focus(), 0);
			});
		});

		document.querySelectorAll('[data-open-delete]').forEach(btn => {
			btn.addEventListener('click', () => {
				idField.value = btn.dataset.id || '';
				deleteLabel.textContent = btn.dataset.label || '';
				openModal(deleteModal);
			});
		});

		document.querySelectorAll('[data-modal-close]').forEach(btn => {
			btn.addEventListener('click', () => {
				closeModal(addModal);
				closeModal(editModal);
				closeModal(deleteModal);
			});
		});
		document.querySelectorAll('[data-modal-backdrop]').forEach(bg => {
			bg.addEventListener('click', () => {
				closeModal(addModal);
				closeModal(editModal);
				closeModal(deleteModal);
			});
		});

		document.getElementById('addSubmit').addEventListener('click', () => {
			actionField.value = 'create_defect';
			idField.value = '';
			nameThField.value = (addNameTh.value || '').trim();
			nameEnField.value = (addNameEn.value || '').trim();
			nameJpField.value = (addNameJp.value || '').trim();
			descThField.value = (addDescTh.value || '').trim();
			descEnField.value = (addDescEn.value || '').trim();
			descJpField.value = (addDescJp.value || '').trim();
			actionForm.submit();
			setTimeout(function(){ window.location.reload(); }, 1200);
		});

		document.getElementById('editSubmit').addEventListener('click', () => {
			actionField.value = 'update_defect';
			nameThField.value = (editNameTh.value || '').trim();
			nameEnField.value = (editNameEn.value || '').trim();
			nameJpField.value = (editNameJp.value || '').trim();
			descThField.value = (editDescTh.value || '').trim();
			descEnField.value = (editDescEn.value || '').trim();
			descJpField.value = (editDescJp.value || '').trim();
			actionForm.submit();
			setTimeout(function(){ window.location.reload(); }, 1200);
		});

		document.getElementById('deleteSubmit').addEventListener('click', () => {
			actionField.value = 'delete_defect';
			actionForm.submit();
		});
	};

	if (document.readyState === 'loading') {
		document.addEventListener('DOMContentLoaded', init);
	} else {
		init();
	}
})();

(() => {
	const init = () => {
		function tsSet(id, val) {
			var el = document.getElementById(id);
			if (!el) return;
			if (el.tomselect) { el.tomselect.setValue(val || ''); } else { el.value = val || ''; }
		}

		const actionForm = document.getElementById('actionForm');
		const actionField = document.getElementById('actionField');
		const idField = document.getElementById('idField');
		const categoryIdField = document.getElementById('categoryIdField');
		const defectModeIdField = document.getElementById('defectModeIdField');
		const titleField = document.getElementById('titleField');
		const descriptionField = document.getElementById('descriptionField');
		const isInlistField = document.getElementById('isInlistField');

		const addModal = document.getElementById('addModal');
		const editModal = document.getElementById('editModal');
		const deleteModal = document.getElementById('deleteModal');

		// Toolbar: import
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

		// Bulk selection
		const selectAll = document.getElementById('selectAllRows');
		const bulkDeleteBtn = document.getElementById('bulkDeleteBtn');
		function updateBulkState() {
			const checked = Array.from(document.querySelectorAll('.rowCheckbox')).filter(cb => cb.checked);
			bulkDeleteBtn.disabled = checked.length === 0;
		}
		if (selectAll) {
			selectAll.addEventListener('change', () => {
				document.querySelectorAll('.rowCheckbox').forEach(cb => cb.checked = selectAll.checked);
				updateBulkState();
			});
		}
		document.querySelectorAll('.rowCheckbox').forEach(cb => cb.addEventListener('change', updateBulkState));
		updateBulkState();

		bulkDeleteBtn.addEventListener('click', () => {
			const ids = Array.from(document.querySelectorAll('.rowCheckbox')).filter(cb => cb.checked).map(cb => cb.dataset.id);
			if (!ids.length) return;
			if (!confirm(`ต้องการลบ ${ids.length} รายการหรือไม่?`)) return;
			actionField.value = 'bulk_delete_defect_by_category';
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

		// Add
		document.getElementById('openAddModal').addEventListener('click', () => openModal(addModal));
		document.getElementById('addSubmit').addEventListener('click', () => {
			actionField.value = 'create';
			idField.value = '';
			categoryIdField.value = (document.getElementById('addCategory').value || '').trim();
			defectModeIdField.value = (document.getElementById('addDefect').value || '').trim();
			titleField.value = (document.getElementById('addTitle').value || '').trim();
			descriptionField.value = (document.getElementById('addDescription').value || '').trim();
			isInlistField.value = document.getElementById('addInlist').checked ? '1' : '0';
			actionForm.submit();
		});

		// Edit
		const editLabel = document.getElementById('editLabel');
		document.querySelectorAll('[data-open-edit]').forEach(btn => {
			btn.addEventListener('click', () => {
				idField.value = btn.dataset.id || '';
				document.getElementById('editCategory').value = btn.dataset.categoryId || '';
				tsSet('editDefect', btn.dataset.defectModeId || '');
				document.getElementById('editTitle').value = btn.dataset.title || '';
				document.getElementById('editDescription').value = btn.dataset.description || '';
				document.getElementById('editInlist').checked = (btn.dataset.isInlist || '0') === '1';
				editLabel.textContent = btn.dataset.label || '';
				openModal(editModal);
			});
		});
		document.getElementById('editSubmit').addEventListener('click', () => {
			actionField.value = 'update';
			categoryIdField.value = (document.getElementById('editCategory').value || '').trim();
			defectModeIdField.value = (document.getElementById('editDefect').value || '').trim();
			titleField.value = (document.getElementById('editTitle').value || '').trim();
			descriptionField.value = (document.getElementById('editDescription').value || '').trim();
			isInlistField.value = document.getElementById('editInlist').checked ? '1' : '0';
			actionForm.submit();
		});

		// Delete
		const deleteLabel = document.getElementById('deleteLabel');
		document.querySelectorAll('[data-open-delete]').forEach(btn => {
			btn.addEventListener('click', () => {
				idField.value = btn.dataset.id || '';
				deleteLabel.textContent = btn.dataset.label || '';
				openModal(deleteModal);
			});
		});
		document.getElementById('deleteSubmit').addEventListener('click', () => {
			actionField.value = 'delete';
			actionForm.submit();
		});
	};

	if (document.readyState === 'loading') {
		document.addEventListener('DOMContentLoaded', init);
	} else {
		init();
	}
})();

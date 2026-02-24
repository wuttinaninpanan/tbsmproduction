(() => {
	const init = () => {
		const actionForm = document.getElementById('actionForm');
		const actionField = document.getElementById('actionField');
		const idField = document.getElementById('idField');
		const itemIdField = document.getElementById('itemIdField');
		const revisionField = document.getElementById('revisionField');
		const eciField = document.getElementById('eciField');
		const scrapField = document.getElementById('scrapField');

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
			actionField.value = 'bulk_delete_boms';
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
			itemIdField.value = (document.getElementById('addItem').value || '').trim();
			revisionField.value = (document.getElementById('addRevision').value || '').trim();
			eciField.value = (document.getElementById('addEci').value || '').trim();
			scrapField.value = (document.getElementById('addScrap').value || '').trim();
			actionForm.submit();
		});

		// Edit
		const editLabel = document.getElementById('editLabel');
		document.querySelectorAll('[data-open-edit]').forEach(btn => {
			btn.addEventListener('click', () => {
				idField.value = btn.dataset.id || '';
				document.getElementById('editItem').value = btn.dataset.itemId || '';
				document.getElementById('editRevision').value = btn.dataset.revision || '';
				document.getElementById('editEci').value = btn.dataset.eci || '';
				document.getElementById('editScrap').value = btn.dataset.scrap || '';
				editLabel.textContent = btn.dataset.label || '';
				openModal(editModal);
			});
		});
		document.getElementById('editSubmit').addEventListener('click', () => {
			actionField.value = 'update';
			itemIdField.value = (document.getElementById('editItem').value || '').trim();
			revisionField.value = (document.getElementById('editRevision').value || '').trim();
			eciField.value = (document.getElementById('editEci').value || '').trim();
			scrapField.value = (document.getElementById('editScrap').value || '').trim();
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

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
		const bomIdField = document.getElementById('bomIdField');
		const componentIdField = document.getElementById('componentIdField');
		const quantityField = document.getElementById('quantityField');
		const unitField = document.getElementById('unitField');
		const sequenceField = document.getElementById('sequenceField');

		const addModal = document.getElementById('addModal');
		const editModal = document.getElementById('editModal');
		const deleteModal = document.getElementById('deleteModal');

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

		// Add
		document.getElementById('openAddModal').addEventListener('click', () => {
			tsSet('addBom', '');
			tsSet('addComponent', '');
			document.getElementById('addQuantity').value = '';
			document.getElementById('addUnit').value = '';
			document.getElementById('addSequence').value = '1';
			openModal(addModal);
		});
		document.getElementById('addSubmit').addEventListener('click', () => {
			actionField.value = 'create';
			idField.value = '';
			bomIdField.value = (document.getElementById('addBom').value || '').trim();
			componentIdField.value = (document.getElementById('addComponent').value || '').trim();
			quantityField.value = (document.getElementById('addQuantity').value || '').trim();
			unitField.value = (document.getElementById('addUnit').value || '').trim();
			sequenceField.value = (document.getElementById('addSequence').value || '1').trim();
			actionForm.submit();
		});

		// Edit
		const editLabel = document.getElementById('editLabel');
		document.querySelectorAll('[data-open-edit]').forEach(btn => {
			btn.addEventListener('click', () => {
				idField.value = btn.dataset.id || '';
				tsSet('editBom', btn.dataset.bomId);
				tsSet('editComponent', btn.dataset.componentId);
				document.getElementById('editQuantity').value = btn.dataset.quantity || '';
				document.getElementById('editUnit').value = btn.dataset.unit || '';
				document.getElementById('editSequence').value = btn.dataset.sequence || '1';
				editLabel.textContent = btn.dataset.label || '';
				openModal(editModal);
			});
		});
		document.getElementById('editSubmit').addEventListener('click', () => {
			actionField.value = 'update';
			bomIdField.value = (document.getElementById('editBom').value || '').trim();
			componentIdField.value = (document.getElementById('editComponent').value || '').trim();
			quantityField.value = (document.getElementById('editQuantity').value || '').trim();
			unitField.value = (document.getElementById('editUnit').value || '').trim();
			sequenceField.value = (document.getElementById('editSequence').value || '1').trim();
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

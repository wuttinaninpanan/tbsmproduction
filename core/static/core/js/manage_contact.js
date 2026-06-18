(() => {
	const init = () => {
		const actionForm = document.getElementById('actionForm');
		const actionField = document.getElementById('actionField');
		const idField = document.getElementById('idField');
		const partnerIdField = document.getElementById('partnerIdField');
		const firstNameField = document.getElementById('firstNameField');
		const lastNameField = document.getElementById('lastNameField');
		const telephoneNumberField = document.getElementById('telephoneNumberField');
		const emailField = document.getElementById('emailField');

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
		document.getElementById('openAddModal').addEventListener('click', () => openModal(addModal));
		document.getElementById('addSubmit').addEventListener('click', () => {
			actionField.value = 'create';
			idField.value = '';
			partnerIdField.value = (document.getElementById('addPartnerId').value || '').trim();
			firstNameField.value = (document.getElementById('addFirstName').value || '').trim();
			lastNameField.value = (document.getElementById('addLastName').value || '').trim();
			telephoneNumberField.value = (document.getElementById('addTelephoneNumber').value || '').trim();
			emailField.value = (document.getElementById('addEmail').value || '').trim();
			actionForm.submit();
		});

		// Edit
		const editLabel = document.getElementById('editLabel');
		document.querySelectorAll('[data-open-edit]').forEach(btn => {
			btn.addEventListener('click', () => {
				idField.value = btn.dataset.id || '';
				document.getElementById('editPartnerId').value = btn.dataset.partnerId || '';
				document.getElementById('editFirstName').value = btn.dataset.firstName || '';
				document.getElementById('editLastName').value = btn.dataset.lastName || '';
				document.getElementById('editTelephoneNumber').value = btn.dataset.telephoneNumber || '';
				document.getElementById('editEmail').value = btn.dataset.email || '';
				editLabel.textContent = `${btn.dataset.firstName || ''} ${btn.dataset.lastName || ''}`.trim();
				openModal(editModal);
			});
		});
		document.getElementById('editSubmit').addEventListener('click', () => {
			actionField.value = 'update';
			partnerIdField.value = (document.getElementById('editPartnerId').value || '').trim();
			firstNameField.value = (document.getElementById('editFirstName').value || '').trim();
			lastNameField.value = (document.getElementById('editLastName').value || '').trim();
			telephoneNumberField.value = (document.getElementById('editTelephoneNumber').value || '').trim();
			emailField.value = (document.getElementById('editEmail').value || '').trim();
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

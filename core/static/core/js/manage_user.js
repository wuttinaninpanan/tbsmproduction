(() => {
	function openAddModal() {
		const modal = document.getElementById('addUserModal');
		if (!modal) return;
		modal.classList.remove('hidden');
		modal.classList.add('flex');
		document.body.classList.add('overflow-hidden');
	}

	function closeAddModal() {
		const modal = document.getElementById('addUserModal');
		if (!modal) return;
		modal.classList.add('hidden');
		modal.classList.remove('flex');
		document.body.classList.remove('overflow-hidden');
	}

	function openEditModal(data) {
		const modal = document.getElementById('editUserModal');
		if (!modal) return;
		document.getElementById('edit_id').value = data.id || '';
		document.getElementById('edit_username').value = data.username || '';
		const fullName = ((data.firstName || '').trim() + ' ' + (data.lastName || '').trim()).trim();
		document.getElementById('edit_full_name').value = fullName;
		document.getElementById('edit_email').value = data.email || '';
		document.getElementById('edit_role').value = (data.role || 'user');
		document.getElementById('edit_shift').value = (data.shift || 'shift_day');
		const groupSelect = document.getElementById('edit_group');
		if (groupSelect) groupSelect.value = (data.group || '');
		document.getElementById('edit_is_active').checked = (data.active === '1');
		document.getElementById('edit_password').value = '';

		modal.classList.remove('hidden');
		modal.classList.add('flex');
		document.body.classList.add('overflow-hidden');
	}

	function closeEditModal() {
		const modal = document.getElementById('editUserModal');
		if (!modal) return;
		modal.classList.add('hidden');
		modal.classList.remove('flex');
		document.body.classList.remove('overflow-hidden');
	}

	const init = () => {
		// Bind edit buttons
		document.querySelectorAll('[data-edit-user]').forEach(btn => {
			btn.addEventListener('click', () => {
				openEditModal({
					id: btn.dataset.id,
					username: btn.dataset.username,
					firstName: btn.dataset.firstName,
					lastName: btn.dataset.lastName,
					email: btn.dataset.email,
					role: btn.dataset.role,
					shift: btn.dataset.shift,
					group: btn.dataset.group,
					active: btn.dataset.active,
				});
			});
		});

		// Close modal handlers
		document.querySelectorAll('[data-modal-close]').forEach(el => {
			el.addEventListener('click', closeEditModal);
		});
		document.querySelectorAll('[data-add-modal-close]').forEach(el => {
			el.addEventListener('click', closeAddModal);
		});
		const backdrop = document.querySelector('#editUserModal [data-modal-backdrop]');
		if (backdrop) backdrop.addEventListener('click', closeEditModal);
		const addBackdrop = document.querySelector('#addUserModal [data-add-modal-backdrop]');
		if (addBackdrop) addBackdrop.addEventListener('click', closeAddModal);
		window.addEventListener('keydown', (e) => {
			if (e.key === 'Escape') {
				closeEditModal();
				closeAddModal();
			}
		});

		// Open add modal
		document.querySelectorAll('[data-open-add-user]').forEach(btn => {
			btn.addEventListener('click', openAddModal);
		});
		try {
			const params = new URLSearchParams(window.location.search);
			if (params.get('open_add') === '1') openAddModal();
		} catch (e) {}

		// Import button
		const importBtn = document.getElementById('importBtn');
		const importFile = document.getElementById('importFile');
		const importForm = document.getElementById('importForm');
		if (importBtn && importFile && importForm) {
			importBtn.addEventListener('click', () => importFile.click());
			importFile.addEventListener('change', () => {
				if (importFile.files && importFile.files.length > 0) importForm.submit();
			});
		}

		// Bulk select/delete
		const selectAll = document.getElementById('selectAllRows');
		const bulkBtn = document.getElementById('bulkDeleteBtn');
		const bulkForm = document.getElementById('bulkDeleteForm');
		const rowCheckboxes = Array.from(document.querySelectorAll('.rowCheckbox'));

		function selectedIds() {
			return rowCheckboxes
				.filter(cb => cb.checked)
				.map(cb => cb.dataset.id)
				.filter(Boolean);
		}
		function syncBulkState() {
			const ids = selectedIds();
			if (bulkBtn) bulkBtn.disabled = ids.length === 0;
			if (selectAll) {
				const allChecked = rowCheckboxes.length > 0 && rowCheckboxes.every(cb => cb.checked);
				selectAll.checked = allChecked;
				selectAll.indeterminate = ids.length > 0 && !allChecked;
			}
		}
		if (selectAll) {
			selectAll.addEventListener('change', () => {
				rowCheckboxes.forEach(cb => { cb.checked = selectAll.checked; });
				syncBulkState();
			});
		}
		rowCheckboxes.forEach(cb => cb.addEventListener('change', syncBulkState));
		if (bulkBtn && bulkForm) {
			bulkBtn.addEventListener('click', () => {
				const ids = selectedIds();
				if (ids.length === 0) return;
				if (!confirm(`ยืนยันการลบผู้ใช้งานที่เลือก ${ids.length} รายการ?`)) return;
				bulkForm.querySelectorAll('input[name="bulk_id"]').forEach(n => n.remove());
				ids.forEach(id => {
					const input = document.createElement('input');
					input.type = 'hidden';
					input.name = 'bulk_id';
					input.value = id;
					bulkForm.appendChild(input);
				});
				bulkForm.submit();
			});
		}
		syncBulkState();

		// Confirm before deleting (client-only; backend can ignore)
		document.querySelectorAll('[data-confirm-delete]').forEach(form => {
			form.addEventListener('submit', (e) => {
				const username = form.dataset.username || '';
				const msg = username ? `ยืนยันการลบผู้ใช้งาน ${username} ?` : 'ยืนยันการลบผู้ใช้งานรายนี้?';
				if (!confirm(msg)) e.preventDefault();
			});
		});
	};

	if (document.readyState === 'loading') {
		document.addEventListener('DOMContentLoaded', init);
	} else {
		init();
	}
})();

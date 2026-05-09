(() => {
	const init = () => {
		const actionForm = document.getElementById('actionForm');
		const actionField = document.getElementById('actionField');
		const idField = document.getElementById('idField');
		const partnerIdField = document.getElementById('partnerIdField');
		const addressTypeField = document.getElementById('addressTypeField');
		const addressLine1Field = document.getElementById('addressLine1Field');
		const addressLine2Field = document.getElementById('addressLine2Field');
		const subdistrictField = document.getElementById('subdistrictField');
		const districtField = document.getElementById('districtField');
		const provinceField = document.getElementById('provinceField');
		const postalCodeField = document.getElementById('postalCodeField');
		const countryField = document.getElementById('countryField');

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
			addressTypeField.value = (document.getElementById('addAddressType').value || '').trim();
			addressLine1Field.value = (document.getElementById('addAddressLine1').value || '').trim();
			addressLine2Field.value = (document.getElementById('addAddressLine2').value || '').trim();
			subdistrictField.value = (document.getElementById('addSubdistrict').value || '').trim();
			districtField.value = (document.getElementById('addDistrict').value || '').trim();
			provinceField.value = (document.getElementById('addProvince').value || '').trim();
			postalCodeField.value = (document.getElementById('addPostalCode').value || '').trim();
			countryField.value = (document.getElementById('addCountry').value || 'Thailand').trim();
			actionForm.submit();
		});

		// Edit
		const editLabel = document.getElementById('editLabel');
		document.querySelectorAll('[data-open-edit]').forEach(btn => {
			btn.addEventListener('click', () => {
				idField.value = btn.dataset.id || '';
				const editPartnerEl = document.getElementById('editPartnerId');
				const editTypeEl = document.getElementById('editAddressType');
				editPartnerEl.value = btn.dataset.partnerId || '';
				editTypeEl.value = btn.dataset.addressType || '';
				document.getElementById('editAddressLine1').value = btn.dataset.addressLine1 || '';
				document.getElementById('editAddressLine2').value = btn.dataset.addressLine2 || '';
				document.getElementById('editSubdistrict').value = btn.dataset.subdistrict || '';
				document.getElementById('editDistrict').value = btn.dataset.district || '';
				document.getElementById('editProvince').value = btn.dataset.province || '';
				document.getElementById('editPostalCode').value = btn.dataset.postalCode || '';
				document.getElementById('editCountry').value = btn.dataset.country || '';
				editLabel.textContent = btn.dataset.addressLine1 || '';
				openModal(editModal);
			});
		});
		document.getElementById('editSubmit').addEventListener('click', () => {
			actionField.value = 'update';
			partnerIdField.value = (document.getElementById('editPartnerId').value || '').trim();
			addressTypeField.value = (document.getElementById('editAddressType').value || '').trim();
			addressLine1Field.value = (document.getElementById('editAddressLine1').value || '').trim();
			addressLine2Field.value = (document.getElementById('editAddressLine2').value || '').trim();
			subdistrictField.value = (document.getElementById('editSubdistrict').value || '').trim();
			districtField.value = (document.getElementById('editDistrict').value || '').trim();
			provinceField.value = (document.getElementById('editProvince').value || '').trim();
			postalCodeField.value = (document.getElementById('editPostalCode').value || '').trim();
			countryField.value = (document.getElementById('editCountry').value || '').trim();
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

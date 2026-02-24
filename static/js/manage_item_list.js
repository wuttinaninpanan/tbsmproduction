(() => {
	const init = () => {
		// Sorting by clicking column headers
		(function(){
			const url0 = new URL(window.location.href);
			const currentSort = url0.searchParams.get('sort') || 'sku';
			const currentDir = (url0.searchParams.get('dir') || 'asc').toLowerCase() === 'desc' ? 'desc' : 'asc';
			function setIndicators(){
				document.querySelectorAll('[data-sort-ind]').forEach(el => {
					const k = el.getAttribute('data-sort-ind');
					if (!k) return;
					if (k === currentSort) el.textContent = currentDir === 'desc' ? '▼' : '▲';
					else el.textContent = '';
				});
			}
			setIndicators();
			document.querySelectorAll('[data-sort]').forEach(btn => {
				btn.addEventListener('click', () => {
					const key = btn.getAttribute('data-sort');
					if (!key) return;
					const url = new URL(window.location.href);
					const params = url.searchParams;
					const prevSort = params.get('sort') || currentSort;
					const prevDir = (params.get('dir') || currentDir).toLowerCase() === 'desc' ? 'desc' : 'asc';
					const nextDir = (prevSort === key) ? (prevDir === 'desc' ? 'asc' : 'desc') : 'asc';
					params.set('sort', key);
					params.set('dir', nextDir);
					params.delete('page');
					window.location.href = url.toString();
				});
			});
		})();

		const actionForm = document.getElementById('actionForm');
		const actionField = document.getElementById('actionField');
		const idField = document.getElementById('idField');
		const sdCodeField = document.getElementById('sdCodeField');
		const partNumberField = document.getElementById('partNumberField');
		const partNameField = document.getElementById('partNameField');
		const skuField = document.getElementById('skuField');
		const weightField = document.getElementById('weightField');
		const categoryIdField = document.getElementById('categoryIdField');
		const purchasedPriceField = document.getElementById('purchasedPriceField');
		const costField = document.getElementById('costField');
		const levelField = document.getElementById('levelField');
		const commentField = document.getElementById('commentField');

		const addModal = document.getElementById('addModal');
		const editModal = document.getElementById('editModal');
		const deleteModal = document.getElementById('deleteModal');
		const deleteLabel = document.getElementById('deleteLabel');

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

		function openModal(el){ el.classList.remove('hidden'); el.classList.add('flex'); }
		function closeModal(el){ el.classList.add('hidden'); el.classList.remove('flex'); }

		// Bulk delete
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
				Array.from(actionForm.querySelectorAll('input[name="bulk_id"]')).forEach(n => n.remove());
				actionField.value = 'bulk_delete_items';
				idField.value = '';
				sdCodeField.value = '';
				partNumberField.value = '';
				partNameField.value = '';
				skuField.value = '';
				weightField.value = '';
				categoryIdField.value = '';
				purchasedPriceField.value = '';
				costField.value = '';
				levelField.value = '';
				commentField.value = '';
				ids.forEach(id => {
					const input = document.createElement('input');
					input.type = 'hidden';
					input.name = 'bulk_id';
					input.value = String(id);
					actionForm.appendChild(input);
				});
				actionForm.submit();
			});
		}

		// Modal close
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

		// Add
		const addSku = document.getElementById('addSku');
		const addSdCode = document.getElementById('addSdCode');
		const addPartNumber = document.getElementById('addPartNumber');
		const addPartName = document.getElementById('addPartName');
		const addWeight = document.getElementById('addWeight');
		const addCategoryId = document.getElementById('addCategoryId');
		const addPurchasedPrice = document.getElementById('addPurchasedPrice');
		const addCost = document.getElementById('addCost');
		const addLevel = document.getElementById('addLevel');
		const addComment = document.getElementById('addComment');
		const addReferenceImage = document.getElementById('addReferenceImage');

		const openAddModalBtn = document.getElementById('openAddModal');
		if (openAddModalBtn) {
			openAddModalBtn.addEventListener('click', () => {
				addSku.value = '';
				addSdCode.value = '';
				addPartNumber.value = '';
				addPartName.value = '';
				addWeight.value = '0';
				addCategoryId.value = '';
				addPurchasedPrice.value = '0';
				if (addCost) addCost.value = '0';
				addLevel.value = '';
				addComment.value = '';
				if (addReferenceImage) addReferenceImage.value = '';
				openModal(addModal);
				setTimeout(() => addSku.focus(), 0);
			});
		}

		// Edit
		const editSku = document.getElementById('editSku');
		const editSdCode = document.getElementById('editSdCode');
		const editPartNumber = document.getElementById('editPartNumber');
		const editPartName = document.getElementById('editPartName');
		const editWeight = document.getElementById('editWeight');
		const editCategoryId = document.getElementById('editCategoryId');
		const editPurchasedPrice = document.getElementById('editPurchasedPrice');
		const editCost = document.getElementById('editCost');
		const editLevel = document.getElementById('editLevel');
		const editComment = document.getElementById('editComment');
		const editId = document.getElementById('editId');
		const editReferenceImage = document.getElementById('editReferenceImage');
		const editImagePreviewWrap = document.getElementById('editImagePreviewWrap');
		const editImageLink = document.getElementById('editImageLink');
		const editImagePreview = document.getElementById('editImagePreview');

		document.querySelectorAll('[data-open-edit]').forEach(btn => {
			btn.addEventListener('click', () => {
				if (editId) editId.value = btn.dataset.id || '';
				idField.value = btn.dataset.id || '';
				editSdCode.value = btn.dataset.sdCode || '';
				editPartNumber.value = btn.dataset.partNumber || '';
				editPartName.value = btn.dataset.partName || '';
				editSku.value = btn.dataset.sku || '';
				editWeight.value = btn.dataset.weight || '0';
				editCategoryId.value = btn.dataset.categoryId || '';
				editPurchasedPrice.value = btn.dataset.purchasedPrice || '0';
				editCost.value = btn.dataset.cost || '0';
				editLevel.value = btn.dataset.level || '';
				editComment.value = btn.dataset.comment || '';
				if (editReferenceImage) editReferenceImage.value = '';
				const imgUrl = (btn.dataset.imageUrl || '').trim();
				if (editImagePreviewWrap && editImageLink && editImagePreview) {
					if (imgUrl) {
						editImagePreviewWrap.classList.remove('hidden');
						editImageLink.href = imgUrl;
						editImagePreview.src = imgUrl;
					} else {
						editImagePreviewWrap.classList.add('hidden');
						editImageLink.href = '#';
						editImagePreview.src = '';
					}
				}
				openModal(editModal);
				setTimeout(() => editSku.focus(), 0);
			});
		});

		// Delete
		document.querySelectorAll('[data-open-delete]').forEach(btn => {
			btn.addEventListener('click', () => {
				idField.value = btn.dataset.id || '';
				deleteLabel.textContent = btn.dataset.label || '';
				openModal(deleteModal);
			});
		});

		const deleteSubmit = document.getElementById('deleteSubmit');
		if (deleteSubmit) {
			deleteSubmit.addEventListener('click', () => {
				actionField.value = 'delete_item';
				actionForm.submit();
			});
		}
	};

	if (document.readyState === 'loading') {
		document.addEventListener('DOMContentLoaded', init);
	} else {
		init();
	}
})();

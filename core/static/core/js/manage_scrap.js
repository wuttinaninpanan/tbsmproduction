(() => {
	const init = () => {
		const actionForm = document.getElementById('actionForm');
		const actionField = document.getElementById('actionField');
		const idField = document.getElementById('idField');
		const lineField = document.getElementById('lineField');
		const partField = document.getElementById('partField');
		const defectField = document.getElementById('defectField');
		const componentPartField = document.getElementById('componentPartField');
		const qtyField = document.getElementById('qtyField');
		const commentField = document.getElementById('commentField');
		const clearPhotoField = document.getElementById('clearPhotoField');

		const recordDataEl = document.getElementById('recordData');
		const recordData = recordDataEl ? JSON.parse(recordDataEl.textContent) : { productionLines: [] };

		const editModal = document.getElementById('editModal');
		const editLabel = document.getElementById('editLabel');
		const editLine = document.getElementById('editLine');
		const editPart = document.getElementById('editPart');
		const editDefect = document.getElementById('editDefect');
		const editComponentPart = document.getElementById('editComponentPart');
		const editQty = document.getElementById('editQty');
		const editComment = document.getElementById('editComment');
		const editPhoto = document.getElementById('editPhoto');
		const editPhotoPreview = document.getElementById('editPhotoPreview');
		const editClearPhoto = document.getElementById('editClearPhoto');

		function setOptions(selectEl, options, placeholder) {
			selectEl.innerHTML = '';
			const opt0 = document.createElement('option');
			opt0.value = '';
			opt0.textContent = placeholder || 'เลือก';
			selectEl.appendChild(opt0);
			options.forEach(o => {
				const opt = document.createElement('option');
				opt.value = o.value;
				opt.textContent = o.label;
				selectEl.appendChild(opt);
			});
		}

		function findLine(code) {
			return (recordData.productionLines || []).find(l => (l.code || '') === (code || '')) || null;
		}
		function findPart(lineObj, partId) {
			if (!lineObj) return null;
			return (lineObj.parts || []).find(p => String(p.id || '') === String(partId || '')) || null;
		}
		function findDefect(partObj, defectId) {
			if (!partObj) return null;
			return (partObj.defects || []).find(d => String(d.id || '') === String(defectId || '')) || null;
		}

		function refreshParts() {
			const lineObj = findLine(editLine.value);
			const parts = (lineObj?.parts || []).map(p => ({ value: String(p.id), label: (p.sd_number || p.part_number || p.id) }));
			setOptions(editPart, parts, 'เลือก SD number');
			editPart.value = '';
			refreshDefects();
		}
		function refreshDefects() {
			const lineObj = findLine(editLine.value);
			const partObj = findPart(lineObj, editPart.value);
			const defects = (partObj?.defects || []).map(d => ({ value: String(d.id), label: d.name }));
			setOptions(editDefect, defects, 'เลือก Defect');
			editDefect.value = '';
			refreshComponentParts();
		}
		function refreshComponentParts() {
			const lineObj = findLine(editLine.value);
			const partObj = findPart(lineObj, editPart.value);
			const defectObj = findDefect(partObj, editDefect.value);
			const componentParts = (defectObj?.component_parts || []).map(s => ({ value: String(s.id || ''), label: s.name }));
			setOptions(editComponentPart, componentParts, 'เลือก Part name');
			editComponentPart.value = '';
		}

		// Initial line options
		setOptions(editLine, (recordData.productionLines || []).map(l => ({ value: l.code, label: l.code })), 'เลือก Line');
		setOptions(editPart, [], 'เลือก SD number');
		setOptions(editDefect, [], 'เลือก Defect');
		setOptions(editComponentPart, [], 'เลือก Part name');

		editLine.addEventListener('change', refreshParts);
		editPart.addEventListener('change', refreshDefects);
		editDefect.addEventListener('change', refreshComponentParts);

		const deleteModal = document.getElementById('deleteModal');
		const deleteLabel = document.getElementById('deleteLabel');

		// Toolbar: bulk delete
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
				actionField.value = 'bulk_delete';
				idField.value = '';
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

		function openModal(el){ el.classList.remove('hidden'); el.classList.add('flex'); }
		function closeModal(el){ el.classList.add('hidden'); el.classList.remove('flex'); }

		// Image modal
		const imageModal = document.getElementById('imageModal');
		const imageModalImg = document.getElementById('imageModalImg');
		function openImageModal(url) {
			if (!url) return;
			if (!imageModal || !imageModalImg) {
				window.open(url, '_blank', 'noreferrer');
				return;
			}
			imageModalImg.src = url;
			imageModalImg.alt = 'Photo';
			openModal(imageModal);
			imageModal.setAttribute('aria-hidden', 'false');
		}
		function closeImageModal() {
			if (!imageModal) return;
			closeModal(imageModal);
			imageModal.setAttribute('aria-hidden', 'true');
			if (imageModalImg) imageModalImg.src = '';
		}
		if (imageModal) {
			imageModal.querySelectorAll('[data-image-modal-close]').forEach(btn => btn.addEventListener('click', closeImageModal));
			imageModal.querySelectorAll('[data-image-modal-backdrop]').forEach(bg => bg.addEventListener('click', closeImageModal));
		}
		const closeFromEvent = (e) => {
			if (!imageModal || imageModal.classList.contains('hidden')) return;
			const target = e.target;
			if (!target || !target.closest) return;
			const hit = target.closest('[data-image-modal-close], [data-image-modal-backdrop], [data-image-modal-img]');
			if (!hit) return;
			e.preventDefault();
			closeImageModal();
		};
		document.addEventListener('pointerdown', closeFromEvent);
		document.addEventListener('click', closeFromEvent);
		// Delegate clicks for dynamically rendered rows too
		document.addEventListener('click', (e) => {
			const link = e.target && e.target.closest ? e.target.closest('a[data-image-popup]') : null;
			if (!link) return;
			e.preventDefault();
			openImageModal(link.getAttribute('href'));
		});

		document.querySelectorAll('[data-open-edit-row]').forEach(btn => {
			btn.addEventListener('click', () => {
				actionField.value = 'update';
				idField.value = btn.dataset.id || '';
				lineField.value = '';
				partField.value = '';
				defectField.value = '';
				componentPartField.value = '';
				qtyField.value = '';
				clearPhotoField.value = '0';

				editLabel.textContent = btn.dataset.label || '';

				// Set datetime, user, and shift (read-only)
				document.getElementById('editDateTime').textContent = btn.dataset.createdAt || '-';
				document.getElementById('editUser').textContent = btn.dataset.username || '-';

				// Format shift display
				const shiftValue = btn.dataset.shift || '-';
				let shiftDisplay = '-';
				if (shiftValue === 'shift_a') {
					shiftDisplay = 'กะ A';
				} else if (shiftValue === 'shift_b') {
					shiftDisplay = 'กะ B';
				} else if (shiftValue === 'shift_day') {
					shiftDisplay = 'กะ Day';
				}
				document.getElementById('editShift').textContent = shiftDisplay;

				// Preselect hierarchy
				const lineCode = btn.dataset.lineCode || '';
				const partId = btn.dataset.partId || '';
				const defectId = btn.dataset.defectId || '';
				const componentPartId = btn.dataset.componentPartId || '';
				editLine.value = lineCode;
				refreshParts();
				editPart.value = partId;
				refreshDefects();
				editDefect.value = String(defectId);
				refreshComponentParts();
				editComponentPart.value = String(componentPartId);

				editQty.value = btn.dataset.quantity || '1';
				if (editComment) editComment.value = btn.dataset.comment || '';
				editClearPhoto.checked = false;
				editPhoto.value = '';
				const photoUrl = btn.dataset.photoUrl || '';
				if (photoUrl) {
					editPhotoPreview.src = photoUrl;
					editPhotoPreview.classList.remove('opacity-40');
				} else {
					editPhotoPreview.src = '';
					editPhotoPreview.classList.add('opacity-40');
				}

				openModal(editModal);
				setTimeout(() => editQty.focus(), 0);
			});
		});

		editPhoto.addEventListener('change', () => {
			const file = editPhoto.files && editPhoto.files[0];
			if (!file) return;
			const url = URL.createObjectURL(file);
			editPhotoPreview.src = url;
			editPhotoPreview.classList.remove('opacity-40');
		});

		document.querySelectorAll('[data-open-delete-row]').forEach(btn => {
			btn.addEventListener('click', () => {
				actionField.value = 'delete';
				idField.value = btn.dataset.id || '';
				deleteLabel.textContent = btn.dataset.label || '';
				openModal(deleteModal);
			});
		});

		document.querySelectorAll('[data-modal-close]').forEach(btn => {
			btn.addEventListener('click', () => {
				closeModal(editModal);
				closeModal(deleteModal);
			});
		});

		document.querySelectorAll('[data-modal-backdrop]').forEach(bg => {
			bg.addEventListener('click', () => {
				closeModal(editModal);
				closeModal(deleteModal);
			});
		});

		document.getElementById('editSubmit').addEventListener('click', () => {
			lineField.value = (editLine.value || '').trim();
			partField.value = (editPart.value || '').trim();
			defectField.value = (editDefect.value || '').trim();
			componentPartField.value = (editComponentPart.value || '').trim();
			qtyField.value = (editQty.value || '1').trim();
			if (editComment && commentField) commentField.value = (editComment.value || '').trim();
			clearPhotoField.value = editClearPhoto.checked ? '1' : '0';
			actionForm.submit();
		});

		document.getElementById('deleteSubmit').addEventListener('click', () => {
			actionForm.submit();
		});

		document.addEventListener('keydown', (e) => {
			if (e.key === 'Escape') {
				closeModal(editModal);
				closeModal(deleteModal);
				closeImageModal();
			}
		});

		// Initialize Flatpickr datepickers
		if (typeof flatpickr !== 'undefined') {
			flatpickr('#date_from_picker', {
				locale: 'th',
				dateFormat: 'Y-m-d',
				allowInput: true,
				wrap: false,
			});
			flatpickr('#date_to_picker', {
				locale: 'th',
				dateFormat: 'Y-m-d',
				allowInput: true,
				wrap: false,
			});
		}

		syncBulkState();
	};

	if (document.readyState === 'loading') {
		document.addEventListener('DOMContentLoaded', init);
	} else {
		init();
	}
})();

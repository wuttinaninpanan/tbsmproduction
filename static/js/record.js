(() => {
	const init = () => {
		const dataEl = document.getElementById('record-data');
		const recordData = dataEl ? JSON.parse(dataEl.textContent) : { productionLines: [] };

		const groupsWrap = document.getElementById('scrap-groups');
		const clearBtn = document.getElementById('clear');
		const addGroupBtn = document.getElementById('add-group');
		const removeGroupBtn = document.getElementById('remove-group');

		const groupTpl = document.getElementById('group-template');
		const rowTpl = document.getElementById('row-template');
		const selectAll0 = document.getElementById('select-all-0');

		// Image modal
		const imageModal = document.getElementById('imageModal');
		const imageModalImg = document.getElementById('imageModalImg');
		const openImageModal = (url) => {
			if (!url) return;
			if (!imageModal || !imageModalImg) {
				window.open(url, '_blank', 'noreferrer');
				return;
			}
			imageModalImg.src = url;
			imageModalImg.alt = 'Photo';
			imageModal.classList.remove('hidden');
			imageModal.classList.add('flex');
			imageModal.setAttribute('aria-hidden', 'false');
		};
		const closeImageModal = () => {
			if (!imageModal) return;
			imageModal.classList.add('hidden');
			imageModal.classList.remove('flex');
			imageModal.setAttribute('aria-hidden', 'true');
			if (imageModalImg) imageModalImg.src = '';
		};
		if (imageModal) {
			imageModal.querySelectorAll('[data-image-modal-close]').forEach(btn => btn.addEventListener('click', closeImageModal));
			imageModal.querySelectorAll('[data-image-modal-backdrop]').forEach(bg => bg.addEventListener('click', closeImageModal));

			const closeFromEvent = (e) => {
				if (!imageModal || imageModal.classList.contains('hidden')) return;
				const target = e.target;
				if (!target || !target.closest) return;
				const hit = target.closest('[data-image-modal-close], [data-image-modal-backdrop], [data-image-modal-img]');
				if (!hit) return;
				e.preventDefault();
				closeImageModal();
			};
			// iOS Safari: pointer events are more reliable than click in some cases
			document.addEventListener('pointerdown', closeFromEvent);
			document.addEventListener('click', closeFromEvent);

			document.addEventListener('keydown', (e) => {
				if (e.key === 'Escape') closeImageModal();
			});
		}

		let productionLineInput = null;
		let productionLineList = null;
		let partSelect = null;
		let topDefectSelect = null;
		let headerHints = null;
		let topHeaderRowEl = null;
		let nextGroupIndex = 1;

		/** dynamic groups (gi >= 1) */
		const extraGroups = [];

		function getLine(lineId) {
			return (recordData.productionLines || []).find(l => l.id === lineId) || null;
		}

		function getPart(lineId, partId) {
			const line = getLine(lineId);
			if (!line) return null;
			return (line.parts || []).find(p => p.id === partId) || null;
		}

		function setOptions(select, options, placeholder = '— Select —') {
			select.innerHTML = '';
			const ph = document.createElement('option');
			ph.value = '';
			ph.textContent = placeholder;
			select.appendChild(ph);
			options.forEach(opt => {
				const o = document.createElement('option');
				o.value = opt.value;
				o.textContent = opt.label;
				select.appendChild(o);
			});
		}

		function setDefectOptions(select, options, placeholder = '— Select defect —') {
			setOptions(select, options, placeholder);
			const hasOther = options.some(o => (o.label || '').trim() === 'อื่นๆ');
			if (!hasOther) {
				const other = document.createElement('option');
				other.value = '__other__';
				other.textContent = 'อื่นๆ';
				select.appendChild(other);
			}
		}

		function isOtherDefectSelected(selectEl) {
			if (!selectEl) return false;
			if (selectEl.value === '__other__') return true;
			const txt = (selectEl.options?.[selectEl.selectedIndex]?.textContent || '').trim();
			return txt === 'อื่นๆ';
		}

		function ensureRowCommentInput({ gi, ri, defectCell }) {
			if (!defectCell) return null;
			let input = defectCell.querySelector(`input[type="text"][data-row-comment="${gi}-${ri}"]`);
			if (!input) {
				input = document.createElement('input');
				input.type = 'text';
				input.className = 'mt-2 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-red-500';
				input.placeholder = 'ระบุ defect อื่นๆ';
				input.name = `blocks[${gi}][rows][${ri}][comment]`;
				input.setAttribute('data-row-comment', `${gi}-${ri}`);
				defectCell.appendChild(input);
			}
			return input;
		}

		function getCurrentLineId() {
			return (productionLineInput?.value || '').trim().toUpperCase();
		}

		function currentParts() {
			const lineId = getCurrentLineId();
			const line = getLine(lineId);
			return line ? (line.parts || []) : [];
		}

		function currentDefects() {
			const lineId = getCurrentLineId();
			const partId = partSelect?.value || '';
			const part = getPart(lineId, partId);
			return part ? (part.defects || []) : [];
		}

		function defectsFor(lineId, partId) {
			const part = getPart(lineId, partId);
			return part ? (part.defects || []) : [];
		}

		function defectByIdFor(lineId, partId, defectId) {
			return defectsFor(lineId, partId).find(d => d.id === defectId) || null;
		}

		function populateLineDatalist(datalistEl) {
			if (!datalistEl) return;
			datalistEl.innerHTML = '';
			(recordData.productionLines || []).forEach(l => {
				const opt = document.createElement('option');
				opt.value = l.id;
				datalistEl.appendChild(opt);
			});
		}

		function openDatalistForInput(inputEl) {
			if (!inputEl) return;
			if (inputEl.disabled || inputEl.readOnly) return;
			try {
				inputEl.focus({ preventScroll: true });
			} catch {
				inputEl.focus();
			}

			// Some browsers may support this; safe to try.
			if (typeof inputEl.showPicker === 'function') {
				try {
					inputEl.showPicker();
					return;
				} catch {
					// fall through
				}
			}

			try { inputEl.click(); } catch {}
			try {
				inputEl.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowDown', code: 'ArrowDown', bubbles: true }));
			} catch {}
		}

		function ensureHiddenField(containerEl, name, value) {
			if (!containerEl || !name) return null;
			let hidden = null;
			containerEl.querySelectorAll('input[type="hidden"]').forEach(el => {
				if (hidden) return;
				if (el && el.name === name) hidden = el;
			});
			if (!hidden) {
				hidden = document.createElement('input');
				hidden.type = 'hidden';
				hidden.name = name;
				containerEl.appendChild(hidden);
			}
			hidden.value = value ?? '';
			return hidden;
		}

		function lockFieldWithHidden({ fieldEl, containerEl, hiddenName, value }) {
			if (!fieldEl) return;
			fieldEl.classList.add('locked-field');
			fieldEl.disabled = true;
			if (hiddenName) ensureHiddenField(containerEl || fieldEl.parentElement, hiddenName, value);
		}

		function buildHeaderRow() {
			const row = rowTpl.content.firstElementChild.cloneNode(true);
			const lineCell = row.querySelector('.line-cell');
			const partCell = row.querySelector('.part-cell');
			const defectCell = row.querySelector('.defect-cell');
			const checkCell = row.querySelector('.check-cell');
			const photoCell = row.querySelector('.photo-cell');
			const scrapCell = row.querySelector('.scrap-cell');
			const qtyCell = row.querySelector('.qty-cell');

			checkCell.innerHTML = '';
			photoCell.innerHTML = '';
			scrapCell.innerHTML = '';
			qtyCell.innerHTML = '';

			// Production line
			productionLineInput = document.createElement('input');
			productionLineInput.id = 'production-line';
			productionLineInput.name = 'production_line';
			productionLineInput.placeholder = 'Input or scan';
			productionLineInput.setAttribute('list', 'production-lines');
			productionLineInput.className = 'production-line-input w-full rounded-md border border-slate-300 bg-white pl-3 pr-10 py-2 focus:outline-none focus:ring-2 focus:ring-red-500';
			const lineWrap = document.createElement('div');
			lineWrap.className = 'relative';
			const chevron = document.createElement('div');
			chevron.className = 'datalist-chevron';
			chevron.setAttribute('aria-hidden', 'true');
			chevron.innerHTML = '<svg viewBox="0 0 20 20" fill="currentColor" class="h-5 w-5"><path fill-rule="evenodd" d="M5.23 7.21a.75.75 0 0 1 1.06.02L10 11.17l3.71-3.94a.75.75 0 1 1 1.08 1.04l-4.25 4.5a.75.75 0 0 1-1.08 0l-4.25-4.5a.75.75 0 0 1 .02-1.06Z" clip-rule="evenodd" /></svg>';
			chevron.addEventListener('click', (e) => {
				e.preventDefault();
				e.stopPropagation();
				openDatalistForInput(productionLineInput);
			});
			lineWrap.addEventListener('click', (e) => {
				if (e.target === productionLineInput) return;
				openDatalistForInput(productionLineInput);
			});
			lineWrap.appendChild(productionLineInput);
			lineWrap.appendChild(chevron);
			productionLineList = document.createElement('datalist');
			productionLineList.id = 'production-lines';
			lineCell.appendChild(lineWrap);
			lineCell.appendChild(productionLineList);
			const lineHint = document.createElement('div');
			lineHint.className = 'text-xs text-slate-600 mt-1';
			lineHint.textContent = 'กรุณาใส่หรือสแกน Production line';
			lineCell.appendChild(lineHint);

			// SD number
			partSelect = document.createElement('select');
			partSelect.id = 'part-number';
			partSelect.name = 'part_number';
			partSelect.className = 'w-full rounded-md border border-slate-300 bg-white px-3 py-2 focus:outline-none focus:ring-2 focus:ring-red-500';
			partCell.appendChild(partSelect);
			const partHint = document.createElement('div');
			partHint.className = 'text-xs text-slate-600 mt-1';
			partHint.textContent = 'เลือก SD number';
			partCell.appendChild(partHint);
			setOptions(partSelect, []);

			// Defect mode (for first block)
			topDefectSelect = document.createElement('select');
			topDefectSelect.id = 'defect-mode';
			topDefectSelect.className = 'w-full rounded-md border border-slate-300 bg-white px-3 py-2 focus:outline-none focus:ring-2 focus:ring-red-500';
			defectCell.appendChild(topDefectSelect);
			const defectHint = document.createElement('div');
			defectHint.className = 'text-xs text-slate-600 mt-1';
			defectHint.textContent = 'เลือก Defect mode';
			defectCell.appendChild(defectHint);
			setDefectOptions(topDefectSelect, [], '— Select defect —');

			row.classList.add('header-row');
			headerHints = { lineHint, partHint, defectHint };
			return row;
		}

		function syncSelectAll0State() {
			if (!selectAll0) return;
			const boxes = getGroupRowEnableCheckboxes(0);
			if (!boxes.length) {
				selectAll0.checked = false;
				selectAll0.indeterminate = false;
				return;
			}
			const checkedCount = boxes.filter(b => b.checked).length;
			selectAll0.checked = checkedCount === boxes.length;
			selectAll0.indeterminate = checkedCount > 0 && checkedCount < boxes.length;
		}

		function setAll0RowsEnabled(checked) {
			const boxes = getGroupRowEnableCheckboxes(0);
			boxes.forEach(b => { b.checked = !!checked; });
			syncSelectAll0State();
		}

		function getGroupRowEnableCheckboxes(gi) {
			if (!groupsWrap) return [];
			if (gi === 0) {
				const rows0 = document.getElementById('rows-0');
				const head0 = topHeaderRowEl;
				const boxes = [];
				if (head0) boxes.push(...Array.from(head0.querySelectorAll('input.row-enable[type="checkbox"]')));
				if (rows0) boxes.push(...Array.from(rows0.querySelectorAll('input.row-enable[type="checkbox"]')));
				return boxes;
			}
			const g = extraGroups.find(x => x.gi === gi);
			if (!g) return [];
			const boxes = [];
			if (g.headerRowEl) boxes.push(...Array.from(g.headerRowEl.querySelectorAll('input.row-enable[type="checkbox"]')));
			if (g.rowsWrap) boxes.push(...Array.from(g.rowsWrap.querySelectorAll('input.row-enable[type="checkbox"]')));
			return boxes;
		}

		function syncGroupSelectAllState(gi) {
			const g = extraGroups.find(x => x.gi === gi);
			const select = g?.groupSelectAll;
			if (!select) return;
			const boxes = getGroupRowEnableCheckboxes(gi);
			if (!boxes.length) {
				select.checked = false;
				select.indeterminate = false;
				return;
			}
			const checkedCount = boxes.filter(b => b.checked).length;
			select.checked = checkedCount === boxes.length;
			select.indeterminate = checkedCount > 0 && checkedCount < boxes.length;
		}

		function setGroupRowsEnabled(gi, checked) {
			const boxes = getGroupRowEnableCheckboxes(gi);
			boxes.forEach(b => { b.checked = !!checked; });
			syncGroupSelectAllState(gi);
			syncSelectAll0State();
		}

		function setHintVisible(el, visible) {
			if (!el) return;
			el.style.display = visible ? '' : 'none';
		}

		function buildScrapRow({ gi, ri, scrap, defectCell = null }) {
			const row = rowTpl.content.firstElementChild.cloneNode(true);
			row.querySelector('.line-cell').innerHTML = '';
			row.querySelector('.part-cell').innerHTML = '';
			row.querySelector('.defect-cell').innerHTML = '';
			buildScrapCells({
				gi,
				ri,
				scrap,
				checkCell: row.querySelector('.check-cell'),
				photoCell: row.querySelector('.photo-cell'),
				scrapCell: row.querySelector('.scrap-cell'),
				qtyCell: row.querySelector('.qty-cell'),
				defectCell,
			});
			return row;
		}

		function buildScrapCells({ gi, ri, scrap, checkCell, photoCell, scrapCell, qtyCell, defectCell = null }) {
			checkCell.innerHTML = '';
			photoCell.innerHTML = '';
			scrapCell.innerHTML = '';
			qtyCell.innerHTML = '';

			// Enable
			const enable = document.createElement('input');
			enable.type = 'checkbox';
			enable.className = 'row-enable h-4 w-4 rounded border-slate-300';
			enable.name = `blocks[${gi}][rows][${ri}][enabled]`;
			enable.value = '1';
			checkCell.classList.add('check-cell');
			checkCell.appendChild(enable);
			enable.addEventListener('change', () => {
				syncSelectAll0State();
				syncGroupSelectAllState(gi);
			});

			// Photo ref
			const refWrap = document.createElement('div');
			refWrap.className = '';
			const refLink = document.createElement('a');
			refLink.className = 'inline-flex items-center gap-2';
			const refImg = document.createElement('img');
			refImg.className = 'w-10 h-10 rounded-lg object-cover border border-slate-300 bg-slate-100';
			refImg.alt = 'Reference';
			const refText = document.createElement('span');
			refText.className = 'text-xs text-blue-700 font-semibold hover:underline whitespace-nowrap';
			refText.textContent = 'ดูรูป';
			refLink.appendChild(refImg);
			refLink.appendChild(refText);
			refWrap.appendChild(refLink);
			photoCell.appendChild(refWrap);

			if (scrap?.image_url) {
				refWrap.classList.remove('hidden');
				refLink.href = scrap.image_url;
				refImg.src = scrap.image_url;
				refLink.addEventListener('click', (e) => {
					e.preventDefault();
					openImageModal(scrap.image_url);
				});
			} else {
				refWrap.classList.add('hidden');
			}

			// Part name (read-only)
			const scrapText = document.createElement('input');
			scrapText.type = 'text';
			scrapText.readOnly = true;
			scrapText.className = 'w-full rounded-md border border-slate-300 bg-slate-50 px-3 py-2 focus:outline-none';
			scrapText.value = scrap?.name || '';
			scrapCell.appendChild(scrapText);
			const scrapHint = document.createElement('div');
			scrapHint.className = 'text-xs text-slate-600 mt-2';
			scrapHint.textContent = 'Part name (มาจาก master data)';
			scrapCell.appendChild(scrapHint);

			// Hidden fields
			const componentPartIdHidden = document.createElement('input');
			componentPartIdHidden.type = 'hidden';
			componentPartIdHidden.name = `blocks[${gi}][rows][${ri}][component_part_id]`;
			componentPartIdHidden.value = scrap?.id || '';
			scrapCell.appendChild(componentPartIdHidden);

			const defectIdHidden = document.createElement('input');
			defectIdHidden.type = 'hidden';
			defectIdHidden.name = `blocks[${gi}][rows][${ri}][defect_id]`;
			defectIdHidden.value = scrap?.defect_id || '';
			scrapCell.appendChild(defectIdHidden);

			const componentPartNameHidden = document.createElement('input');
			componentPartNameHidden.type = 'hidden';
			componentPartNameHidden.name = `blocks[${gi}][rows][${ri}][component_part_name]`;
			componentPartNameHidden.value = scrap?.name || '';
			scrapCell.appendChild(componentPartNameHidden);

			// Quantity (manual input)
			const qty = document.createElement('input');
			qty.type = 'number';
			qty.min = '1';
			qty.step = '1';
			qty.value = '1';
			qty.inputMode = 'numeric';
			qty.className = 'row-qty w-full rounded-md border border-slate-300 bg-white px-2 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-red-500';
			qty.name = `blocks[${gi}][rows][${ri}][quantity]`;
			qtyCell.appendChild(qty);

			const enableOnInteract = () => { if (!enable.checked) enable.checked = true; };
			qty.addEventListener('change', enableOnInteract);
			qty.addEventListener('focus', enableOnInteract);

			// Per-row comment when defect mode is 'อื่นๆ' — placed in defect-cell of the header/group row
			const selectEl = gi === 0 ? topDefectSelect : (extraGroups.find(g => g.gi === gi)?.defectSelect);
			const resolvedDefectCell = defectCell
				|| (gi === 0 ? topHeaderRowEl?.querySelector('.defect-cell') : extraGroups.find(g => g.gi === gi)?.headerRowEl?.querySelector('.defect-cell'));
			const commentInput = ensureRowCommentInput({ gi, ri, defectCell: resolvedDefectCell });
			const show = isOtherDefectSelected(selectEl);
			if (commentInput) {
				commentInput.style.display = show ? '' : 'none';
				if (!show) commentInput.value = '';
			}
		}

		function refreshCommentVisibilityForGroup(gi) {
			if (gi === 0) {
				const defectCellEl = topHeaderRowEl?.querySelector('.defect-cell');
				if (!defectCellEl) return;
				const show = isOtherDefectSelected(topDefectSelect);
				const input = ensureRowCommentInput({ gi: 0, ri: 0, defectCell: defectCellEl });
				if (input) {
					input.style.display = show ? '' : 'none';
					if (!show) input.value = '';
				}
				return;
			}

			const g = extraGroups.find(x => x.gi === gi);
			if (!g) return;
			const show = isOtherDefectSelected(g.defectSelect);
			const defectCellEl = g.headerRowEl?.querySelector('.defect-cell');
			if (!defectCellEl) return;
			const input = ensureRowCommentInput({ gi, ri: 0, defectCell: defectCellEl });
			if (input) {
				input.style.display = show ? '' : 'none';
				if (!show) input.value = '';
			}
		}

		function rebuildBlockRows(gi, lineId, partId, defectId, rowsWrap, headerRowEl = null) {
			const hDefectCell = headerRowEl?.querySelector('.defect-cell') || null;

			// Determine component_parts to show
			// Priority: defect.component_parts → part.component_parts → placeholder
			let normalized;
			if (defectId === '__other__') {
				normalized = [{ id: '', name: 'Part name', defect_id: '__other__', image_url: '' }];
			} else if (defectId) {
				const defect = defectByIdFor(lineId, partId, defectId);
				const cp = defect ? (defect.component_parts || []) : [];
				normalized = cp.length ? cp : [{ id: '', name: 'Part name', defect_id: defectId, image_url: '' }];
			} else if (partId) {
				// No defect selected yet — show rows from part.component_parts
				const part = getPart(lineId, partId);
				const cp = part ? (part.component_parts || []) : [];
				normalized = cp.length ? cp.map(s => ({ ...s, defect_id: '' })) : [{ id: '', name: 'Part name', defect_id: '', image_url: '' }];
			} else {
				// Nothing selected — clear everything
				rowsWrap.innerHTML = '';
				if (headerRowEl) {
					headerRowEl.querySelector('.check-cell').innerHTML = '';
					headerRowEl.querySelector('.photo-cell').innerHTML = '';
					headerRowEl.querySelector('.scrap-cell').innerHTML = '';
					headerRowEl.querySelector('.qty-cell').innerHTML = '';
				}
				return;
			}

			// Check if rows already exist with same count — if so, just update defect_id hidden fields
			const existingHeaderHasContent = headerRowEl && headerRowEl.querySelector('.check-cell input.row-enable');
			const existingRowCount = rowsWrap.querySelectorAll('.row-enable').length + (existingHeaderHasContent ? 1 : 0);
			const sameCount = existingRowCount === normalized.length;

			if (sameCount && existingRowCount > 0) {
				// Update defect_id hidden fields in-place
				const allDefectHiddens = [];
				if (headerRowEl) {
					const h = headerRowEl.querySelector(`input[name="blocks[${gi}][rows][0][defect_id]"]`);
					if (h) allDefectHiddens.push(h);
				}
				rowsWrap.querySelectorAll(`input[name^="blocks[${gi}][rows]"][name$="[defect_id]"]`).forEach(h => allDefectHiddens.push(h));
				allDefectHiddens.forEach(h => { h.value = defectId || ''; });
				refreshCommentVisibilityForGroup(gi);
				return;
			}

			// Full rebuild
			rowsWrap.innerHTML = '';
			if (headerRowEl) {
				headerRowEl.querySelector('.check-cell').innerHTML = '';
				headerRowEl.querySelector('.photo-cell').innerHTML = '';
				headerRowEl.querySelector('.scrap-cell').innerHTML = '';
				headerRowEl.querySelector('.qty-cell').innerHTML = '';
			}

			if (headerRowEl) {
				buildScrapCells({
					gi,
					ri: 0,
					scrap: normalized[0],
					checkCell: headerRowEl.querySelector('.check-cell'),
					photoCell: headerRowEl.querySelector('.photo-cell'),
					scrapCell: headerRowEl.querySelector('.scrap-cell'),
					qtyCell: headerRowEl.querySelector('.qty-cell'),
					defectCell: hDefectCell,
				});
				for (let idx = 1; idx < normalized.length; idx++) {
					rowsWrap.appendChild(buildScrapRow({ gi, ri: idx, scrap: normalized[idx], defectCell: hDefectCell }));
				}
				refreshCommentVisibilityForGroup(gi);
				return;
			}

			normalized.forEach((s, idx) => rowsWrap.appendChild(buildScrapRow({ gi, ri: idx, scrap: s, defectCell: hDefectCell })));
			refreshCommentVisibilityForGroup(gi);
		}

		function refreshPartsAndDefects() {
			const lineId = getCurrentLineId();
			productionLineInput.value = lineId;
			setHintVisible(headerHints?.lineHint, !lineId);

			// Parts
			const parts = currentParts().map(p => ({ value: p.id, label: (p.sd_number || p.part_number || p.id) }));
			const prevPart = partSelect.value;
			setOptions(partSelect, parts);
			if (prevPart && parts.some(p => p.value === prevPart)) partSelect.value = prevPart;
			setHintVisible(headerHints?.partHint, !partSelect.value);

			// Defects
			const defects = currentDefects();
			const defectOpts = defects.map(d => ({ value: d.id, label: d.name || d.id }));
			const prevTopDefect = topDefectSelect.value;
			setDefectOptions(topDefectSelect, defectOpts, '— Select defect —');
			if (prevTopDefect && (defectOpts.some(d => d.value === prevTopDefect) || prevTopDefect === '__other__')) topDefectSelect.value = prevTopDefect;
			setHintVisible(headerHints?.defectHint, !topDefectSelect.value);

			// Refresh extra groups independently (their own line/part)
			extraGroups.forEach(g => {
				const gLine = (g.lineInput?.value || '').trim().toUpperCase();
				if (g.lineInput) g.lineInput.value = gLine;
				setHintVisible(g.lineHint, !gLine);
				const gParts = (getLine(gLine)?.parts || []).map(p => ({ value: p.id, label: (p.sd_number || p.part_number || p.id) }));
				const prevPart = g.partSelect?.value || '';
				setOptions(g.partSelect, gParts);
				if (prevPart && gParts.some(p => p.value === prevPart)) g.partSelect.value = prevPart;
				setHintVisible(g.partHint, !(g.partSelect?.value || ''));
				const gPartId = g.partSelect?.value || '';
				const gDefectOpts = defectsFor(gLine, gPartId).map(d => ({ value: d.id, label: d.name || d.id }));
				const prevDef = g.defectSelect.value;
				setDefectOptions(g.defectSelect, gDefectOpts, '— Select defect —');
				if (prevDef && (gDefectOpts.some(d => d.value === prevDef) || prevDef === '__other__')) g.defectSelect.value = prevDef;
				setHintVisible(g.defectHint, !g.defectSelect.value);
			});

			// Rebuild rows for every block
			rebuildBlockRows(0, lineId, partSelect.value, topDefectSelect.value, document.getElementById('rows-0'), topHeaderRowEl);
			extraGroups.forEach(g => {
				const gLine = (g.lineInput?.value || '').trim().toUpperCase();
				const gPart = g.partSelect?.value || '';
				rebuildBlockRows(g.gi, gLine, gPart, g.defectSelect.value, g.rowsWrap, g.headerRowEl);
			});
		}

		function addExtraGroup() {
			// If user already filled the first row, carry over Production line + SD number
			// and lock them (grey) for all added groups.
			const defaultLineId = getCurrentLineId();
			const defaultPartId = partSelect?.value || '';
			const shouldLockFromHeader = !!(defaultLineId && defaultPartId);

			const gi = nextGroupIndex++;
			const group = groupTpl.content.firstElementChild.cloneNode(true);
			const rowsWrap = group.querySelector('.space-y-0');

			// Row 1: per-group select-all only
			const groupAllRow = rowTpl.content.firstElementChild.cloneNode(true);
			groupAllRow.classList.add('group-all-row');
			groupAllRow.querySelector('.line-cell').innerHTML = '';
			groupAllRow.querySelector('.part-cell').innerHTML = '';
			groupAllRow.querySelector('.defect-cell').innerHTML = '';
			groupAllRow.querySelector('.photo-cell').innerHTML = '';
			groupAllRow.querySelector('.scrap-cell').innerHTML = '';
			groupAllRow.querySelector('.qty-cell').innerHTML = '';
			const groupAllCell = groupAllRow.querySelector('.check-cell');
			groupAllCell.innerHTML = '';
			groupAllCell.classList.add('check-cell');
			groupAllCell.style.minHeight = '2.5rem';
			groupAllCell.style.alignItems = 'center';
			groupAllCell.style.justifyContent = 'center';
			const groupAllWrap = document.createElement('label');
			groupAllWrap.className = 'inline-flex flex-row items-center justify-center gap-1 select-none';
			const groupAll = document.createElement('input');
			groupAll.type = 'checkbox';
			groupAll.className = 'group-select-all h-4 w-4 rounded border-slate-300 text-red-600 focus:ring-red-500';
			groupAll.title = 'เลือกทั้งหมดในชุดนี้';
			groupAll.setAttribute('aria-label', 'เลือกทั้งหมด');
			const groupAllText = document.createElement('span');
			groupAllText.className = 'text-[10px] leading-tight font-semibold text-slate-700 whitespace-nowrap text-center';
			groupAllText.textContent = 'เลือกทั้งหมด';
			groupAllWrap.appendChild(groupAll);
			groupAllWrap.appendChild(groupAllText);
			groupAllCell.appendChild(groupAllWrap);
			rowsWrap.appendChild(groupAllRow);

			// Create a header row (Line + Part + Defect) for this group
			const defectRow = rowTpl.content.firstElementChild.cloneNode(true);
			defectRow.querySelector('.check-cell').innerHTML = '';
			defectRow.querySelector('.photo-cell').innerHTML = '';
			defectRow.querySelector('.scrap-cell').innerHTML = '';
			defectRow.querySelector('.qty-cell').innerHTML = '';
			defectRow.classList.add('header-row');

			// Line
			const lineCell = defectRow.querySelector('.line-cell');
			const lineMirror = document.createElement('input');
			lineMirror.type = 'text';
			lineMirror.name = `blocks[${gi}][production_line]`;
			lineMirror.placeholder = 'Input or scan';
			lineMirror.value = shouldLockFromHeader ? defaultLineId : '';
			lineMirror.setAttribute('list', `production-lines-${gi}`);
			lineMirror.className = 'production-line-input flex-1 min-w-0 w-full rounded-md border border-slate-300 bg-white pl-3 pr-10 py-2 focus:outline-none focus:ring-2 focus:ring-red-500';
			const lineMirrorWrap = document.createElement('div');
			lineMirrorWrap.className = 'relative flex items-center gap-2 w-full';
			// Group delete selector (checkbox) — inline (does not affect row height)
			const delWrap = document.createElement('label');
			delWrap.className = 'shrink-0 inline-flex items-center gap-1 text-xs text-slate-700 select-none';
			const delCheck = document.createElement('input');
			delCheck.type = 'checkbox';
			delCheck.className = 'group-remove h-4 w-4 rounded border-slate-300';
			delCheck.title = 'เลือกเพื่อลบกลุ่มนี้';
			delCheck.setAttribute('aria-label', 'Select group for deletion');
			const delText = document.createElement('span');
			delText.textContent = 'ลบ';
			delWrap.appendChild(delCheck);
			delWrap.appendChild(delText);
			// no select-all in this header row; it is the first row of the group
			const chevron2 = document.createElement('div');
			chevron2.className = 'datalist-chevron';
			chevron2.setAttribute('aria-hidden', 'true');
			chevron2.innerHTML = '<svg viewBox="0 0 20 20" fill="currentColor" class="h-5 w-5"><path fill-rule="evenodd" d="M5.23 7.21a.75.75 0 0 1 1.06.02L10 11.17l3.71-3.94a.75.75 0 1 1 1.08 1.04l-4.25 4.5a.75.75 0 0 1-1.08 0l-4.25-4.5a.75.75 0 0 1 .02-1.06Z" clip-rule="evenodd" /></svg>';
			chevron2.addEventListener('click', (e) => {
				e.preventDefault();
				e.stopPropagation();
				openDatalistForInput(lineMirror);
			});
			lineMirrorWrap.addEventListener('click', (e) => {
				if (e.target === lineMirror) return;
				openDatalistForInput(lineMirror);
			});
			lineMirrorWrap.appendChild(delWrap);
			lineMirrorWrap.appendChild(lineMirror);
			lineMirrorWrap.appendChild(chevron2);
			const lineList = document.createElement('datalist');
			lineList.id = `production-lines-${gi}`;
			lineCell.appendChild(lineMirrorWrap);
			lineCell.appendChild(lineList);
			const lineHint = document.createElement('div');
			lineHint.className = 'text-xs text-slate-600 mt-1';
			lineHint.textContent = 'กรุณาใส่หรือสแกน Production line';
			lineCell.appendChild(lineHint);

			// Part
			const partCell = defectRow.querySelector('.part-cell');
			const partMirror = document.createElement('select');
			partMirror.name = `blocks[${gi}][part_number]`;
			partMirror.className = 'w-full rounded-md border border-slate-300 bg-white px-3 py-2 focus:outline-none focus:ring-2 focus:ring-red-500';
			partCell.appendChild(partMirror);
			const partHint = document.createElement('div');
			partHint.className = 'text-xs text-slate-600 mt-1';
			partHint.textContent = 'เลือก SD number';
			partCell.appendChild(partHint);

			const defectCell = defectRow.querySelector('.defect-cell');
			const sel = document.createElement('select');
			sel.name = `blocks[${gi}][defect_mode]`;
			sel.className = 'w-full rounded-md border border-slate-300 bg-white px-3 py-2 focus:outline-none focus:ring-2 focus:ring-red-500';
			defectCell.appendChild(sel);
			const hint = document.createElement('div');
			hint.className = 'text-xs text-slate-600 mt-1';
			hint.textContent = 'เลือก Defect mode';
			defectCell.appendChild(hint);

			rowsWrap.appendChild(defectRow);

			const scrapRowsWrap = document.createElement('div');
			scrapRowsWrap.className = 'space-y-2 mt-1';
			rowsWrap.appendChild(scrapRowsWrap);

			groupsWrap.appendChild(group);

			populateLineDatalist(lineList);
			setOptions(partMirror, []);
			setDefectOptions(sel, [], '— Select defect —');
			const scheduleRefresh = () => {
				const gLine = (lineMirror.value || '').trim().toUpperCase();
				lineMirror.value = gLine;
				setHintVisible(lineHint, !gLine);
				const parts = (getLine(gLine)?.parts || []).map(p => ({ value: p.id, label: (p.sd_number || p.part_number || p.id) }));
				const prevPart = shouldLockFromHeader ? defaultPartId : partMirror.value;
				setOptions(partMirror, parts);
				if (prevPart && parts.some(p => p.value === prevPart)) partMirror.value = prevPart;
				setHintVisible(partHint, !partMirror.value);
				const gPart = partMirror.value;
				const defectOpts = defectsFor(gLine, gPart).map(d => ({ value: d.id, label: d.name || d.id }));
				const prevDef = sel.value;
				setDefectOptions(sel, defectOpts, '— Select defect —');
				if (prevDef && (defectOpts.some(d => d.value === prevDef) || prevDef === '__other__')) sel.value = prevDef;
				setHintVisible(hint, !sel.value);
				rebuildBlockRows(gi, gLine, gPart, sel.value, scrapRowsWrap, defectRow);
			};

			let t = null;
			if (shouldLockFromHeader) {
				lockFieldWithHidden({
					fieldEl: lineMirror,
					containerEl: lineCell,
					hiddenName: `blocks[${gi}][production_line]`,
					value: defaultLineId,
				});
				lockFieldWithHidden({
					fieldEl: partMirror,
					containerEl: partCell,
					hiddenName: `blocks[${gi}][part_number]`,
					value: defaultPartId,
				});
				// Ensure select matches the locked value after options are loaded
				try { scheduleRefresh(); } catch {}
				// Ensure hidden values track any programmatic refresh
				const hiddenLine = lineCell.querySelector(`input[type="hidden"][name="blocks[${gi}][production_line]"]`);
				const hiddenPart = partCell.querySelector(`input[type="hidden"][name="blocks[${gi}][part_number]"]`);
				if (hiddenLine) hiddenLine.value = defaultLineId;
				if (hiddenPart) hiddenPart.value = defaultPartId;
			}

			lineMirror.addEventListener('change', scheduleRefresh);
			lineMirror.addEventListener('input', scheduleRefresh);
			partMirror.addEventListener('change', scheduleRefresh);
			sel.addEventListener('change', scheduleRefresh);

			groupAll.addEventListener('change', () => setGroupRowsEnabled(gi, groupAll.checked));

			extraGroups.push({ gi, groupEl: group, defectSelect: sel, rowsWrap: scrapRowsWrap, lineInput: lineMirror, partSelect: partMirror, lineList, lineHint, partHint, defectHint: hint, headerRowEl: defectRow, removeCheck: delCheck, groupSelectAll: groupAll, groupAllRowEl: groupAllRow });
			removeGroupBtn.disabled = extraGroups.length === 0;
			syncGroupSelectAllState(gi);
			syncSelectAll0State();
		};

		function removeSelectedExtraGroups() {
			let removed = 0;
			for (let idx = extraGroups.length - 1; idx >= 0; idx--) {
				const g = extraGroups[idx];
				if (g?.removeCheck?.checked) {
					g.groupEl.remove();
					extraGroups.splice(idx, 1);
					removed++;
				}
			}
			if (removed === 0) {
				const g = extraGroups.pop();
				if (!g) return;
				g.groupEl.remove();
				removeGroupBtn.disabled = extraGroups.length === 0;
				return;
			}
			removeGroupBtn.disabled = extraGroups.length === 0;
			refreshPartsAndDefects();
			syncSelectAll0State();
		}

		function clearAll() {
			groupsWrap.innerHTML = '';
			extraGroups.splice(0, extraGroups.length);
			removeGroupBtn.disabled = true;
			nextGroupIndex = 1;

			// Header group container
			const group0 = groupTpl.content.firstElementChild.cloneNode(true);
			const rowsWrap0 = group0.querySelector('.space-y-0');
			const headerRow = buildHeaderRow();
			topHeaderRowEl = headerRow;
			rowsWrap0.appendChild(headerRow);

			// Dedicated container for group0 scrap rows
			const rows0 = document.createElement('div');
			rows0.id = 'rows-0';
			rows0.className = 'space-y-2 mt-1';
			rowsWrap0.appendChild(rows0);

			groupsWrap.appendChild(group0);

			// Populate datalist
			populateLineDatalist(productionLineList);

			let plTimer = null;
			const scheduleRefresh = () => {
				clearTimeout(plTimer);
				plTimer = setTimeout(refreshPartsAndDefects, 40);
			};
			productionLineInput.addEventListener('input', scheduleRefresh);
			productionLineInput.addEventListener('change', refreshPartsAndDefects);
			productionLineInput.addEventListener('blur', refreshPartsAndDefects);
			partSelect.addEventListener('change', refreshPartsAndDefects);
			topDefectSelect.addEventListener('change', () => {
				rebuildBlockRows(0, getCurrentLineId(), partSelect.value, topDefectSelect.value, rows0, topHeaderRowEl);
				refreshCommentVisibilityForGroup(0);
			});

			refreshPartsAndDefects();
		}

		if (selectAll0) {
			selectAll0.addEventListener('change', () => setAll0RowsEnabled(selectAll0.checked));
		}
		clearBtn.addEventListener('click', clearAll);
		addGroupBtn.addEventListener('click', addExtraGroup);
		removeGroupBtn.addEventListener('click', removeSelectedExtraGroups);

		clearAll();
		syncSelectAll0State();
	};

	if (document.readyState === 'loading') {
		document.addEventListener('DOMContentLoaded', init);
	} else {
		init();
	}
})();

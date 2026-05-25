(() => {
	const init = () => {
		const dataEl = document.getElementById('record-data');
		const recordData = dataEl ? JSON.parse(dataEl.textContent) : { productionLines: [] };
		const lines = recordData.productionLines || [];

		const blocksWrap = document.getElementById('blocks');
		const clearBtn = document.getElementById('clear');
		const blockTpl = document.getElementById('block-template');
		const sectionTpl = document.getElementById('defect-section-template');
		const scrapTpl = document.getElementById('scrap-row-template');

		let nextGi = 1;       // block index in the submitted field names (0 stays unused)
		let nextUid = 1;      // unique id suffix for per-block datalists

		const toInt = (v) => { const n = parseInt(String(v ?? '').replace(/[^0-9]/g, ''), 10); return Number.isFinite(n) ? n : 0; };
		// Scrap qty is a whole number (integer field + step=1 input), so round the
		// auto-calculated value; the worker can still adjust it by hand.
		const fmtQty = (n) => String(Math.round(n));

		// ----------------------------------------------------------------- data lookups
		const getLine = (id) => lines.find((l) => l.id === id) || null;
		const getPart = (lineId, partId) => {
			const l = getLine(lineId);
			return l ? (l.parts || []).find((p) => p.id === partId) || null : null;
		};
		// Resolve a typed/scanned value (sd_number, part_number, or UUID) → part UUID
		const resolvePartId = (lineId, value) => {
			const v = (value || '').trim();
			if (!v) return '';
			const l = getLine(lineId);
			if (!l) return '';
			const hit = (l.parts || []).find((p) =>
				p.id === v ||
				(p.sd_number || '').toLowerCase() === v.toLowerCase() ||
				(p.part_number || '').toLowerCase() === v.toLowerCase()
			);
			return hit ? hit.id : '';
		};
		const defectsFor = (lineId, partId) => {
			const p = getPart(lineId, partId);
			return p ? (p.defects || []) : [];
		};
		const defectById = (lineId, partId, did) => defectsFor(lineId, partId).find((d) => d.id === did) || null;

		// Scrap rows for a defect = the FG (product itself) first, then BOM children.
		const normalizedScraps = (lineId, partId, did) => {
			const part = getPart(lineId, partId);
			if (!part) return [];
			let components;
			if (did === '__other__') {
				components = (part.component_parts || []).map((s) => ({ ...s, defect_id: '__other__' }));
			} else if (did) {
				const d = defectById(lineId, partId, did);
				components = (d ? (d.component_parts || []) : []).map((s) => ({ ...s, defect_id: did }));
			} else {
				components = (part.component_parts || []).map((s) => ({ ...s, defect_id: '' }));
			}
			const fg = {
				id: partId,
				name: part.part_name || part.sd_number || part.part_number || '',
				sd_code: part.sd_number || '',
				part_number: part.part_number || '',
				image_url: part.image_url || '',
				defect_id: did || '',
				is_fg: true,
				bom_qty: 1, // FG scrap = defect qty × 1
			};
			return [fg, ...components];
		};

		// ----------------------------------------------------------------- datalists / options
		const populateLineDatalist = (el) => {
			if (!el) return;
			el.innerHTML = '';
			lines.forEach((l) => {
				const o = document.createElement('option');
				o.value = l.id;
				el.appendChild(o);
			});
		};
		const populatePartDatalist = (el, lineId) => {
			if (!el) return;
			el.innerHTML = '';
			(getLine(lineId)?.parts || []).forEach((p) => {
				const o = document.createElement('option');
				o.value = p.sd_number || p.part_number || p.id;
				el.appendChild(o);
			});
		};
		const setDefectOptions = (select, options) => {
			const prev = select.value;
			select.innerHTML = '';
			const ph = document.createElement('option');
			ph.value = '';
			ph.textContent = '— Select defect —';
			select.appendChild(ph);
			options.forEach((opt) => {
				const o = document.createElement('option');
				o.value = opt.value;
				o.textContent = opt.label;
				select.appendChild(o);
			});
			const other = document.createElement('option');
			other.value = '__other__';
			other.textContent = 'อื่นๆ';
			select.appendChild(other);
			if (prev && (options.some((o) => o.value === prev) || prev === '__other__')) select.value = prev;
		};
		const isOther = (select) => {
			if (!select) return false;
			if (select.value === '__other__') return true;
			return (select.options[select.selectedIndex]?.textContent || '').trim() === 'อื่นๆ';
		};

		// ----------------------------------------------------------------- image modal
		const imageModal = document.getElementById('imageModal');
		const imageModalImg = document.getElementById('imageModalImg');
		const openImageModal = (url) => {
			if (!url) return;
			if (!imageModal || !imageModalImg) { window.open(url, '_blank', 'noreferrer'); return; }
			imageModalImg.src = url;
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
			imageModal.querySelectorAll('[data-image-modal-close]').forEach((b) => b.addEventListener('click', closeImageModal));
			imageModal.querySelectorAll('[data-image-modal-backdrop]').forEach((b) => b.addEventListener('click', closeImageModal));
			document.addEventListener('keydown', (e) => { if (e.key === 'Escape') closeImageModal(); });
		}

		// Force-open a datalist for an input (best-effort across browsers).
		const openDatalist = (inputEl) => {
			if (!inputEl || inputEl.disabled) return;
			try { inputEl.focus({ preventScroll: true }); } catch { inputEl.focus(); }
			if (typeof inputEl.showPicker === 'function') { try { inputEl.showPicker(); return; } catch {} }
			try { inputEl.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowDown', bubbles: true })); } catch {}
		};

		const mkHidden = (name) => {
			const h = document.createElement('input');
			h.type = 'hidden';
			h.name = name;
			return h;
		};

		// ----------------------------------------------------------------- block (1 product / lot)
		function buildBlock(prefillLine = '') {
			const el = blockTpl.content.firstElementChild.cloneNode(true);
			const lineInput = el.querySelector('[data-line]');
			const lineList = el.querySelector('[data-line-list]');
			const sdInput = el.querySelector('[data-sd]');
			const sdList = el.querySelector('[data-sd-list]');
			const prodQtyInput = el.querySelector('[data-prodqty]');
			const sectionsWrap = el.querySelector('[data-defect-sections]');
			const addBtn = el.querySelector('[data-add-defect]');
			const removeBtn = el.querySelector('[data-remove-defect]');

			const uid = nextUid++;
			lineList.id = `lines-${uid}`;
			lineInput.setAttribute('list', lineList.id);
			sdList.id = `sds-${uid}`;
			sdInput.setAttribute('list', sdList.id);
			populateLineDatalist(lineList);

			const block = { el, lineInput, sdInput, prodQtyInput, sectionsWrap, sections: [], partId: '' };
			const lineId = () => (lineInput.value || '').trim().toUpperCase();

			// --- mirror product header into a section's hidden block fields ---
			const mirror = (sec) => {
				sec.hidLine.value = lineId();
				sec.hidPart.value = block.partId || (sdInput.value || '').trim();
				sec.hidProd.value = (prodQtyInput.value || '').trim();
			};

			const fgEnable = (sec) => sec.scrapsWrap.querySelector('[data-enable][data-fg]');
			const componentEnables = (sec) => Array.from(sec.scrapsWrap.querySelectorAll('[data-enable]:not([data-fg])'));

			// "เลือกทั้งหมด" covers the components only — FG is exclusive of them.
			const syncSelectAll = (sec) => {
				const boxes = componentEnables(sec);
				if (!boxes.length) { sec.selectAll.checked = false; sec.selectAll.indeterminate = false; return; }
				const n = boxes.filter((b) => b.checked).length;
				sec.selectAll.checked = n === boxes.length;
				sec.selectAll.indeterminate = n > 0 && n < boxes.length;
			};

			// Auto-fill a ticked row's Qtty = defect qty × BoM multiplier (FG = ×1).
			// Unticked rows reset to 0. The value stays user-editable afterwards.
			const rowAutoQty = (sec, rowEl) => {
				const en = rowEl.querySelector('[data-enable]');
				const q = rowEl.querySelector('[data-qty]');
				if (!en || !q) return;
				q.value = en.checked ? fmtQty(toInt(sec.defQtyInput.value) * (Number(q.dataset.bomQty) || 0)) : '0';
			};
			const recomputeSectionQtys = (sec, { includeUnchecked = false } = {}) => {
				sec.scrapsWrap.querySelectorAll('.scrap-row').forEach((rowEl) => {
					const en = rowEl.querySelector('[data-enable]');
					if (en && (en.checked || includeUnchecked)) rowAutoQty(sec, rowEl);
				});
			};
			const setRowEnabled = (sec, enableEl, checked) => {
				enableEl.checked = checked;
				const rowEl = enableEl.closest('.scrap-row');
				if (rowEl) rowAutoQty(sec, rowEl);
			};
			// FG and components are mutually exclusive: ticking FG clears all
			// components; ticking any component clears FG.
			const handleEnableToggle = (sec, enableEl, rowEl) => {
				if (enableEl.checked) {
					if (enableEl.dataset.fg) {
						componentEnables(sec).forEach((c) => { if (c.checked) setRowEnabled(sec, c, false); });
					} else {
						const fg = fgEnable(sec);
						if (fg && fg.checked) setRowEnabled(sec, fg, false);
					}
				}
				rowAutoQty(sec, rowEl);
				syncSelectAll(sec);
			};

			const buildScrapRow = (sec, ri, scrap) => {
				const row = scrapTpl.content.firstElementChild.cloneNode(true);
				const enable = row.querySelector('[data-enable]');
				enable.name = `blocks[${sec.gi}][rows][${ri}][enabled]`;
				if (scrap?.is_fg) enable.dataset.fg = '1';
				enable.addEventListener('change', () => handleEnableToggle(sec, enable, row));

				const photo = row.querySelector('[data-photo]');
				const photoImg = row.querySelector('[data-photo-img]');
				if (scrap?.image_url) {
					photo.href = scrap.image_url;
					photoImg.src = scrap.image_url;
					photo.addEventListener('click', (e) => { e.preventDefault(); openImageModal(scrap.image_url); });
				} else {
					// No reference image — keep an empty placeholder box in the image column.
					photoImg.removeAttribute('src');
					photo.removeAttribute('href');
				}

				const nameInput = row.querySelector('[data-name]');
				let disp = [scrap?.sd_code, scrap?.name].filter(Boolean).join(' — ') || (scrap?.name || '');
				if (scrap?.is_fg) {
					disp = `FG · ${disp}`.trim();
					nameInput.classList.add('font-semibold');
					nameInput.style.backgroundColor = '#ecfdf5'; // emerald-50
				}
				nameInput.value = disp;

				const cpid = row.querySelector('[data-cpid]');
				cpid.name = `blocks[${sec.gi}][rows][${ri}][component_part_id]`;
				cpid.value = scrap?.id || '';
				const defid = row.querySelector('[data-defid]');
				defid.name = `blocks[${sec.gi}][rows][${ri}][defect_id]`;
				defid.value = scrap?.defect_id || '';
				const cpname = row.querySelector('[data-cpname]');
				cpname.name = `blocks[${sec.gi}][rows][${ri}][component_part_name]`;
				cpname.value = scrap?.name || '';

				const qty = row.querySelector('[data-qty]');
				qty.name = `blocks[${sec.gi}][rows][${ri}][quantity]`;
				qty.dataset.bomQty = String(Number(scrap?.bom_qty) || 0);
				const enableOnInteract = () => { if (!enable.checked) { enable.checked = true; handleEnableToggle(sec, enable, row); } };
				qty.addEventListener('focus', enableOnInteract);
				qty.addEventListener('change', enableOnInteract);

				return row;
			};

			const rebuildScraps = (sec) => {
				sec.scrapsWrap.innerHTML = '';
				const rows = block.partId ? normalizedScraps(lineId(), block.partId, sec.defectSelect.value || '') : [];
				rows.forEach((s, ri) => sec.scrapsWrap.appendChild(buildScrapRow(sec, ri, s)));
				sec.scrapsEmpty.classList.toggle('hidden', rows.length > 0);
				syncSelectAll(sec);
			};

			const updateDefectIds = (sec) => {
				const v = sec.defectSelect.value || '';
				sec.scrapsWrap.querySelectorAll('[data-defid]').forEach((h) => { h.value = v; });
			};

			const toggleComment = (sec) => {
				const show = isOther(sec.defectSelect);
				sec.commentInput.classList.toggle('hidden', !show);
				if (!show) sec.commentInput.value = '';
			};

			const repopulateDefects = (sec) => {
				const opts = defectsFor(lineId(), block.partId).map((d) => ({ value: d.id, label: d.name || d.id }));
				setDefectOptions(sec.defectSelect, opts);
				sec.defectHint.style.display = sec.defectSelect.value ? 'none' : '';
			};

			const addSection = () => {
				const gi = nextGi++;
				const secEl = sectionTpl.content.firstElementChild.cloneNode(true);
				const defectSelect = secEl.querySelector('[data-defect]');
				const defQtyInput = secEl.querySelector('[data-defqty]');
				defQtyInput.name = `blocks[${gi}][defect_quantity]`;
				const commentInput = secEl.querySelector('[data-comment]');
				commentInput.name = `blocks[${gi}][rows][0][comment]`;
				const scrapsWrap = secEl.querySelector('[data-scraps]');
				const scrapsEmpty = secEl.querySelector('[data-scraps-empty]');
				const selectAll = secEl.querySelector('[data-select-all]');
				const defectHint = secEl.querySelector('[data-defect-hint]');

				const hidLine = mkHidden(`blocks[${gi}][production_line]`);
				const hidPart = mkHidden(`blocks[${gi}][part_number]`);
				const hidProd = mkHidden(`blocks[${gi}][production_quantity]`);
				secEl.appendChild(hidLine);
				secEl.appendChild(hidPart);
				secEl.appendChild(hidProd);

				const sec = {
					gi, el: secEl, defectSelect, defQtyInput, commentInput,
					scrapsWrap, scrapsEmpty, selectAll, defectHint, hidLine, hidPart, hidProd,
				};

				setDefectOptions(defectSelect, []);
				defectSelect.addEventListener('change', () => {
					updateDefectIds(sec);
					toggleComment(sec);
					defectHint.style.display = defectSelect.value ? 'none' : '';
					updateButtons();
				});
				defQtyInput.addEventListener('input', () => { recomputeSectionQtys(sec); updateButtons(); });
				selectAll.addEventListener('change', () => {
					const on = selectAll.checked;
					const fg = fgEnable(sec);
					if (fg) setRowEnabled(sec, fg, false); // FG never part of "select all"
					componentEnables(sec).forEach((c) => setRowEnabled(sec, c, on));
					syncSelectAll(sec);
				});

				block.sections.push(sec);
				sectionsWrap.appendChild(secEl);
				mirror(sec);
				repopulateDefects(sec);
				rebuildScraps(sec);
				updateButtons();
				return sec;
			};

			const removeLastSection = () => {
				if (block.sections.length <= 1) return;
				const sec = block.sections.pop();
				sec.el.remove();
				updateButtons();
			};

			// Only the product header must be filled to add a defect section:
			// Production line + SD number + Production Qty (any non-blank values).
			const headerComplete = () =>
				(lineInput.value || '').trim() !== '' &&
				(sdInput.value || '').trim() !== '' &&
				(prodQtyInput.value || '').trim() !== '';
			// "เพิ่ม": enabled once the header is filled.
			// "ลบ": only when there is more than one section to remove.
			function updateButtons() {
				addBtn.disabled = !headerComplete();
				removeBtn.disabled = block.sections.length <= 1;
			}

			// Product header changed → re-mirror; on part change also rebuild scraps.
			const onProductChanged = ({ partChanged = false } = {}) => {
				lineInput.value = lineId();
				populatePartDatalist(sdList, lineId());
				if (partChanged) block.partId = resolvePartId(lineId(), sdInput.value);
				block.sections.forEach((sec) => {
					mirror(sec);
					if (partChanged) {
						repopulateDefects(sec);
						rebuildScraps(sec);
					}
				});
				updateButtons();
			};

			lineInput.addEventListener('input', () => onProductChanged({ partChanged: true }));
			lineInput.addEventListener('change', () => onProductChanged({ partChanged: true }));
			sdInput.addEventListener('input', () => onProductChanged({ partChanged: true }));
			sdInput.addEventListener('change', () => onProductChanged({ partChanged: true }));
			prodQtyInput.addEventListener('input', () => { block.sections.forEach(mirror); updateButtons(); });
			prodQtyInput.addEventListener('change', () => { block.sections.forEach(mirror); updateButtons(); });

			el.querySelector('[data-line-chevron]')?.addEventListener('click', (e) => { e.preventDefault(); openDatalist(lineInput); });
			el.querySelector('[data-sd-chevron]')?.addEventListener('click', (e) => { e.preventDefault(); openDatalist(sdInput); });

			addBtn.addEventListener('click', addSection);
			removeBtn.addEventListener('click', removeLastSection);

			if (prefillLine) lineInput.value = prefillLine;

			blocksWrap.appendChild(el);
			addSection(); // every block starts with one defect section
			return block;
		}

		function clearAll() {
			blocksWrap.innerHTML = '';
			nextGi = 1;
			buildBlock();
		}

		clearBtn.addEventListener('click', clearAll);
		clearAll();
	};

	if (document.readyState === 'loading') {
		document.addEventListener('DOMContentLoaded', init);
	} else {
		init();
	}
})();

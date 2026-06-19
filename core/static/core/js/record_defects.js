/**
 * Record — Page 2 (defect & scrap entry).
 *
 * Reads the production draft saved by Page 1 from ``sessionStorage`` under
 * ``tbsm:record:draft``. For each entry (one row in Step 1 with prodQty ≥ 1)
 * we render:
 *
 *   - a read-only header (line, part, qty produced)
 *   - one defect section (defect mode + qty + scrap rows) — extra sections
 *     can be added with "+ เพิ่มของเสีย" the same way as the old single-page
 *     /record/ did.
 *
 * Hidden fields on submit mirror the schema RecordDefectsView.post expects:
 *   blocks[gi][production_line]        line code
 *   blocks[gi][part_number]            part UUID
 *   blocks[gi][production_quantity]
 *   blocks[gi][start_time], [end_time] datetime-local strings
 *   blocks[gi][defect_quantity]
 *   blocks[gi][rows][ri][...]          scrap rows
 */
(() => {
	const STORAGE_KEY = 'tbsm:record:draft';
	const DRAFT_VERSION = 2;

	const init = () => {
		const dataEl = document.getElementById('record-data');
		const recordData = dataEl ? JSON.parse(dataEl.textContent) : { productionLines: [] };
		const lines = recordData.productionLines || [];

		const blocksWrap = document.getElementById('blocks');
		const singleBlocksWrap = document.getElementById('single-part-blocks');
		const blockTpl = document.getElementById('block-template');
		const singleBlockTpl = document.getElementById('single-part-block-template');
		const sectionTpl = document.getElementById('defect-section-template');
		const scrapTpl = document.getElementById('scrap-row-template');
		const summaryWrap = document.getElementById('summary');
		const emptyState = document.getElementById('empty-state');
		const recordForm = document.getElementById('record-form');
		const saveBtn = document.getElementById('save');

		let nextGi = 1; // global field-name index across all blocks
		const productBlocks = [];

		const toInt = (v) => { const n = parseInt(String(v ?? '').replace(/[^0-9]/g, ''), 10); return Number.isFinite(n) ? n : 0; };
		const fmtQty = (n) => String(Math.round(n));
		const defectLimitMessage = (total, max) => `จำนวนของเสียรวม (${total}) ต้องไม่เกินจำนวนผลิต (${max})`;
		const setInvalid = (input, message) => {
			if (!input) return;
			input.setCustomValidity(message || '');
			input.classList.toggle('border-red-500', Boolean(message));
			input.classList.toggle('bg-red-50', Boolean(message));
			input.title = message || '';
		};
		const validateBlockDefectLimit = (block) => {
			const max = toInt(block?.entry?.prodQty);
			const total = (block?.sections || []).reduce((sum, sec) => sum + toInt(sec.defQtyInput.value), 0);
			const message = total > max ? defectLimitMessage(total, max) : '';
			(block?.sections || []).forEach((sec) => {
				setInvalid(sec.defQtyInput, message);
				if (sec.limitMsg) {
					sec.limitMsg.textContent = message;
					sec.limitMsg.classList.toggle('hidden', !message);
				}
			});
			return !message;
		};
		const validateAllDefectTotals = ({ report = false } = {}) => {
			let ok = true;
			productBlocks.forEach((block) => {
				if (!validateBlockDefectLimit(block)) ok = false;
			});
			if (!ok && report) {
				const firstInvalid = productBlocks
					.flatMap((block) => block.sections || [])
					.map((sec) => sec.defQtyInput)
					.find((input) => input && !input.checkValidity());
				if (firstInvalid) {
					firstInvalid.focus();
					firstInvalid.reportValidity();
				} else {
					recordForm?.reportValidity();
				}
			}
			return ok;
		};
		// A defect section with qty > 0 must pick at least one scrap mode
		// (เสียทั้งชิ้น and/or ระบุพาร์ท), otherwise the user can't proceed.
		const sectionModeValid = (sec) => {
			const need = toInt(sec.defQtyInput.value) > 0 && !sec.modeFg.checked && !sec.modePart.checked;
			if (sec.modeMsg) sec.modeMsg.classList.toggle('hidden', !need);
			return !need;
		};
		const validateAllSectionModes = ({ report = false } = {}) => {
			let ok = true;
			let firstBad = null;
			productBlocks.forEach((block) => (block.sections || []).forEach((sec) => {
				if (!sectionModeValid(sec)) { ok = false; if (!firstBad) firstBad = sec; }
			}));
			if (!ok && report && firstBad) firstBad.modeFg.focus();
			return ok;
		};
		const refreshSaveState = () => {
			if (!saveBtn) return;
			saveBtn.disabled = !(validateAllDefectTotals() && validateAllSectionModes());
		};

		// ----------------------------------------------------------- data lookups
		const getLine = (id) => lines.find((l) => l.id === id) || null;
		const getPart = (lineId, partId) => {
			const l = getLine(lineId);
			return l ? (l.parts || []).find((p) => p.id === partId) || null : null;
		};
		const defectsFor = (lineId, partId) => {
			const p = getPart(lineId, partId);
			return p ? (p.defects || []) : [];
		};

		// Scrap rows = FG (the product itself) first, then BOM children.
		const normalizedScraps = (lineId, partId, did) => {
			const part = getPart(lineId, partId);
			if (!part) return [];
			let components;
			if (did === '__other__') {
				// "อื่นๆ" = scrapping for a reason outside the process defects.
				// Let the operator pick ANY part (or component) used on this
				// line — not just the current part's BOM children — since the
				// discarded workpiece may be unrelated to the produced part.
				const line = getLine(lineId);
				const seen = new Set([partId]); // FG (current part) is added below
				components = [];
				(line?.parts || []).forEach((p) => {
					if (!seen.has(p.id)) {
						seen.add(p.id);
						components.push({
							id: p.id,
							name: p.part_name || p.part_number || p.sd_number || '',
							sd_code: p.sd_number || '',
							part_number: p.part_number || '',
							image_url: p.image_url || '',
							bom_qty: 1,
							defect_id: '__other__',
						});
					}
					(p.component_parts || []).forEach((c) => {
						if (seen.has(c.id)) return;
						seen.add(c.id);
						components.push({ ...c, defect_id: '__other__' });
					});
				});
			} else if (did) {
				// A specific defect is selected. The scrap candidates are the
				// part's BOM components (the payload no longer duplicates this
				// list per defect); stamp the chosen defect id onto each.
				components = (part.component_parts || []).map((s) => ({ ...s, defect_id: did }));
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
				bom_qty: 1,
			};
			return [fg, ...components];
		};

		// Every distinct part + BOM component used on a line — the candidate list
		// for a "single part" scrap (no FG, since there's no produced product).
		const singlePartScraps = (lineId) => {
			const line = getLine(lineId);
			if (!line) return [];
			const seen = new Set();
			const out = [];
			(line.parts || []).forEach((p) => {
				if (!seen.has(p.id)) {
					seen.add(p.id);
					out.push({
						id: p.id,
						name: p.part_name || p.part_number || p.sd_number || '',
						sd_code: p.sd_number || '',
						part_number: p.part_number || '',
						image_url: p.image_url || '',
					});
				}
				(p.component_parts || []).forEach((c) => {
					if (seen.has(c.id)) return;
					seen.add(c.id);
					out.push({
						id: c.id,
						name: c.name || c.part_number || c.sd_code || '',
						sd_code: c.sd_code || '',
						part_number: c.part_number || '',
						image_url: c.image_url || '',
					});
				});
			});
			return out;
		};

		// ----------------------------------------------------------- defect select
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

		// ----------------------------------------------------------- image modal
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

		const mkHidden = (name, value = '') => {
			const h = document.createElement('input');
			h.type = 'hidden';
			h.name = name;
			h.value = value;
			return h;
		};

		// ----------------------------------------------------------- block
		function buildBlock(entry) {
			const el = blockTpl.content.firstElementChild.cloneNode(true);
			const lineDisplay = el.querySelector('[data-line-display]');
			const partDisplay = el.querySelector('[data-part-display]');
			const prodQtyDisplay = el.querySelector('[data-prodqty-display]');
			const sectionsWrap = el.querySelector('[data-defect-sections]');
			const addBtn = el.querySelector('[data-add-defect]');
			const removeBtn = el.querySelector('[data-remove-defect]');

			lineDisplay.value = entry.lineCode || '';
			// Org identifies parts by SD code; show only "SD — Part No." (no part_name).
			const partLabel = [entry.sdNumber, entry.partNumber].filter(Boolean).join(' — ');
			partDisplay.value = partLabel || entry.partName || entry.partId;
			prodQtyDisplay.value = String(entry.prodQty || 0);

			const block = { el, entry, sections: [] };

			// "เลือกทั้งหมด" covers components only.
			const componentEnables = (sec) => Array.from(sec.scrapsWrap.querySelectorAll('[data-enable]:not([data-fg])'));
			const fgRow = (sec) => sec.scrapsWrap.querySelector('.scrap-row[data-row-type="fg"]');
			const compRows = (sec) => Array.from(sec.scrapsWrap.querySelectorAll('.scrap-row[data-row-type="comp"]'));
			const showEl = (el, on) => { if (el) el.style.display = on ? '' : 'none'; };
			const syncSelectAll = (sec) => {
				const boxes = componentEnables(sec);
				if (!boxes.length) { sec.selectAll.checked = false; sec.selectAll.indeterminate = false; return; }
				const n = boxes.filter((b) => b.checked).length;
				sec.selectAll.checked = n === boxes.length;
				sec.selectAll.indeterminate = n > 0 && n < boxes.length;
			};

			const rowAutoQty = (sec, rowEl) => {
				const en = rowEl.querySelector('[data-enable]');
				const q = rowEl.querySelector('[data-qty]');
				if (!en || !q) return;
				q.value = en.checked ? fmtQty(toInt(sec.defQtyInput.value) * (Number(q.dataset.bomQty) || 0)) : '0';
			};
			const recomputeSectionQtys = (sec) => {
				sec.scrapsWrap.querySelectorAll('.scrap-row').forEach((rowEl) => {
					const en = rowEl.querySelector('[data-enable]');
					if (en && en.checked) rowAutoQty(sec, rowEl);
				});
			};
			const setRowEnabled = (sec, enableEl, checked) => {
				enableEl.checked = checked;
				const rowEl = enableEl.closest('.scrap-row');
				if (rowEl) rowAutoQty(sec, rowEl);
			};
			const handleEnableToggle = (sec, enableEl, rowEl) => {
				// FG and components are independent now (both modes may be on).
				rowAutoQty(sec, rowEl);
				syncSelectAll(sec);
			};
			// Show/hide the FG row and component rows from the two mode checkboxes:
			// เสียทั้งชิ้น -> FG row, ระบุพาร์ท -> sub-part rows. Hidden rows are
			// disabled so they aren't submitted.
			const applyScrapMode = (sec) => {
				const fgOn = sec.modeFg.checked;
				const partOn = sec.modePart.checked;
				const fg = fgRow(sec);
				if (fg) {
					showEl(fg, fgOn);
					const en = fg.querySelector('[data-enable]');
					if (en) setRowEnabled(sec, en, fgOn);  // FG enable follows "เสียทั้งชิ้น"
				}
				const comps = compRows(sec);
				comps.forEach((rowEl) => {
					showEl(rowEl, partOn);
					if (!partOn) {
						const en = rowEl.querySelector('[data-enable]');
						if (en && en.checked) setRowEnabled(sec, en, false);
					}
				});
				showEl(sec.scrapsHeader, partOn && comps.length > 0);
				showEl(sec.scrapsEmpty, partOn && comps.length === 0);
				syncSelectAll(sec);
				validateBlockDefectLimit(block);
				refreshSaveState();
			};

			const buildScrapRow = (sec, ri, scrap) => {
				const row = scrapTpl.content.firstElementChild.cloneNode(true);
				row.dataset.rowType = scrap?.is_fg ? 'fg' : 'comp';
				const enable = row.querySelector('[data-enable]');
				enable.name = `blocks[${sec.gi}][rows][${ri}][enabled]`;
				if (scrap?.is_fg) {
					enable.dataset.fg = '1';
					enable.classList.add('hidden');  // FG toggled by the "เสียทั้งชิ้น" checkbox, not per-row
				}
				enable.addEventListener('change', () => handleEnableToggle(sec, enable, row));

				const photo = row.querySelector('[data-photo]');
				const photoImg = row.querySelector('[data-photo-img]');
				if (scrap?.image_url) {
					photo.href = scrap.image_url;
					photoImg.src = scrap.image_url;
					photo.addEventListener('click', (e) => { e.preventDefault(); openImageModal(scrap.image_url); });
				} else {
					photoImg.removeAttribute('src');
					photo.removeAttribute('href');
				}

				const nameInput = row.querySelector('[data-name]');
				// Show "SD — Part No." (no part_name); fall back to name if both blank.
				let disp = [scrap?.sd_code, scrap?.part_number].filter(Boolean).join(' — ') || (scrap?.name || '');
				if (scrap?.is_fg) {
					disp = `เสียทั้งชิ้น · ${disp}`.trim();
					nameInput.classList.add('font-semibold');
					nameInput.style.backgroundColor = '#ecfdf5';
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
				const rows = normalizedScraps(entry.lineCode, entry.partId, sec.defectSelect.value || '');
				rows.forEach((s, ri) => sec.scrapsWrap.appendChild(buildScrapRow(sec, ri, s)));
				applyScrapMode(sec);
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
				const opts = defectsFor(entry.lineCode, entry.partId).map((d) => ({ value: d.id, label: d.name || d.id }));
				setDefectOptions(sec.defectSelect, opts);
				sec.defectHint.style.display = sec.defectSelect.value ? 'none' : '';
			};

			const updateButtons = () => {
				removeBtn.disabled = block.sections.length <= 1;
			};

			const addSection = () => {
				const gi = nextGi++;
				const secEl = sectionTpl.content.firstElementChild.cloneNode(true);
				const defectSelect = secEl.querySelector('[data-defect]');
				const defQtyInput = secEl.querySelector('[data-defqty]');
				defQtyInput.name = `blocks[${gi}][defect_quantity]`;
				defQtyInput.max = String(toInt(entry.prodQty));
				const limitMsg = document.createElement('p');
				limitMsg.className = 'hidden mt-1 text-xs font-semibold text-red-600';
				defQtyInput.insertAdjacentElement('afterend', limitMsg);
				const commentInput = secEl.querySelector('[data-comment]');
				commentInput.name = `blocks[${gi}][rows][0][comment]`;
				const scrapsWrap = secEl.querySelector('[data-scraps]');
				const scrapsEmpty = secEl.querySelector('[data-scraps-empty]');
				const scrapsHeader = secEl.querySelector('[data-scraps-header]');
				const selectAll = secEl.querySelector('[data-select-all]');
				const defectHint = secEl.querySelector('[data-defect-hint]');
				const modeFg = secEl.querySelector('[data-mode-fg]');
				const modePart = secEl.querySelector('[data-mode-part]');
				const modeMsg = secEl.querySelector('[data-mode-msg]');

				// Per-block hidden fields — read by RecordDefectsView.post.
				secEl.appendChild(mkHidden(`blocks[${gi}][production_line]`, entry.lineCode || ''));
				secEl.appendChild(mkHidden(`blocks[${gi}][part_number]`, entry.partId || ''));
				secEl.appendChild(mkHidden(`blocks[${gi}][production_quantity]`, String(entry.prodQty || 0)));
				secEl.appendChild(mkHidden(`blocks[${gi}][start_time]`, entry.startTime || ''));
				secEl.appendChild(mkHidden(`blocks[${gi}][end_time]`, entry.endTime || ''));

				const sec = {
					gi, el: secEl, defectSelect, defQtyInput, commentInput,
					scrapsWrap, scrapsEmpty, scrapsHeader, selectAll, defectHint, limitMsg,
					modeFg, modePart, modeMsg,
				};

				setDefectOptions(defectSelect, []);
				defectSelect.addEventListener('change', () => {
					updateDefectIds(sec);
					toggleComment(sec);
					defectHint.style.display = defectSelect.value ? 'none' : '';
				});
				defQtyInput.addEventListener('input', () => {
					recomputeSectionQtys(sec);
					validateBlockDefectLimit(block);
					refreshSaveState();
				});
				modeFg.addEventListener('change', () => applyScrapMode(sec));
				modePart.addEventListener('change', () => applyScrapMode(sec));
				selectAll.addEventListener('change', () => {
					const on = selectAll.checked;
					componentEnables(sec).forEach((c) => setRowEnabled(sec, c, on));
					syncSelectAll(sec);
					refreshSaveState();
				});

				block.sections.push(sec);
				sectionsWrap.appendChild(secEl);
				repopulateDefects(sec);
				rebuildScraps(sec);
				validateBlockDefectLimit(block);
				updateButtons();
				return sec;
			};

			const removeLastSection = () => {
				if (block.sections.length <= 1) return;
				const sec = block.sections.pop();
				sec.el.remove();
				validateBlockDefectLimit(block);
				refreshSaveState();
				updateButtons();
			};

			addBtn.addEventListener('click', addSection);
			removeBtn.addEventListener('click', removeLastSection);

			blocksWrap.appendChild(el);
			addSection(); // every block starts with one defect section
			return block;
		}

		// ----------------------------------------------------------- single part
		// One block per line for not-yet-assembled parts scrapped on that line
		// (no product → recorded server-side as NG mode "Other" / "Single part").
		function buildSinglePartBlock(lineCode, lineEntry = {}) {
			const scraps = singlePartScraps(lineCode);
			if (!scraps.length) return null;

			const el = singleBlockTpl.content.firstElementChild.cloneNode(true);
			el.querySelector('[data-line-display]').textContent = lineCode || '';
			const toggle = el.querySelector('[data-single-toggle]');
			const body = el.querySelector('[data-single-body]');
			const selectAll = el.querySelector('[data-select-all]');
			const scrapsWrap = el.querySelector('[data-scraps]');
			const scrapsEmpty = el.querySelector('[data-scraps-empty]');
			const commentInput = el.querySelector('[data-single-comment]');

			const gi = nextGi++;
			// Block-level hidden fields read by RecordDefectsView.post.
			el.appendChild(mkHidden(`blocks[${gi}][production_line]`, lineCode || ''));
			el.appendChild(mkHidden(`blocks[${gi}][single_part]`, '1'));
			el.appendChild(mkHidden(`blocks[${gi}][start_time]`, lineEntry.startTime || ''));
			el.appendChild(mkHidden(`blocks[${gi}][end_time]`, lineEntry.endTime || ''));
			// Operator-entered reason → ProcessDefect.comment (server falls back
			// to "Single part" when left blank). Attached to row 0 so the existing
			// per-row comment parser picks it up.
			if (commentInput) commentInput.name = `blocks[${gi}][rows][0][comment]`;

			const rowEnables = () => Array.from(scrapsWrap.querySelectorAll('[data-enable]'));
			const syncSelectAll = () => {
				const boxes = rowEnables();
				if (!boxes.length) { selectAll.checked = false; selectAll.indeterminate = false; return; }
				const n = boxes.filter((b) => b.checked).length;
				selectAll.checked = n === boxes.length;
				selectAll.indeterminate = n > 0 && n < boxes.length;
			};

			scraps.forEach((s, ri) => {
				const row = scrapTpl.content.firstElementChild.cloneNode(true);
				const enable = row.querySelector('[data-enable]');
				enable.name = `blocks[${gi}][rows][${ri}][enabled]`;

				const photo = row.querySelector('[data-photo]');
				const photoImg = row.querySelector('[data-photo-img]');
				if (s.image_url) {
					photo.href = s.image_url;
					photoImg.src = s.image_url;
					photo.addEventListener('click', (e) => { e.preventDefault(); openImageModal(s.image_url); });
				} else {
					photoImg.removeAttribute('src');
					photo.removeAttribute('href');
				}

				const nameInput = row.querySelector('[data-name]');
				// Show "SD — Part No." (no part_name); fall back to name if both blank.
				nameInput.value = [s.sd_code, s.part_number].filter(Boolean).join(' — ') || s.name || '';

				const cpid = row.querySelector('[data-cpid]');
				cpid.name = `blocks[${gi}][rows][${ri}][component_part_id]`;
				cpid.value = s.id || '';
				const defid = row.querySelector('[data-defid]');
				defid.name = `blocks[${gi}][rows][${ri}][defect_id]`;
				defid.value = '__other__';
				const cpname = row.querySelector('[data-cpname]');
				cpname.name = `blocks[${gi}][rows][${ri}][component_part_name]`;
				cpname.value = s.name || '';

				const qty = row.querySelector('[data-qty]');
				qty.name = `blocks[${gi}][rows][${ri}][quantity]`;

				// Checkbox ↔ qty stay in sync: ticking seeds qty 1, untick zeroes it;
				// typing a qty ticks the box, clearing to 0 unticks it.
				enable.addEventListener('change', () => {
					if (enable.checked) { if (toInt(qty.value) < 1) qty.value = '1'; }
					else qty.value = '0';
					syncSelectAll();
				});
				qty.addEventListener('input', () => { enable.checked = toInt(qty.value) >= 1; syncSelectAll(); });

				scrapsWrap.appendChild(row);
			});

			scrapsEmpty.classList.toggle('hidden', scraps.length > 0);

			selectAll.addEventListener('change', () => {
				const on = selectAll.checked;
				rowEnables().forEach((en) => {
					en.checked = on;
					const qty = en.closest('.scrap-row')?.querySelector('[data-qty]');
					if (qty) qty.value = on ? (toInt(qty.value) < 1 ? '1' : qty.value) : '0';
				});
				syncSelectAll();
			});

			// The "NG mode Other" checkbox reveals the part list. Collapsing it
			// clears any entered rows so a hidden block never submits stale data.
			toggle.addEventListener('change', () => {
				body.classList.toggle('hidden', !toggle.checked);
				if (commentInput) commentInput.classList.toggle('hidden', !toggle.checked);
				if (!toggle.checked) {
					rowEnables().forEach((en) => {
						en.checked = false;
						const qty = en.closest('.scrap-row')?.querySelector('[data-qty]');
						if (qty) qty.value = '0';
					});
					if (commentInput) commentInput.value = '';
					syncSelectAll();
				}
			});

			singleBlocksWrap.appendChild(el);
			return el;
		}

		// ----------------------------------------------------------- summary
		// The read-only Step 1 list (incl. start/end time display) was removed;
		// the same data appears in the blocks below. start/end times stay in the
		// `entries` array and are submitted via hidden inputs. Here we only reveal
		// the "← แก้ไข Step 1" shortcut.
		function renderSummary(/* entries */) {
			summaryWrap?.classList.remove('hidden');
		}

		// ----------------------------------------------------------- bootstrap
		let entries = [];
		let draftShift = '';
		let draftDate = '';
		try {
			const raw = sessionStorage.getItem(STORAGE_KEY);
			if (raw) {
				const draft = JSON.parse(raw);
				if (draft && draft.version === DRAFT_VERSION && Array.isArray(draft.entries)) {
					entries = draft.entries;
					draftShift = draft.shift || '';
					draftDate = draft.date || '';
				}
			}
		} catch {}

		if (!entries.length) {
			// No draft → show empty state, hide form.
			emptyState?.classList.remove('hidden');
			recordForm?.classList.add('hidden');
			summaryWrap?.classList.add('hidden');
			return;
		}

		renderSummary(entries);
		// Shift + working day (production_date) apply to the whole submission
		// (both chosen on Page 1) — single form-level hidden fields;
		// RecordDefectsView.post applies them to every ProductionRecord it creates.
		if (draftShift && recordForm) recordForm.appendChild(mkHidden('shift', draftShift));
		if (draftDate && recordForm) recordForm.appendChild(mkHidden('production_date', draftDate));
		entries.forEach((e) => productBlocks.push(buildBlock(e)));
		refreshSaveState();

		// One "single part" block per distinct line in the draft (order preserved).
		const seenLines = new Set();
		entries.forEach((e) => {
			if (!e.lineCode || seenLines.has(e.lineCode)) return;
			seenLines.add(e.lineCode);
			buildSinglePartBlock(e.lineCode, e);
		});

		// Clear draft after a successful submit so coming back doesn't re-populate stale data.
		recordForm.addEventListener('submit', (e) => {
			if (!validateAllDefectTotals({ report: true }) || !validateAllSectionModes({ report: true })) {
				e.preventDefault();
				refreshSaveState();
				return;
			}
			try { sessionStorage.removeItem(STORAGE_KEY); } catch {}
			saveBtn.disabled = true;
		});

		// Leaving the record flow (any link that isn't Step 1 / Step 2) drops the
		// draft, so unfinished data doesn't linger and reappear later.
		document.addEventListener('click', (e) => {
			const a = e.target.closest && e.target.closest('a[href]');
			if (!a) return;
			let url;
			try { url = new URL(a.href, window.location.origin); } catch { return; }
			if (url.origin !== window.location.origin) return; // external link
			const path = url.pathname.replace(/\/+$/, '');
			const inFlow = path === '/record' || path === '/record/defects';
			if (!inFlow) {
				try { sessionStorage.removeItem(STORAGE_KEY); } catch {}
			}
		}, true);
	};

	if (document.readyState === 'loading') {
		document.addEventListener('DOMContentLoaded', init);
	} else {
		init();
	}
})();

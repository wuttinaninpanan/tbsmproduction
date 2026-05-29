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
	const DRAFT_VERSION = 1;

	const init = () => {
		const dataEl = document.getElementById('record-data');
		const recordData = dataEl ? JSON.parse(dataEl.textContent) : { productionLines: [] };
		const lines = recordData.productionLines || [];

		const blocksWrap = document.getElementById('blocks');
		const blockTpl = document.getElementById('block-template');
		const sectionTpl = document.getElementById('defect-section-template');
		const scrapTpl = document.getElementById('scrap-row-template');
		const summaryWrap = document.getElementById('summary');
		const summaryList = summaryWrap?.querySelector('[data-summary-list]');
		const summaryRowTpl = document.getElementById('summary-row-template');
		const emptyState = document.getElementById('empty-state');
		const recordForm = document.getElementById('record-form');
		const saveBtn = document.getElementById('save');

		let nextGi = 1; // global field-name index across all blocks

		const toInt = (v) => { const n = parseInt(String(v ?? '').replace(/[^0-9]/g, ''), 10); return Number.isFinite(n) ? n : 0; };
		const fmtQty = (n) => String(Math.round(n));

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
		const defectById = (lineId, partId, did) => defectsFor(lineId, partId).find((d) => d.id === did) || null;

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
				bom_qty: 1,
			};
			return [fg, ...components];
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
			const partLabel = [entry.sdNumber, entry.partNumber, entry.partName].filter(Boolean).join(' — ');
			partDisplay.value = partLabel || entry.partId;
			prodQtyDisplay.value = String(entry.prodQty || 0);

			const block = { el, entry, sections: [] };

			// "เลือกทั้งหมด" covers components only — FG is exclusive of them.
			const fgEnable = (sec) => sec.scrapsWrap.querySelector('[data-enable][data-fg]');
			const componentEnables = (sec) => Array.from(sec.scrapsWrap.querySelectorAll('[data-enable]:not([data-fg])'));
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
					photoImg.removeAttribute('src');
					photo.removeAttribute('href');
				}

				const nameInput = row.querySelector('[data-name]');
				let disp = [scrap?.sd_code, scrap?.name].filter(Boolean).join(' — ') || (scrap?.name || '');
				if (scrap?.is_fg) {
					disp = `FG · ${disp}`.trim();
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
				const commentInput = secEl.querySelector('[data-comment]');
				commentInput.name = `blocks[${gi}][rows][0][comment]`;
				const scrapsWrap = secEl.querySelector('[data-scraps]');
				const scrapsEmpty = secEl.querySelector('[data-scraps-empty]');
				const selectAll = secEl.querySelector('[data-select-all]');
				const defectHint = secEl.querySelector('[data-defect-hint]');

				// Per-block hidden fields — read by RecordDefectsView.post.
				secEl.appendChild(mkHidden(`blocks[${gi}][production_line]`, entry.lineCode || ''));
				secEl.appendChild(mkHidden(`blocks[${gi}][part_number]`, entry.partId || ''));
				secEl.appendChild(mkHidden(`blocks[${gi}][production_quantity]`, String(entry.prodQty || 0)));
				secEl.appendChild(mkHidden(`blocks[${gi}][start_time]`, entry.startTime || ''));
				secEl.appendChild(mkHidden(`blocks[${gi}][end_time]`, entry.endTime || ''));

				const sec = {
					gi, el: secEl, defectSelect, defQtyInput, commentInput,
					scrapsWrap, scrapsEmpty, selectAll, defectHint,
				};

				setDefectOptions(defectSelect, []);
				defectSelect.addEventListener('change', () => {
					updateDefectIds(sec);
					toggleComment(sec);
					defectHint.style.display = defectSelect.value ? 'none' : '';
				});
				defQtyInput.addEventListener('input', () => recomputeSectionQtys(sec));
				selectAll.addEventListener('change', () => {
					const on = selectAll.checked;
					const fg = fgEnable(sec);
					if (fg) setRowEnabled(sec, fg, false);
					componentEnables(sec).forEach((c) => setRowEnabled(sec, c, on));
					syncSelectAll(sec);
				});

				block.sections.push(sec);
				sectionsWrap.appendChild(secEl);
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

			addBtn.addEventListener('click', addSection);
			removeBtn.addEventListener('click', removeLastSection);

			blocksWrap.appendChild(el);
			addSection(); // every block starts with one defect section
			return block;
		}

		// ----------------------------------------------------------- summary
		function renderSummary(entries) {
			if (!summaryList || !summaryRowTpl) return;
			summaryList.innerHTML = '';
			entries.forEach((e) => {
				const row = summaryRowTpl.content.firstElementChild.cloneNode(true);
				const part = getPart(e.lineCode, e.partId);
				const img = row.querySelector('[data-img]');
				if (part?.image_url) img.src = part.image_url; else img.removeAttribute('src');
				row.querySelector('[data-name]').textContent = e.partName || (part?.part_name || part?.part_number || '');
				row.querySelector('[data-meta]').textContent = [e.lineCode, e.sdNumber, e.partNumber].filter(Boolean).join(' · ');
				row.querySelector('[data-qty]').textContent = String(e.prodQty || 0);
				const timeBits = [];
				if (e.startTime) timeBits.push(`เริ่ม: ${e.startTime.replace('T', ' ')}`);
				if (e.endTime) timeBits.push(`จบ: ${e.endTime.replace('T', ' ')}`);
				row.querySelector('[data-time]').textContent = timeBits.join('  •  ') || '—';
				summaryList.appendChild(row);
			});
			summaryWrap.classList.remove('hidden');
		}

		// ----------------------------------------------------------- bootstrap
		let entries = [];
		try {
			const raw = sessionStorage.getItem(STORAGE_KEY);
			if (raw) {
				const draft = JSON.parse(raw);
				if (draft && draft.version === DRAFT_VERSION && Array.isArray(draft.entries)) {
					entries = draft.entries;
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
		entries.forEach((e) => buildBlock(e));

		// Clear draft after a successful submit so coming back doesn't re-populate stale data.
		recordForm.addEventListener('submit', () => {
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

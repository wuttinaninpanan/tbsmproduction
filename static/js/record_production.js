/**
 * Record — Page 1 (production qty + time window per part).
 *
 * Lets the operator add one or more "line sections". Each section has a
 * custom JS autocomplete (typeahead) for the line, and once a line is
 * picked, every Part configured on that line is rendered as one input row
 * (qty + start_time + end_time).
 *
 * On "ถัดไป" we serialize all non-empty entries into ``sessionStorage``
 * under ``tbsm:record:draft`` and navigate to Page 2 ("/record/defects/").
 * Page 2 reads that draft to pre-fill its defect blocks.
 *
 * Draft shape:
 *   {
 *     version: 1,
 *     savedAt: <ISO>,
 *     entries: [
 *       { lineCode, partId, sdNumber, partNumber, partName,
 *         prodQty, startTime, endTime }
 *     ]
 *   }
 */
(() => {
	const STORAGE_KEY = 'tbsm:record:draft';
	const DRAFT_VERSION = 1;

	const init = () => {
		const dataEl = document.getElementById('record-data');
		const recordData = dataEl ? JSON.parse(dataEl.textContent) : { productionLines: [] };
		const lines = recordData.productionLines || [];

		const linesWrap = document.getElementById('lines-wrap');
		const addLineBtn = document.getElementById('add-line');
		const clearBtn = document.getElementById('clear');
		const nextBtn = document.getElementById('next');
		const lineTpl = document.getElementById('line-template');
		const partRowTpl = document.getElementById('part-row-template');

		// ----------------------------------------------------------- helpers
		const getLine = (lineCode) => lines.find((l) => l.id === lineCode) || null;
		const sections = []; // [{ el, lineInput, lineCode, partsWrap, partRows: [{ partId, ... }] }]

		// Custom autocomplete: type to filter, click/Enter to pick.
		// We deliberately don't use <datalist> — the user asked for a richer
		// dropdown (clearer styling, keyboard nav, no native chrome).
		function attachAutocomplete(wrap, input, menu, getOptions, onPick) {
			let activeIdx = -1;
			let opts = [];

			const render = (query = '') => {
				const q = query.trim().toLowerCase();
				opts = getOptions().filter((o) => !q || o.label.toLowerCase().includes(q));
				menu.innerHTML = '';
				if (!opts.length) {
					const div = document.createElement('div');
					div.className = 'ac-empty';
					div.textContent = 'ไม่พบรายการ';
					menu.appendChild(div);
					return;
				}
				opts.forEach((o, i) => {
					const div = document.createElement('div');
					div.className = 'ac-item' + (i === activeIdx ? ' active' : '');
					div.setAttribute('role', 'option');
					div.dataset.value = o.value;
					div.textContent = o.label;
					div.addEventListener('mousedown', (e) => {
						e.preventDefault(); // keep focus, prevents input blur racing
						pick(i);
					});
					menu.appendChild(div);
				});
			};

			const open = () => { menu.classList.add('open'); render(input.value); };
			const close = () => { menu.classList.remove('open'); activeIdx = -1; };
			const setActive = (i) => {
				activeIdx = Math.max(0, Math.min(i, opts.length - 1));
				render(input.value);
				const el = menu.children[activeIdx];
				if (el && el.scrollIntoView) el.scrollIntoView({ block: 'nearest' });
			};
			const pick = (i) => {
				const o = opts[i];
				if (!o) return;
				input.value = o.label;
				close();
				onPick(o.value, o.label);
			};

			input.addEventListener('focus', open);
			input.addEventListener('input', () => { activeIdx = -1; open(); onPick('', input.value); });
			input.addEventListener('keydown', (e) => {
				if (e.key === 'ArrowDown') { e.preventDefault(); if (!menu.classList.contains('open')) open(); setActive(activeIdx + 1); }
				else if (e.key === 'ArrowUp') { e.preventDefault(); setActive(activeIdx - 1); }
				else if (e.key === 'Enter') { if (activeIdx >= 0) { e.preventDefault(); pick(activeIdx); } }
				else if (e.key === 'Escape') { close(); }
			});
			input.addEventListener('blur', () => setTimeout(close, 120));

			wrap.querySelector('[data-ac-chevron]')?.addEventListener('click', (e) => {
				e.preventDefault();
				if (menu.classList.contains('open')) { close(); }
				else { input.focus(); open(); }
			});
		}

		// ----------------------------------------------------------- line section
		function buildLineSection(prefill = null) {
			const el = lineTpl.content.firstElementChild.cloneNode(true);
			const lineInput = el.querySelector('[data-line]');
			const menu = el.querySelector('[data-ac-menu]');
			const acWrap = el.querySelector('[data-ac]');
			const partsWrap = el.querySelector('[data-parts-wrap]');
			const partsList = el.querySelector('[data-parts]');
			const partsEmpty = el.querySelector('[data-parts-empty]');
			const removeBtn = el.querySelector('[data-remove-line]');

			const sec = { el, lineInput, lineCode: '', partsWrap, partsList, partRows: [] };

			const renderParts = () => {
				partsList.innerHTML = '';
				sec.partRows = [];
				const line = getLine(sec.lineCode);
				if (!line) {
					partsWrap.classList.add('hidden');
					return;
				}
				partsWrap.classList.remove('hidden');
				const parts = line.parts || [];
				partsEmpty.classList.toggle('hidden', parts.length > 0);
				parts.forEach((p) => {
					const row = partRowTpl.content.firstElementChild.cloneNode(true);
					const img = row.querySelector('[data-part-img]');
					if (p.image_url) img.src = p.image_url;
					else img.removeAttribute('src');
					row.querySelector('[data-part-name]').textContent = p.part_name || p.part_number || p.sd_number || '(ไม่มีชื่อ)';
					row.querySelector('[data-part-meta]').textContent = [p.sd_number, p.part_number].filter(Boolean).join(' · ');
					const prodQty = row.querySelector('[data-prodqty]');
					const startEl = row.querySelector('[data-start]');
					const endEl = row.querySelector('[data-end]');
					partsList.appendChild(row);
					sec.partRows.push({ part: p, prodQty, startEl, endEl });
				});
				updateNextEnabled();
			};

			attachAutocomplete(
				acWrap, lineInput, menu,
				() => lines.map((l) => ({ value: l.id, label: l.id })),
				(value, _label) => {
					// value='' means the user is still typing — only treat an exact match as picked.
					const exact = value || (lines.find((l) => l.id.toLowerCase() === (lineInput.value || '').trim().toLowerCase())?.id || '');
					sec.lineCode = exact;
					renderParts();
				},
			);

			removeBtn.addEventListener('click', () => {
				if (sections.length <= 1) {
					// Keep at least one section — just clear it instead.
					sec.lineCode = '';
					lineInput.value = '';
					partsWrap.classList.add('hidden');
					partsList.innerHTML = '';
					sec.partRows = [];
					updateNextEnabled();
					return;
				}
				const idx = sections.indexOf(sec);
				if (idx >= 0) sections.splice(idx, 1);
				el.remove();
				updateNextEnabled();
			});

			// Re-evaluate "Next" button whenever any qty changes.
			el.addEventListener('input', updateNextEnabled);

			linesWrap.appendChild(el);
			sections.push(sec);

			if (prefill?.lineCode) {
				lineInput.value = prefill.lineCode;
				sec.lineCode = prefill.lineCode;
				renderParts();
				// pre-fill matching part qty/time
				(prefill.entries || []).forEach((e) => {
					const r = sec.partRows.find((row) => row.part.id === e.partId);
					if (!r) return;
					if (e.prodQty) r.prodQty.value = e.prodQty;
					if (e.startTime) r.startEl.value = e.startTime;
					if (e.endTime) r.endEl.value = e.endTime;
				});
			}
			updateNextEnabled();
			return sec;
		}

		// ----------------------------------------------------------- gather & next
		const toInt = (v) => { const n = parseInt(String(v ?? '').replace(/[^0-9]/g, ''), 10); return Number.isFinite(n) ? n : 0; };

		// Collect every part row that has prodQty ≥ 1 across all line sections.
		function collectEntries() {
			const out = [];
			for (const sec of sections) {
				if (!sec.lineCode) continue;
				for (const r of sec.partRows) {
					const qty = toInt(r.prodQty.value);
					if (qty < 1) continue;
					out.push({
						lineCode: sec.lineCode,
						partId: r.part.id,
						sdNumber: r.part.sd_number || '',
						partNumber: r.part.part_number || '',
						partName: r.part.part_name || '',
						prodQty: qty,
						startTime: (r.startEl.value || '').trim(),
						endTime: (r.endEl.value || '').trim(),
					});
				}
			}
			return out;
		}

		function updateNextEnabled() {
			nextBtn.disabled = collectEntries().length === 0;
		}

		nextBtn.addEventListener('click', () => {
			const entries = collectEntries();
			if (!entries.length) return;
			const draft = { version: DRAFT_VERSION, savedAt: new Date().toISOString(), entries };
			try {
				sessionStorage.setItem(STORAGE_KEY, JSON.stringify(draft));
			} catch (e) {
				alert('ไม่สามารถบันทึก draft ลง sessionStorage ได้');
				console.error(e);
				return;
			}
			window.location.assign('/record/defects/');
		});

		clearBtn.addEventListener('click', () => {
			try { sessionStorage.removeItem(STORAGE_KEY); } catch {}
			linesWrap.innerHTML = '';
			sections.length = 0;
			buildLineSection();
		});

		addLineBtn.addEventListener('click', () => buildLineSection());

		// ----------------------------------------------------------- bootstrap
		// Restore draft on load — group entries by lineCode and re-create one
		// section per line.
		let restored = false;
		try {
			const raw = sessionStorage.getItem(STORAGE_KEY);
			if (raw) {
				const draft = JSON.parse(raw);
				if (draft && draft.version === DRAFT_VERSION && Array.isArray(draft.entries) && draft.entries.length) {
					const byLine = new Map();
					draft.entries.forEach((e) => {
						if (!byLine.has(e.lineCode)) byLine.set(e.lineCode, []);
						byLine.get(e.lineCode).push(e);
					});
					for (const [lineCode, entries] of byLine.entries()) {
						buildLineSection({ lineCode, entries });
					}
					restored = true;
				}
			}
		} catch {}
		if (!restored) buildLineSection();
	};

	if (document.readyState === 'loading') {
		document.addEventListener('DOMContentLoaded', init);
	} else {
		init();
	}
})();

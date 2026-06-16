/**
 * Record — Page 1 (production qty per part + time window per line).
 *
 * Lets the operator add one or more "line sections". Each section has a
 * custom JS autocomplete (typeahead) for the line, and once a line is
 * picked, the operator keys one start/end window for that line, then every
 * Part configured on that line is rendered as one quantity input row.
 *
 * On "ถัดไป" we serialize all non-empty entries into ``sessionStorage``
 * under ``tbsm:record:draft`` and navigate to Page 2 ("/record/defects/").
 * Page 2 reads that draft to pre-fill its defect blocks.
 *
 * Draft shape:
 *   {
 *     version: 2,
 *     savedAt: <ISO>,
 *     entries: [
 *       { lineCode, partId, sdNumber, partNumber, partName,
 *         prodQty, startTime, endTime }
 *     ]
 *   }
 */
(() => {
	const STORAGE_KEY = 'tbsm:record:draft';
	const DRAFT_VERSION = 2;

	const init = () => {
		const dataEl = document.getElementById('record-data');
		const recordData = dataEl ? JSON.parse(dataEl.textContent) : { productionLines: [] };
		const lines = recordData.productionLines || [];

		const linesWrap = document.getElementById('lines-wrap');
		const dateInput = document.getElementById('record-date');
		const shiftWrap = document.getElementById('shift-wrap');
		const addLineBtn = document.getElementById('add-line');
		const clearBtn = document.getElementById('clear');
		const nextBtn = document.getElementById('next');
		const lineTpl = document.getElementById('line-template');
		const partRowTpl = document.getElementById('part-row-template');

		// ----------------------------------------------------------- helpers
		const getLine = (lineCode) => lines.find((l) => l.id === lineCode) || null;
		const sections = []; // [{ el, lineInput, lineCode, start/end fields, partRows: [{ partId, prodQty }] }]

		// Date is keyed once (top of form); each line section keys the time.
		// We combine them back into the ``YYYY-MM-DDTHH:MM`` shape Page 2 / the
		// backend already expect, so nothing downstream needs to change.
		const todayISO = () => {
			const d = new Date();
			const off = d.getTimezoneOffset();
			return new Date(d.getTime() - off * 60000).toISOString().slice(0, 10);
		};
		// Free-typed time → canonical 24h "HH:MM" (or '' if not a valid time).
		// Accepts "0810", "810", "8:10", "08.10", "08 10" etc.
		const normalizeTime = (raw) => {
			const s = String(raw ?? '').trim();
			if (!s) return '';
			const m = s.match(/^(\d{1,2})\s*[:.\s]\s*(\d{1,2})$/) // H:MM / H.MM / H MM
				|| (/^\d{3,4}$/.test(s) ? [null, s.slice(0, s.length - 2), s.slice(-2)] : null)
				|| (/^\d{1,2}$/.test(s) ? [null, s, '0'] : null);
			if (!m) return '';
			const h = parseInt(m[1], 10);
			const mi = parseInt(m[2], 10);
			if (!Number.isFinite(h) || !Number.isFinite(mi) || h > 23 || mi > 59) return '';
			return `${String(h).padStart(2, '0')}:${String(mi).padStart(2, '0')}`;
		};
		const combineDateTime = (date, time) => {
			const t = normalizeTime(time);
			return (date && t ? `${date}T${t}` : '');
		};
		const combineWorkDateTime = (baseDate, time) => combineDateTime(baseDate, time);
		// Open the native time/date picker the moment the field is clicked or
		// focused — so a single tap shows the number selector instead of making
		// the user hunt for the little clock icon. (No-op on browsers without
		// showPicker; guarded because it throws without a user gesture.)
		const openPickerOnInteract = (el) => {
			if (!el || typeof el.showPicker !== 'function') return;
			const show = () => { try { el.showPicker(); } catch {} };
			el.addEventListener('focus', show);
			el.addEventListener('click', show);
		};
		// Pull the time half out of a full datetime (or pass a bare time through).
		const timePart = (dt) => (dt && dt.includes('T') ? dt.split('T')[1] : (dt || ''));
		const datePart = (dt) => (dt && dt.includes('T') ? dt.split('T')[0] : '');
		if (dateInput && !dateInput.value) dateInput.value = todayISO();
		openPickerOnInteract(dateInput);

		dateInput?.addEventListener('change', () => {
			saveDraft();
		});

		// ----------------------------------------------------------- shift
		// One shift applies to the whole record. Rendered as checkboxes (per the
		// UI request) but enforced single-select here: ticking one unticks the
		// others. The form-level 'change' listener re-saves the draft afterwards.
		const shiftBoxes = () => (shiftWrap ? Array.from(shiftWrap.querySelectorAll('[data-shift]')) : []);
		// Server-provided default = the logged-in user's profile shift (may be '').
		const defaultShift = shiftWrap?.dataset.defaultShift || '';
		const getSelectedShift = () => (shiftBoxes().find((b) => b.checked)?.value || '');
		const setSelectedShift = (id) => { shiftBoxes().forEach((b) => { b.checked = !!id && b.value === id; }); };
		// A shift is REQUIRED before Step 2. Highlight the box red when missing;
		// clears the moment one is ticked.
		const validateShift = () => {
			const ok = !!getSelectedShift();
			if (shiftWrap) {
				shiftWrap.classList.toggle('ring-2', !ok);
				shiftWrap.classList.toggle('ring-red-500', !ok);
			}
			return ok;
		};
		shiftBoxes().forEach((box) => {
			box.addEventListener('change', () => {
				if (box.checked) shiftBoxes().forEach((b) => { if (b !== box) b.checked = false; });
				validateShift();
			});
		});

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
			const startEl = el.querySelector('[data-start]');
			const endEl = el.querySelector('[data-end]');

			const fmtTime = (input) => {
				const t = normalizeTime(input.value);
				if (t) {
					input.value = t;
					input.classList.remove('ring-2', 'ring-red-500');
				}
			};
			startEl.addEventListener('blur', () => { fmtTime(startEl); saveDraft(); });
			endEl.addEventListener('blur', () => { fmtTime(endEl); saveDraft(); });

			const sec = {
				el, lineInput, lineCode: '', partsWrap, partsList, partRows: [],
				startEl, endEl,
			};

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
					partsList.appendChild(row);
					sec.partRows.push({ part: p, prodQty });
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
					saveDraft();
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
					saveDraft();
					return;
				}
				const idx = sections.indexOf(sec);
				if (idx >= 0) sections.splice(idx, 1);
				el.remove();
				updateNextEnabled();
				saveDraft();
			});

			// Re-evaluate "Next" button whenever any qty changes.
			el.addEventListener('input', updateNextEnabled);

			linesWrap.appendChild(el);
			sections.push(sec);

			if (prefill?.lineCode) {
				lineInput.value = prefill.lineCode;
				sec.lineCode = prefill.lineCode;
				const firstTimed = (prefill.entries || []).find((e) => e.startTime || e.endTime) || {};
				if (prefill.startTime || firstTimed.startTime) {
					startEl.value = timePart(prefill.startTime || firstTimed.startTime);
				}
				if (prefill.endTime || firstTimed.endTime) {
					endEl.value = timePart(prefill.endTime || firstTimed.endTime);
				}
				renderParts();
				// pre-fill matching part quantities
				(prefill.entries || []).forEach((e) => {
					const r = sec.partRows.find((row) => row.part.id === e.partId);
					if (!r) return;
					if (e.prodQty) r.prodQty.value = e.prodQty;
				});
			}
			updateNextEnabled();
			return sec;
		}

		// ----------------------------------------------------------- gather & next
		const toInt = (v) => { const n = parseInt(String(v ?? '').replace(/[^0-9]/g, ''), 10); return Number.isFinite(n) ? n : 0; };

		// Collect every part row that has prodQty ≥ 1 across all line sections.
		function collectEntries() {
			const topDate = (dateInput?.value || '').trim();
			const out = [];
			for (const sec of sections) {
				if (!sec.lineCode) continue;
				const startTime = combineWorkDateTime(topDate, (sec.startEl.value || '').trim());
				const endTime = combineWorkDateTime(topDate, (sec.endEl.value || '').trim());
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
						startTime,
						endTime,
					});
				}
			}
			return out;
		}

		function updateNextEnabled() {
			nextBtn.disabled = collectEntries().length === 0;
		}

		// Persist the live state on every edit so a refresh reflects exactly
		// what's on screen now (e.g. a deleted line stays deleted). When there's
		// nothing to save, drop the draft entirely instead of leaving stale data.
		function saveDraft() {
			const entries = collectEntries();
			try {
				if (!entries.length) {
					sessionStorage.removeItem(STORAGE_KEY);
					return true;
				}
				const draft = { version: DRAFT_VERSION, savedAt: new Date().toISOString(), date: (dateInput?.value || '').trim(), shift: getSelectedShift(), entries };
				sessionStorage.setItem(STORAGE_KEY, JSON.stringify(draft));
				return true;
			} catch (e) {
				console.error(e);
				return false;
			}
		}

		// Every part with a produced qty MUST have both a start and end time —
		// the lot number is built from them server-side, so an empty clock would
		// yield a lot-less record. Highlight the offending fields and block.
		function validateTimes() {
			let firstBad = null;
			for (const sec of sections) {
				if (!sec.lineCode) continue;
				const hasQty = sec.partRows.some((r) => toInt(r.prodQty.value) >= 1);
				const checks = [
					[dateInput, hasQty && !(dateInput?.value || '').trim()],
					[sec.startEl, hasQty && !normalizeTime(sec.startEl.value)],
					[sec.endEl, hasQty && !normalizeTime(sec.endEl.value)],
				];
				checks.forEach(([el, bad]) => {
					el.classList.toggle('ring-2', bad);
					el.classList.toggle('ring-red-500', bad);
					if (bad && !firstBad) firstBad = el;
				});
			}
			if (firstBad) { firstBad.focus(); return false; }
			return true;
		}

		nextBtn.addEventListener('click', () => {
			if (collectEntries().length === 0) return;
			if (!validateShift()) {
				alert('กรุณาเลือกกะการทำงานก่อนไปขั้นตอนถัดไป');
				shiftWrap?.scrollIntoView({ behavior: 'smooth', block: 'center' });
				return;
			}
			if (!validateTimes()) {
				alert('ตรวจสอบเวลา: ต้องกรอกวันทำการและเวลาเริ่ม/จบให้ครบ');
				return;
			}
			if (!saveDraft()) {
				alert('ไม่สามารถบันทึก draft ลง sessionStorage ได้');
				return;
			}
			window.location.assign('/record/defects/');
		});

		clearBtn.addEventListener('click', () => {
			try { sessionStorage.removeItem(STORAGE_KEY); } catch {}
			if (dateInput) dateInput.value = todayISO();
			setSelectedShift(defaultShift);
			linesWrap.innerHTML = '';
			sections.length = 0;
			buildLineSection();
		});

		addLineBtn.addEventListener('click', () => { buildLineSection(); saveDraft(); });

		// Auto-save on any field edit (qty / time / date). Structural changes
		// (add/remove line, line pick) call saveDraft() directly.
		const productionForm = document.getElementById('production-form');
		if (productionForm) {
			productionForm.addEventListener('input', saveDraft);
			productionForm.addEventListener('change', saveDraft);
		}

		// ----------------------------------------------------------- bootstrap
		// Restore draft on load — group entries by lineCode and re-create one
		// section per line.
		let restored = false;
		try {
			const raw = sessionStorage.getItem(STORAGE_KEY);
			if (raw) {
				const draft = JSON.parse(raw);
				if (draft && draft.version === DRAFT_VERSION && Array.isArray(draft.entries) && draft.entries.length) {
					// Recover the single date from the draft (top-level, else the first entry).
					const savedDate = draft.date || datePart(draft.entries.find((e) => e.startTime || e.endTime)?.startTime || draft.entries[0].endTime || '');
					if (dateInput && savedDate) dateInput.value = savedDate;
					if (draft.shift) setSelectedShift(draft.shift);
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
		// Pre-tick the operator's profile shift when nothing came from a draft —
		// saves a click; they can still change or untick it.
		if (!getSelectedShift() && defaultShift) setSelectedShift(defaultShift);

		// The on-screen numeric keypad for the time / qty fields lives in the
		// shared numeric_keypad.js module (driven by the inputs' data-keypad attr).

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

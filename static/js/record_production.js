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
		const dateInput = document.getElementById('record-date');
		const addLineBtn = document.getElementById('add-line');
		const clearBtn = document.getElementById('clear');
		const nextBtn = document.getElementById('next');
		const lineTpl = document.getElementById('line-template');
		const partRowTpl = document.getElementById('part-row-template');

		// ----------------------------------------------------------- helpers
		const getLine = (lineCode) => lines.find((l) => l.id === lineCode) || null;
		const sections = []; // [{ el, lineInput, lineCode, partsWrap, partRows: [{ partId, ... }] }]

		// Date is keyed once (top of form); each part row only keys the time.
		// We combine them back into the ``YYYY-MM-DDTHH:MM`` shape Page 2 / the
		// backend already expect, so nothing downstream needs to change.
		const todayISO = () => {
			const d = new Date();
			const off = d.getTimezoneOffset();
			return new Date(d.getTime() - off * 60000).toISOString().slice(0, 10);
		};
		// Free-typed time → canonical 24h "HH:MM" (or '' if not a valid time).
		// Accepts "0810", "810", "8:10", "08.10", "08 10" etc. — minutes are
		// required (1–2 bare digits = whole hour, e.g. "8" → "08:00").
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
		// Shift a "YYYY-MM-DD" string by n days (local, no timezone drift).
		const addDays = (iso, n) => {
			if (!iso) return iso;
			const [y, m, d] = iso.split('-').map(Number);
			const dt = new Date(y, m - 1, d);
			dt.setDate(dt.getDate() + n);
			return `${dt.getFullYear()}-${String(dt.getMonth() + 1).padStart(2, '0')}-${String(dt.getDate()).padStart(2, '0')}`;
		};

		if (dateInput && !dateInput.value) dateInput.value = todayISO();
		openPickerOnInteract(dateInput);

		// The top "วันที่ผลิต" seeds every part row's start/end date. Picking a
		// new date copies it down to all rows (operators then bump the END date
		// to the next day for a night shift that crosses midnight).
		const syncRowDates = () => {
			const d = (dateInput?.value || '').trim();
			if (!d) return;
			sections.forEach((sec) => sec.partRows.forEach((r) => {
				if (r.startDateEl) r.startDateEl.value = d;
				if (r.endDateEl) r.endDateEl.value = d;
				r.applyDateRules?.(); // bump start/end to next day when time < 08:00
				r.refreshError?.();   // re-check end<start after the date shuffle
			}));
		};
		dateInput?.addEventListener('change', syncRowDates);

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
					const startDateEl = row.querySelector('[data-start-date]');
					const endDateEl = row.querySelector('[data-end-date]');
					const errEl = row.querySelector('[data-time-error]');
					// Seed both row dates from the top "วันที่ผลิต".
					const topDate = (dateInput?.value || '').trim();
					if (topDate) { startDateEl.value = topDate; endDateEl.value = topDate; }
					openPickerOnInteract(startDateEl);
					openPickerOnInteract(endDateEl);
					// Reformat free-typed time to canonical "HH:MM" on blur, and
					// clear the invalid-time highlight once it parses.
					const fmtTime = (el) => {
						const t = normalizeTime(el.value);
						if (t) {
							el.value = t;
							el.classList.remove('ring-2', 'ring-red-500');
						}
					};
					// Night-shift auto-date: a time before 08:00 belongs to the day
					// after the production date (the lot crossed midnight). Both the
					// start and end date are derived from the top "วันที่ผลิต": +1 day
					// when their time is < 08:00, otherwise the production date itself.
					const applyDateRules = () => {
						const base = (dateInput?.value || '').trim();
						if (!base) return;
						const toMin = (t) => { const [h, mi] = t.split(':').map(Number); return h * 60 + mi; };
						const st = normalizeTime(startEl.value);
						const et = normalizeTime(endEl.value);
						if (st) startDateEl.value = toMin(st) < 8 * 60 ? addDays(base, 1) : base;
						if (et) endDateEl.value = toMin(et) < 8 * 60 ? addDays(base, 1) : base;
					};
					// After the auto-date rule, an end that still lands before the
					// start can't be a real (cross-midnight) window — it's a typo, so
					// flag it (red border + message) and let validateTimes() block.
					const refreshError = () => {
						const st = normalizeTime(startEl.value);
						const et = normalizeTime(endEl.value);
						const sd = (startDateEl.value || '').trim();
						const ed = (endDateEl.value || '').trim();
						const bad = !!(st && et && sd && ed) && `${ed}T${et}` < `${sd}T${st}`;
						if (errEl) errEl.classList.toggle('hidden', !bad);
						// Swap the slate border for red so the color actually wins.
						endEl.classList.toggle('border-red-500', bad);
						endEl.classList.toggle('border-slate-300', !bad);
						return bad;
					};
					startEl.addEventListener('blur', () => { fmtTime(startEl); applyDateRules(); refreshError(); });
					endEl.addEventListener('blur', () => { fmtTime(endEl); applyDateRules(); refreshError(); });
					startDateEl.addEventListener('change', refreshError);
					endDateEl.addEventListener('change', refreshError);
					partsList.appendChild(row);
					sec.partRows.push({ part: p, prodQty, startEl, endEl, startDateEl, endDateEl, applyDateRules, refreshError });
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
				renderParts();
				// pre-fill matching part qty/time
				(prefill.entries || []).forEach((e) => {
					const r = sec.partRows.find((row) => row.part.id === e.partId);
					if (!r) return;
					if (e.prodQty) r.prodQty.value = e.prodQty;
					if (e.startTime) {
						r.startEl.value = timePart(e.startTime);
						const d = datePart(e.startTime); if (d) r.startDateEl.value = d;
					}
					if (e.endTime) {
						r.endEl.value = timePart(e.endTime);
						const d = datePart(e.endTime); if (d) r.endDateEl.value = d;
					}
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
				for (const r of sec.partRows) {
					const qty = toInt(r.prodQty.value);
					if (qty < 1) continue;
					// Each row carries its own start/end date (defaults to the top
					// date) so a night shift can end on the next day.
					const sd = (r.startDateEl?.value || topDate || '').trim();
					const ed = (r.endDateEl?.value || topDate || '').trim();
					out.push({
						lineCode: sec.lineCode,
						partId: r.part.id,
						sdNumber: r.part.sd_number || '',
						partNumber: r.part.part_number || '',
						partName: r.part.part_name || '',
						prodQty: qty,
						startTime: combineDateTime(sd, (r.startEl.value || '').trim()),
						endTime: combineDateTime(ed, (r.endEl.value || '').trim()),
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
				const draft = { version: DRAFT_VERSION, savedAt: new Date().toISOString(), date: (dateInput?.value || '').trim(), entries };
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
				for (const r of sec.partRows) {
					const hasQty = toInt(r.prodQty.value) >= 1;
					// Each row needs a valid date + time for both start and end
					// (missing → red ring, kept separate from the end<start border).
					const checks = [
						[r.startDateEl, hasQty && !(r.startDateEl.value || '').trim()],
						[r.startEl, hasQty && !normalizeTime(r.startEl.value)],
						[r.endDateEl, hasQty && !(r.endDateEl.value || '').trim()],
						[r.endEl, hasQty && !normalizeTime(r.endEl.value)],
					];
					checks.forEach(([el, bad]) => {
						el.classList.toggle('ring-2', bad);
						el.classList.toggle('ring-red-500', bad);
						if (bad && !firstBad) firstBad = el;
					});
					// End-before-start (same-day) → red border + message; blocks too.
					if (hasQty && r.refreshError?.() && !firstBad) firstBad = r.endEl;
				}
			}
			if (firstBad) { firstBad.focus(); return false; }
			return true;
		}

		nextBtn.addEventListener('click', () => {
			if (collectEntries().length === 0) return;
			if (!validateTimes()) {
				alert('ตรวจสอบเวลา: ต้องกรอกวันที่+เวลาเริ่ม/จบ ให้ครบ และเวลาจบต้องมาหลังเวลาเริ่ม ก่อนไปขั้นตอนถัดไป');
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

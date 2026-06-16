/**
 * Shared on-screen numeric keypad (iPad-friendly).
 *
 * Any <input> tagged with `data-keypad="int"` or `data-keypad="time"` (and
 * `inputmode="none"` so the OS keyboard stays closed) gets this keypad on
 * focus. It injects its own markup + styles, so a page only needs to include
 * this script and tag the inputs — nothing else.
 *
 * Modes:
 *   int  → plain integer (digits, up to 6). Finalizes to the trimmed number.
 *   time → 24h clock. Digits accumulate as HHMM and snap to "HH:MM".
 *
 * Optional `data-keypad-label="..."` overrides the header text.
 *
 * Finalizing dispatches `input` + `change` and blurs the field, so existing
 * per-field handlers (auto-date rules, validation, draft autosave) still run.
 */
(() => {
	if (window.__numericKeypadLoaded) return;
	window.__numericKeypadLoaded = true;

	// Free-typed time digits → canonical 24h "HH:MM" (or '' if invalid).
	const normalizeTime = (raw) => {
		const s = String(raw ?? '').trim();
		if (!s) return '';
		const m = s.match(/^(\d{1,2})\s*[:.\s]\s*(\d{1,2})$/)
			|| (/^\d{3,4}$/.test(s) ? [null, s.slice(0, s.length - 2), s.slice(-2)] : null)
			|| (/^\d{1,2}$/.test(s) ? [null, s, '0'] : null);
		if (!m) return '';
		const h = parseInt(m[1], 10);
		const mi = parseInt(m[2], 10);
		if (!Number.isFinite(h) || !Number.isFinite(mi) || h > 23 || mi > 59) return '';
		return `${String(h).padStart(2, '0')}:${String(mi).padStart(2, '0')}`;
	};

	const style = document.createElement('style');
	style.textContent = `
		#numeric-keypad{position:fixed;z-index:9998;width:16rem;display:none}
		#numeric-keypad.open{display:block}
		#numeric-keypad .nk-card{background:#fff;border:1px solid #cbd5e1;box-shadow:0 12px 32px rgba(15,23,42,.28);border-radius:.75rem;padding:.75rem}
		#numeric-keypad .nk-head{display:flex;align-items:center;justify-content:space-between;padding:0 .25rem .5rem}
		#numeric-keypad .nk-label{font-size:.85rem;font-weight:700;color:#334155}
		#numeric-keypad .nk-value{font-size:1.5rem;font-weight:800;color:#0f172a;font-variant-numeric:tabular-nums}
		#numeric-keypad .nk-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:.5rem}
		#numeric-keypad .nk-btn{padding:.9rem 0;border-radius:.6rem;font-size:1.4rem;font-weight:700;background:#f1f5f9;color:#0f172a;border:1px solid #cbd5e1;cursor:pointer;user-select:none;-webkit-user-select:none}
		#numeric-keypad .nk-btn:active{background:#e2e8f0;transform:translateY(1px)}
		#numeric-keypad .nk-fn{background:#fee2e2;color:#b91c1c;font-size:1.05rem}
		#numeric-keypad .nk-done{width:100%;margin-top:.5rem;padding:.65rem 0;border-radius:.6rem;background:#2563eb;color:#fff;font-weight:700;font-size:1rem;border:none;cursor:pointer}
		#numeric-keypad .nk-done:active{background:#1d4ed8}
	`;
	document.head.appendChild(style);

	const kp = document.createElement('div');
	kp.id = 'numeric-keypad';
	kp.innerHTML = `
		<div class="nk-card">
			<div class="nk-head"><span class="nk-label" data-nk-label>กรอกตัวเลข</span><span class="nk-value" data-nk-value>--</span></div>
			<div class="nk-grid">
				${[1, 2, 3, 4, 5, 6, 7, 8, 9].map((n) => `<button type="button" class="nk-btn" data-nk="${n}">${n}</button>`).join('')}
				<button type="button" class="nk-btn nk-fn" data-nk="clear">ล้าง</button>
				<button type="button" class="nk-btn" data-nk="0">0</button>
				<button type="button" class="nk-btn nk-fn" data-nk="back">⌫</button>
			</div>
			<button type="button" class="nk-done" data-nk="done">เสร็จ</button>
		</div>`;
	const mount = () => document.body.appendChild(kp);
	if (document.body) mount(); else document.addEventListener('DOMContentLoaded', mount);

	const labelEl = kp.querySelector('[data-nk-label]');
	const valueEl = kp.querySelector('[data-nk-value]');
	const MAXLEN = { time: 4, int: 6 };
	let active = null;
	let mode = 'int';

	const isKpInput = (el) => !!(el && el.matches && el.matches('input[data-keypad]'));
	const liveDisplay = (raw) => (mode === 'time' && raw.length === 4) ? `${raw.slice(0, 2)}:${raw.slice(2)}` : raw;
	const refreshValue = () => {
		valueEl.textContent = (active?.value || '').trim() || (mode === 'time' ? '--:--' : '--');
	};
	const position = () => {
		if (!active) return;
		const r = active.getBoundingClientRect();
		const w = kp.offsetWidth || 256;
		const h = kp.offsetHeight || 320;
		const gap = 6;
		const left = Math.max(8, Math.min(r.left, window.innerWidth - w - 8));
		let top = r.bottom + gap;
		if (top + h > window.innerHeight - 8) top = Math.max(8, r.top - gap - h);
		kp.style.left = `${left}px`;
		kp.style.top = `${top}px`;
	};
	const show = (el) => {
		active = el;
		mode = el.dataset.keypad === 'time' ? 'time' : 'int';
		kp.classList.add('open');
		labelEl.textContent = el.dataset.keypadLabel || (mode === 'time' ? 'กรอกเวลา' : 'กรอกจำนวน');
		refreshValue();
		position();
	};
	const hide = () => { kp.classList.remove('open'); active = null; };
	const finalize = () => {
		if (active) {
			const raw = (active.value || '').replace(/\D/g, '');
			if (mode === 'time') { const t = normalizeTime(raw); if (t) active.value = t; }
			else active.value = raw ? String(parseInt(raw, 10)) : '';
			active.dispatchEvent(new Event('input', { bubbles: true }));
			active.dispatchEvent(new Event('change', { bubbles: true }));
			active.blur();
		}
		hide();
	};

	// Keep focus on the field while tapping keys (so it doesn't blur and close).
	kp.addEventListener('mousedown', (e) => { if (e.target.closest('[data-nk]')) e.preventDefault(); });
	kp.addEventListener('click', (e) => {
		const btn = e.target.closest('[data-nk]');
		if (!btn || !active) return;
		const key = btn.dataset.nk;
		if (key === 'done') { finalize(); return; }
		let raw = (active.value || '').replace(/\D/g, '');
		if (key === 'back') raw = raw.slice(0, -1);
		else if (key === 'clear') raw = '';
		else if (/^\d$/.test(key) && raw.length < MAXLEN[mode]) raw += key;
		active.value = liveDisplay(raw);
		active.dispatchEvent(new Event('input', { bubbles: true }));
		refreshValue();
	});

	document.addEventListener('focusin', (e) => { if (isKpInput(e.target)) show(e.target); });
	document.addEventListener('pointerdown', (e) => {
		if (!kp.classList.contains('open')) return;
		if (e.target.closest('#numeric-keypad') || isKpInput(e.target)) return;
		finalize();
	});
	window.addEventListener('resize', position);
	window.addEventListener('scroll', position, true);
})();

path = '/app/templates/inspection/inspection_modelss.html'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. ห่อ Count Detect block ใน Add modal ด้วย div + id
old_add_count = """\t\t\t<div>
\t\t\t\t<label class="block text-sm font-semibold text-slate-700">Count Detect</label>
\t\t\t\t<input name="count_detect" type="number" value="0" class="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500" />
\t\t\t</div>
\t\t</div>
\t\t<div class="mt-5 flex items-center justify-end gap-2">
\t\t\t<button type="button" class="px-4 py-2 rounded-lg font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200" data-modal-close>ยกเลิก</button>
\t\t\t<button type="submit" class="px-4 py-2 rounded-lg font-semibold text-white bg-emerald-600 hover:bg-emerald-700">บันทึก</button>
\t\t</div>
\t</form>
</div>

<!-- Edit Modal -->"""

new_add_count = """\t\t\t<div id="addCountDetectBlock">
\t\t\t\t<label class="block text-sm font-semibold text-slate-700">Count Detect</label>
\t\t\t\t<input name="count_detect" type="number" value="0" class="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500" />
\t\t\t</div>
\t\t</div>
\t\t<div class="mt-5 flex items-center justify-end gap-2">
\t\t\t<button type="button" class="px-4 py-2 rounded-lg font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200" data-modal-close>ยกเลิก</button>
\t\t\t<button type="submit" class="px-4 py-2 rounded-lg font-semibold text-white bg-emerald-600 hover:bg-emerald-700">บันทึก</button>
\t\t</div>
\t</form>
</div>

<!-- Edit Modal -->"""

if old_add_count in content:
    content = content.replace(old_add_count, new_add_count)
    print("Add modal Count Detect wrapped")
else:
    print("WARNING: Add modal count detect block not found")

# 2. ห่อ Count Detect block ใน Edit modal ด้วย div + id
old_edit_count = """\t\t\t<div>
\t\t\t\t<label class="block text-sm font-semibold text-slate-700">Count Detect</label>
\t\t\t\t<input name="count_detect" id="editCountDetect" type="number" class="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500" />
\t\t\t</div>
\t\t</div>
\t\t<div class="mt-5 flex items-center justify-end gap-2">
\t\t\t<button type="button" class="px-4 py-2 rounded-lg font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200" data-modal-close>ยกเลิก</button>
\t\t\t<button type="submit" class="px-4 py-2 rounded-lg font-semibold text-white bg-emerald-600 hover:bg-emerald-700">บันทึก</button>
\t\t</div>
\t</form>
</div>

<!-- Delete Modal -->"""

new_edit_count = """\t\t\t<div id="editCountDetectBlock">
\t\t\t\t<label class="block text-sm font-semibold text-slate-700">Count Detect</label>
\t\t\t\t<input name="count_detect" id="editCountDetect" type="number" class="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500" />
\t\t\t</div>
\t\t</div>
\t\t<div class="mt-5 flex items-center justify-end gap-2">
\t\t\t<button type="button" class="px-4 py-2 rounded-lg font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200" data-modal-close>ยกเลิก</button>
\t\t\t<button type="submit" class="px-4 py-2 rounded-lg font-semibold text-white bg-emerald-600 hover:bg-emerald-700">บันทึก</button>
\t\t</div>
\t</form>
</div>

<!-- Delete Modal -->"""

if old_edit_count in content:
    content = content.replace(old_edit_count, new_edit_count)
    print("Edit modal Count Detect wrapped")
else:
    print("WARNING: Edit modal count detect block not found")

# 3. เพิ่ม JS สำหรับ show/hide ก่อน })(); ปิด script
old_js_end = """\tdocument.querySelectorAll('[data-open-delete]').forEach(btn => {
\t\tbtn.addEventListener('click', () => {
\t\t\tdocument.getElementById('deleteId').value = btn.dataset.id || '';
\t\t\tdocument.getElementById('deleteLabel').textContent = btn.dataset.label || '';
\t\t\topenModal(deleteModal);
\t\t});
\t});
})();"""

new_js_end = """\tdocument.querySelectorAll('[data-open-delete]').forEach(btn => {
\t\tbtn.addEventListener('click', () => {
\t\t\tdocument.getElementById('deleteId').value = btn.dataset.id || '';
\t\t\tdocument.getElementById('deleteLabel').textContent = btn.dataset.label || '';
\t\t\topenModal(deleteModal);
\t\t});
\t});

\t// แสดง/ซ่อน Count Detect ตาม model type
\tfunction toggleCountDetect(prefix, type) {
\t\tconst block = document.getElementById(prefix + 'CountDetectBlock');
\t\tif (!block) return;
\t\tif (type === 'DEFECT') {
\t\t\tblock.style.display = 'none';
\t\t\tconst input = block.querySelector('input');
\t\t\tif (input) input.value = '0';
\t\t} else {
\t\t\tblock.style.display = '';
\t\t}
\t}

\t// Add modal radios
\tdocument.querySelectorAll('#addModal input[name="model_type"]').forEach(radio => {
\t\tradio.addEventListener('change', () => toggleCountDetect('add', radio.value));
\t});
\ttoggleCountDetect('add', 'OBJECT');

\t// Edit modal radios
\tdocument.querySelectorAll('#editModal input[name="model_type"]').forEach(radio => {
\t\tradio.addEventListener('change', () => toggleCountDetect('edit', radio.value));
\t});
})();"""

if old_js_end in content:
    content = content.replace(old_js_end, new_js_end)
    print("JS toggle added")
else:
    print("WARNING: JS end block not found")

# 4. แก้ openModal ใน edit ให้ trigger toggle หลังจาก set radio
old_open_edit = """\t\t\tconst mt = btn.dataset.modelType || 'OBJECT';
\t\t\tdocument.getElementById('editTypeObject').checked = (mt === 'OBJECT');
\t\t\tdocument.getElementById('editTypeDefect').checked = (mt === 'DEFECT');
\t\t\topenModal(editModal);"""

new_open_edit = """\t\t\tconst mt = btn.dataset.modelType || 'OBJECT';
\t\t\tdocument.getElementById('editTypeObject').checked = (mt === 'OBJECT');
\t\t\tdocument.getElementById('editTypeDefect').checked = (mt === 'DEFECT');
\t\t\ttoggleCountDetect('edit', mt);
\t\t\topenModal(editModal);"""

if old_open_edit in content:
    content = content.replace(old_open_edit, new_open_edit)
    print("Edit modal toggle on open added")
else:
    print("WARNING: Edit modal open block not found")

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Done")

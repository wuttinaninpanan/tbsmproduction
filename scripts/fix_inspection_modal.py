path = '/app/templates/inspection/inspection_modelss.html'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

cut_start = content.find('\n<!-- Add Modal -->')
if cut_start == -1:
    print("ERROR: cut point not found")
    exit(1)

base = content[:cut_start]

new_modals = """
<!-- Add Modal -->
<div id="addModal" class="fixed inset-0 z-[9999] hidden items-center justify-center p-4 sm:p-6">
\t<div class="absolute inset-0 bg-slate-900/70 backdrop-blur-sm" data-modal-backdrop></div>
\t<form method="post" enctype="multipart/form-data" class="relative w-full max-w-lg rounded-2xl shadow-2xl bg-white p-6 max-h-[90vh] overflow-y-auto">
\t\t{% csrf_token %}
\t\t<input type="hidden" name="action" value="create">
\t\t<button type="button" class="absolute right-3 top-3 h-9 w-9 inline-flex items-center justify-center rounded-full bg-white/90 hover:bg-white shadow" data-modal-close>x</button>
\t\t<h2 class="text-lg font-extrabold text-slate-900">เพิ่ม Inspection Model</h2>
\t\t<div class="mt-4 space-y-4">
\t\t\t<div>
\t\t\t\t<label class="block text-sm font-semibold text-slate-700">ประเภท Model <span class="text-red-500">*</span></label>
\t\t\t\t<div class="mt-2 flex gap-6">
\t\t\t\t\t<label class="inline-flex items-center gap-2 cursor-pointer">
\t\t\t\t\t\t<input type="radio" name="model_type" value="OBJECT" checked>
\t\t\t\t\t\t<span class="text-sm font-semibold text-indigo-700 bg-indigo-100 px-2 py-0.5 rounded-full">Object Detection</span>
\t\t\t\t\t</label>
\t\t\t\t\t<label class="inline-flex items-center gap-2 cursor-pointer">
\t\t\t\t\t\t<input type="radio" name="model_type" value="DEFECT">
\t\t\t\t\t\t<span class="text-sm font-semibold text-rose-700 bg-rose-100 px-2 py-0.5 rounded-full">Defect Detection</span>
\t\t\t\t\t</label>
\t\t\t\t</div>
\t\t\t</div>
\t\t\t<div>
\t\t\t\t<label class="block text-sm font-semibold text-slate-700">Class Name <span class="text-red-500">*</span></label>
\t\t\t\t<input name="class_name" required type="text" placeholder="เช่น Bolt_LH, Defect_Scratch" class="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500" />
\t\t\t</div>
\t\t\t<div>
\t\t\t\t<label class="block text-sm font-semibold text-slate-700">Description (TH)</label>
\t\t\t\t<textarea name="description_th" rows="2" class="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"></textarea>
\t\t\t</div>
\t\t\t<div>
\t\t\t\t<label class="block text-sm font-semibold text-slate-700">อัปโหลด Model File</label>
\t\t\t\t<input type="file" name="model_file" accept=".pt,.pth,.onnx,.pkl,.bin,.weights"
\t\t\t\t\tclass="mt-1 w-full text-sm text-slate-700 file:mr-3 file:py-2 file:px-4 file:rounded-lg file:border-0 file:font-semibold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100 cursor-pointer border border-slate-200 rounded-md p-1" />
\t\t\t\t<p class="text-xs text-slate-500 mt-1">รองรับ .pt .pth .onnx .pkl .bin .weights — ไฟล์จะถูก save ที่ server อัตโนมัติ</p>
\t\t\t</div>
\t\t\t<div>
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

<!-- Edit Modal -->
<div id="editModal" class="fixed inset-0 z-[9999] hidden items-center justify-center p-4 sm:p-6">
\t<div class="absolute inset-0 bg-slate-900/70 backdrop-blur-sm" data-modal-backdrop></div>
\t<form method="post" enctype="multipart/form-data" class="relative w-full max-w-lg rounded-2xl shadow-2xl bg-white p-6 max-h-[90vh] overflow-y-auto">
\t\t{% csrf_token %}
\t\t<input type="hidden" name="action" value="update">
\t\t<input type="hidden" name="id" id="editId">
\t\t<button type="button" class="absolute right-3 top-3 h-9 w-9 inline-flex items-center justify-center rounded-full bg-white/90 hover:bg-white shadow" data-modal-close>x</button>
\t\t<h2 class="text-lg font-extrabold text-slate-900">แก้ไข Inspection Model</h2>
\t\t<div class="mt-4 space-y-4">
\t\t\t<div>
\t\t\t\t<label class="block text-sm font-semibold text-slate-700">ประเภท Model <span class="text-red-500">*</span></label>
\t\t\t\t<div class="mt-2 flex gap-6">
\t\t\t\t\t<label class="inline-flex items-center gap-2 cursor-pointer">
\t\t\t\t\t\t<input type="radio" name="model_type" id="editTypeObject" value="OBJECT">
\t\t\t\t\t\t<span class="text-sm font-semibold text-indigo-700 bg-indigo-100 px-2 py-0.5 rounded-full">Object Detection</span>
\t\t\t\t\t</label>
\t\t\t\t\t<label class="inline-flex items-center gap-2 cursor-pointer">
\t\t\t\t\t\t<input type="radio" name="model_type" id="editTypeDefect" value="DEFECT">
\t\t\t\t\t\t<span class="text-sm font-semibold text-rose-700 bg-rose-100 px-2 py-0.5 rounded-full">Defect Detection</span>
\t\t\t\t\t</label>
\t\t\t\t</div>
\t\t\t</div>
\t\t\t<div>
\t\t\t\t<label class="block text-sm font-semibold text-slate-700">Class Name <span class="text-red-500">*</span></label>
\t\t\t\t<input name="class_name" id="editClassName" required type="text" class="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500" />
\t\t\t</div>
\t\t\t<div>
\t\t\t\t<label class="block text-sm font-semibold text-slate-700">Description (TH)</label>
\t\t\t\t<textarea name="description_th" id="editDescTh" rows="2" class="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"></textarea>
\t\t\t</div>
\t\t\t<div>
\t\t\t\t<label class="block text-sm font-semibold text-slate-700">Model Path ปัจจุบัน</label>
\t\t\t\t<p id="editCurrentPath" class="mt-1 text-xs font-mono text-slate-500 break-all bg-slate-50 border border-slate-200 rounded px-2 py-1.5 min-h-[28px]">(ไม่มี)</p>
\t\t\t</div>
\t\t\t<div>
\t\t\t\t<label class="block text-sm font-semibold text-slate-700">อัปโหลด Model File ใหม่ <span class="text-slate-400 font-normal">(ไม่บังคับ)</span></label>
\t\t\t\t<input type="file" name="model_file" accept=".pt,.pth,.onnx,.pkl,.bin,.weights"
\t\t\t\t\tclass="mt-1 w-full text-sm text-slate-700 file:mr-3 file:py-2 file:px-4 file:rounded-lg file:border-0 file:font-semibold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100 cursor-pointer border border-slate-200 rounded-md p-1" />
\t\t\t\t<p class="text-xs text-slate-500 mt-1">ถ้าไม่เลือกไฟล์ใหม่ จะใช้ path เดิม</p>
\t\t\t</div>
\t\t\t<div>
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

<!-- Delete Modal -->
<div id="deleteModal" class="fixed inset-0 z-[9999] hidden items-center justify-center p-4 sm:p-6">
\t<div class="absolute inset-0 bg-slate-900/70 backdrop-blur-sm" data-modal-backdrop></div>
\t<form method="post" class="relative w-full max-w-md rounded-2xl shadow-2xl bg-white p-6">
\t\t{% csrf_token %}
\t\t<input type="hidden" name="action" value="delete">
\t\t<input type="hidden" name="id" id="deleteId">
\t\t<h2 class="text-lg font-extrabold text-slate-900">ยืนยันการลบ</h2>
\t\t<p class="text-sm text-slate-700 mt-2">ต้องการลบรายการนี้หรือไม่?</p>
\t\t<div class="mt-1 text-xs text-slate-500 font-semibold" id="deleteLabel"></div>
\t\t<div class="mt-5 flex items-center justify-end gap-2">
\t\t\t<button type="button" class="px-4 py-2 rounded-lg font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200" data-modal-close>ยกเลิก</button>
\t\t\t<button type="submit" class="px-4 py-2 rounded-lg font-semibold text-white bg-red-600 hover:bg-red-700">ลบ</button>
\t\t</div>
\t</form>
</div>

<script>
(() => {
\tconst addModal = document.getElementById('addModal');
\tconst editModal = document.getElementById('editModal');
\tconst deleteModal = document.getElementById('deleteModal');

\tfunction openModal(el) { if (!el) return; el.classList.remove('hidden'); el.classList.add('flex'); }
\tfunction closeAll() { [addModal, editModal, deleteModal].forEach(m => { if(m){ m.classList.add('hidden'); m.classList.remove('flex'); }}); }
\tdocument.querySelectorAll('[data-modal-close], [data-modal-backdrop]').forEach(b => b.addEventListener('click', closeAll));

\tconst selectAll = document.getElementById('selectAllRows');
\tconst bulkDeleteBtn = document.getElementById('bulkDeleteBtn');
\tfunction updateBulk() { bulkDeleteBtn.disabled = !document.querySelectorAll('.rowCheckbox:checked').length; }
\tif (selectAll) selectAll.addEventListener('change', () => { document.querySelectorAll('.rowCheckbox').forEach(cb => cb.checked = selectAll.checked); updateBulk(); });
\tdocument.querySelectorAll('.rowCheckbox').forEach(cb => cb.addEventListener('change', updateBulk));
\tupdateBulk();

\tbulkDeleteBtn.addEventListener('click', () => {
\t\tconst ids = Array.from(document.querySelectorAll('.rowCheckbox:checked')).map(cb => cb.dataset.id);
\t\tif (!ids.length) return;
\t\tif (!confirm('ต้องการลบ ' + ids.length + ' รายการหรือไม่?')) return;
\t\tconst form = document.createElement('form');
\t\tform.method = 'post'; form.style.display = 'none';
\t\tconst csrfEl = document.createElement('input'); csrfEl.type = 'hidden'; csrfEl.name = 'csrfmiddlewaretoken';
\t\tcsrfEl.value = document.querySelector('[name=csrfmiddlewaretoken]').value;
\t\tform.appendChild(csrfEl);
\t\tconst actionEl = document.createElement('input'); actionEl.type = 'hidden'; actionEl.name = 'action'; actionEl.value = 'bulk_delete';
\t\tform.appendChild(actionEl);
\t\tids.forEach(id => { const i = document.createElement('input'); i.type='hidden'; i.name='bulk_id'; i.value=id; form.appendChild(i); });
\t\tdocument.body.appendChild(form); form.submit();
\t});

\tdocument.getElementById('openAddModal').addEventListener('click', () => openModal(addModal));

\tdocument.querySelectorAll('[data-open-edit]').forEach(btn => {
\t\tbtn.addEventListener('click', () => {
\t\t\tdocument.getElementById('editId').value = btn.dataset.id || '';
\t\t\tdocument.getElementById('editClassName').value = btn.dataset.className || '';
\t\t\tdocument.getElementById('editDescTh').value = btn.dataset.descriptionTh || '';
\t\t\tdocument.getElementById('editCountDetect').value = btn.dataset.countDetect || 0;
\t\t\tdocument.getElementById('editCurrentPath').textContent = btn.dataset.modelPath || '(ไม่มี)';
\t\t\tconst mt = btn.dataset.modelType || 'OBJECT';
\t\t\tdocument.getElementById('editTypeObject').checked = (mt === 'OBJECT');
\t\t\tdocument.getElementById('editTypeDefect').checked = (mt === 'DEFECT');
\t\t\topenModal(editModal);
\t\t});
\t});

\tdocument.querySelectorAll('[data-open-delete]').forEach(btn => {
\t\tbtn.addEventListener('click', () => {
\t\t\tdocument.getElementById('deleteId').value = btn.dataset.id || '';
\t\t\tdocument.getElementById('deleteLabel').textContent = btn.dataset.label || '';
\t\t\topenModal(deleteModal);
\t\t});
\t});
})();
</script>
{% endblock %}"""

with open(path, 'w', encoding='utf-8') as f:
    f.write(base + new_modals)
print("Done")

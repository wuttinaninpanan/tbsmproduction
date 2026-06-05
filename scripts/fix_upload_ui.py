path = '/app/templates/inspection/inspection_modelss.html'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# --- Add modal upload block ---
old_add = """\t\t\t<div>
\t\t\t\t<label class="block text-sm font-semibold text-slate-700">อัปโหลด Model File</label>
\t\t\t\t<input type="file" name="model_file" accept=".pt,.pth,.onnx,.pkl,.bin,.weights"
\t\t\t\t\tclass="mt-1 w-full text-sm text-slate-700 file:mr-3 file:py-2 file:px-4 file:rounded-lg file:border-0 file:font-semibold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100 cursor-pointer border border-slate-200 rounded-md p-1" />
\t\t\t\t<p class="text-xs text-slate-500 mt-1">รองรับ .pt .pth .onnx .pkl .bin .weights — ไฟล์จะถูก save ที่ server อัตโนมัติ</p>
\t\t\t</div>"""

new_add = """\t\t\t<div>
\t\t\t\t<label class="block text-sm font-semibold text-slate-700">อัปโหลด Model File</label>
\t\t\t\t<input type="file" id="addFileInput" name="model_file" accept=".pt,.pth,.onnx,.pkl,.bin,.weights" class="hidden" />
\t\t\t\t<div id="addFileZone" onclick="document.getElementById('addFileInput').click()"
\t\t\t\t\tclass="mt-1 flex flex-col items-center justify-center gap-2 border-2 border-dashed border-slate-300 rounded-xl px-4 py-5 cursor-pointer hover:border-indigo-400 hover:bg-indigo-50 transition">
\t\t\t\t\t<svg xmlns="http://www.w3.org/2000/svg" class="w-8 h-8 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
\t\t\t\t\t\t<path stroke-linecap="round" stroke-linejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
\t\t\t\t\t</svg>
\t\t\t\t\t<div id="addFileName" class="text-sm text-slate-500 text-center">คลิกเพื่อเลือกไฟล์ Model</div>
\t\t\t\t\t<span class="px-3 py-1 rounded-lg bg-indigo-600 text-white text-xs font-semibold">เลือกไฟล์</span>
\t\t\t\t</div>
\t\t\t\t<p class="text-xs text-slate-400 mt-1">รองรับ .pt .pth .onnx .pkl .bin .weights</p>
\t\t\t</div>"""

if old_add in content:
    content = content.replace(old_add, new_add)
    print("Add modal upload replaced")
else:
    print("WARNING: Add modal upload block not found")

# --- Edit modal upload block ---
old_edit = """\t\t\t<div>
\t\t\t\t<label class="block text-sm font-semibold text-slate-700">อัปโหลด Model File ใหม่ <span class="text-slate-400 font-normal">(ไม่บังคับ)</span></label>
\t\t\t\t<input type="file" name="model_file" accept=".pt,.pth,.onnx,.pkl,.bin,.weights"
\t\t\t\t\tclass="mt-1 w-full text-sm text-slate-700 file:mr-3 file:py-2 file:px-4 file:rounded-lg file:border-0 file:font-semibold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100 cursor-pointer border border-slate-200 rounded-md p-1" />
\t\t\t\t<p class="text-xs text-slate-500 mt-1">ถ้าไม่เลือกไฟล์ใหม่ จะใช้ path เดิม</p>
\t\t\t</div>"""

new_edit = """\t\t\t<div>
\t\t\t\t<label class="block text-sm font-semibold text-slate-700">อัปโหลด Model File ใหม่ <span class="text-slate-400 font-normal">(ไม่บังคับ)</span></label>
\t\t\t\t<input type="file" id="editFileInput" name="model_file" accept=".pt,.pth,.onnx,.pkl,.bin,.weights" class="hidden" />
\t\t\t\t<div id="editFileZone" onclick="document.getElementById('editFileInput').click()"
\t\t\t\t\tclass="mt-1 flex flex-col items-center justify-center gap-2 border-2 border-dashed border-slate-300 rounded-xl px-4 py-5 cursor-pointer hover:border-indigo-400 hover:bg-indigo-50 transition">
\t\t\t\t\t<svg xmlns="http://www.w3.org/2000/svg" class="w-8 h-8 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
\t\t\t\t\t\t<path stroke-linecap="round" stroke-linejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
\t\t\t\t\t</svg>
\t\t\t\t\t<div id="editFileName" class="text-sm text-slate-500 text-center">คลิกเพื่อเลือกไฟล์ใหม่</div>
\t\t\t\t\t<span class="px-3 py-1 rounded-lg bg-slate-600 text-white text-xs font-semibold">เลือกไฟล์</span>
\t\t\t\t</div>
\t\t\t\t<p class="text-xs text-slate-400 mt-1">ถ้าไม่เลือกไฟล์ใหม่ จะใช้ path เดิม</p>
\t\t\t</div>"""

if old_edit in content:
    content = content.replace(old_edit, new_edit)
    print("Edit modal upload replaced")
else:
    print("WARNING: Edit modal upload block not found")

# --- เพิ่ม JS สำหรับ update filename display ก่อน })(); ---
old_js_end = """\tdocument.querySelectorAll('[data-open-delete]').forEach(btn => {"""

new_js_end = """\t// File upload display
\tdocument.getElementById('addFileInput').addEventListener('change', function() {
\t\tconst nameEl = document.getElementById('addFileName');
\t\tconst zone = document.getElementById('addFileZone');
\t\tif (this.files && this.files[0]) {
\t\t\tconst name = this.files[0].name;
\t\t\tconst size = (this.files[0].size / 1024 / 1024).toFixed(2);
\t\t\tnameEl.innerHTML = '<span class="font-semibold text-indigo-700">' + name + '</span><br><span class="text-xs text-slate-400">' + size + ' MB</span>';
\t\t\tzone.classList.remove('border-slate-300');
\t\t\tzone.classList.add('border-emerald-400', 'bg-emerald-50');
\t\t} else {
\t\t\tnameEl.textContent = 'คลิกเพื่อเลือกไฟล์ Model';
\t\t\tzone.classList.remove('border-emerald-400', 'bg-emerald-50');
\t\t\tzone.classList.add('border-slate-300');
\t\t}
\t});

\tdocument.getElementById('editFileInput').addEventListener('change', function() {
\t\tconst nameEl = document.getElementById('editFileName');
\t\tconst zone = document.getElementById('editFileZone');
\t\tif (this.files && this.files[0]) {
\t\t\tconst name = this.files[0].name;
\t\t\tconst size = (this.files[0].size / 1024 / 1024).toFixed(2);
\t\t\tnameEl.innerHTML = '<span class="font-semibold text-indigo-700">' + name + '</span><br><span class="text-xs text-slate-400">' + size + ' MB</span>';
\t\t\tzone.classList.remove('border-slate-300');
\t\t\tzone.classList.add('border-emerald-400', 'bg-emerald-50');
\t\t} else {
\t\t\tnameEl.textContent = 'คลิกเพื่อเลือกไฟล์ใหม่';
\t\t\tzone.classList.remove('border-emerald-400', 'bg-emerald-50');
\t\t\tzone.classList.add('border-slate-300');
\t\t}
\t});

\t// Reset add file zone when add modal opens
\tdocument.getElementById('openAddModal').addEventListener('click', function() {
\t\tdocument.getElementById('addFileInput').value = '';
\t\tdocument.getElementById('addFileName').textContent = 'คลิกเพื่อเลือกไฟล์ Model';
\t\tconst zone = document.getElementById('addFileZone');
\t\tzone.classList.remove('border-emerald-400', 'bg-emerald-50');
\t\tzone.classList.add('border-slate-300');
\t});

\tdocument.querySelectorAll('[data-open-delete]').forEach(btn => {"""

if old_js_end in content:
    content = content.replace(old_js_end, new_js_end, 1)
    print("JS for file display added")
else:
    print("WARNING: JS end block not found")

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Done")

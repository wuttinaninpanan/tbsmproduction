(() => {
	const init = () => {
		// Excel import: hidden file input, triggered by visible button.
		const importBtn = document.getElementById('bomImportBtn');
		const importFile = document.getElementById('bomImportFile');
		const importForm = document.getElementById('bomImportForm');
		if (importBtn && importFile && importForm) {
			importBtn.addEventListener('click', () => importFile.click());
			importFile.addEventListener('change', () => {
				if (importFile.files && importFile.files.length > 0) {
					importForm.submit();
				}
			});
		}

		// Row-click navigation -> product detail page. Skips clicks on interactive controls.
		document.querySelectorAll('tr[data-detail-url]').forEach(tr => {
			tr.addEventListener('click', (e) => {
				if (e.target.closest('a, button, input, label, select, textarea')) return;
				const url = tr.dataset.detailUrl;
				if (!url) return;
				if (e.ctrlKey || e.metaKey || e.button === 1) {
					window.open(url, '_blank');
				} else {
					window.location.href = url;
				}
			});
		});
	};

	if (document.readyState === 'loading') {
		document.addEventListener('DOMContentLoaded', init);
	} else {
		init();
	}
})();

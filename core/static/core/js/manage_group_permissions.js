(() => {
	const init = () => {
		const actionForm = document.getElementById("actionForm");
		const actionField = document.getElementById("actionField");
		const idField = document.getElementById("idField");

		const $ = (id) => document.getElementById(id);
		const setField = (id, val) => { const el = $(id); if (el) el.value = val ?? ""; };
		const getInput = (id) => ($(id)?.value || "").trim();

		const addModal = $("addModal");
		const editModal = $("editModal");
		const deleteModal = $("deleteModal");

		const openModal = (el) => { if (!el) return; el.classList.remove("hidden"); el.classList.add("flex"); };
		const closeModal = (el) => { if (!el) return; el.classList.add("hidden"); el.classList.remove("flex"); };
		const closeAll = () => { closeModal(addModal); closeModal(editModal); closeModal(deleteModal); };

		document.querySelectorAll("[data-modal-close]").forEach((b) => b.addEventListener("click", closeAll));
		document.querySelectorAll("[data-modal-backdrop]").forEach((b) => b.addEventListener("click", closeAll));
		document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeAll(); });

		let submitting = false;
		const submitOnce = (btn, fn) => {
			if (submitting) return;
			submitting = true;
			if (btn) {
				btn.disabled = true;
				btn.classList.add("opacity-60", "pointer-events-none");
			}
			fn();
		};

		// Add
		$("openAddModal")?.addEventListener("click", () => {
			setField("add_name", "");
			openModal(addModal);
		});
		$("addSubmit")?.addEventListener("click", () => {
			const name = getInput("add_name");
			if (!name) {
				const el = $("add_name");
				if (el) { el.classList.add("ring-2", "ring-red-500", "border-red-500"); el.focus(); }
				return;
			}
			submitOnce($("addSubmit"), () => {
				actionField.value = "group_create";
				idField.value = "";
				setField("f_name", name);
				actionForm.submit();
			});
		});

		// Edit (rename)
		document.querySelectorAll("[data-open-edit]").forEach((btn) => {
			btn.addEventListener("click", () => {
				const ds = btn.dataset;
				idField.value = ds.id || "";
				setField("edit_name", ds.name);
				openModal(editModal);
			});
		});
		$("editSubmit")?.addEventListener("click", () => submitOnce($("editSubmit"), () => {
			actionField.value = "group_rename";
			setField("f_name", getInput("edit_name"));
			actionForm.submit();
		}));

		// Delete
		const deleteLabel = $("deleteLabel");
		document.querySelectorAll("[data-open-delete]").forEach((btn) => {
			btn.addEventListener("click", () => {
				idField.value = btn.dataset.id || "";
				if (deleteLabel) deleteLabel.textContent = btn.dataset.label || "";
				openModal(deleteModal);
			});
		});
		$("deleteSubmit")?.addEventListener("click", () => submitOnce($("deleteSubmit"), () => {
			actionField.value = "group_delete";
			actionForm.submit();
		}));
	};

	if (document.readyState === "loading") {
		document.addEventListener("DOMContentLoaded", init);
	} else {
		init();
	}
})();

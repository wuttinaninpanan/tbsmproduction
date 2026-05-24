(() => {
	const init = () => {
		const tab = window.__SETTINGS_TAB__ || "item_stage";

		const actionForm = document.getElementById("actionForm");
		const actionField = document.getElementById("actionField");
		const idField = document.getElementById("idField");

		const $ = (id) => document.getElementById(id);
		const setField = (id, val) => { const el = $(id); if (el) el.value = val ?? ""; };
		const getInput = (id) => ($(id)?.value || "").trim();
		const getCheckbox = (id) => ($(id)?.checked ? "1" : "0");

		const addModal = $("addModal");
		const editModal = $("editModal");
		const deleteModal = $("deleteModal");

		const openModal = (el) => { if (!el) return; el.classList.remove("hidden"); el.classList.add("flex"); };
		const closeModal = (el) => { if (!el) return; el.classList.add("hidden"); el.classList.remove("flex"); };
		const closeAll = () => { closeModal(addModal); closeModal(editModal); closeModal(deleteModal); };

		document.querySelectorAll("[data-modal-close]").forEach((b) => b.addEventListener("click", closeAll));
		document.querySelectorAll("[data-modal-backdrop]").forEach((b) => b.addEventListener("click", closeAll));
		document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeAll(); });

		// Whole-row navigation: clicking anywhere on a row with [data-row-href] navigates to that URL.
		document.querySelectorAll("tr[data-row-href]").forEach((tr) => {
			tr.addEventListener("click", () => { window.location.href = tr.dataset.rowHref; });
		});

		// defect_by_category tab has no inline modals (managed on a dedicated page).
		if (tab === "defect_by_category") return;

		const collectAdd = () => {
			if (tab === "item_stage") {
				setField("f_name", getInput("add_name"));
				setField("f_display_name", getInput("add_display_name"));
				return "stage_create";
			}
			if (tab === "item_category") {
				setField("f_name", getInput("add_name"));
				setField("f_description", getInput("add_description"));
				return "cat_create";
			}
			if (tab === "way") {
				setField("f_title", getInput("add_title"));
				return "way_create";
			}
			// defect_mode
			setField("f_category_id", getInput("add_category_id"));
			setField("f_name_th", getInput("add_name_th"));
			setField("f_name_en", getInput("add_name_en"));
			setField("f_name_jp", getInput("add_name_jp"));
			setField("f_description_th", getInput("add_description_th"));
			setField("f_description_en", getInput("add_description_en"));
			setField("f_description_jp", getInput("add_description_jp"));
			return "defect_create";
		};

		const collectEdit = () => {
			if (tab === "item_stage") {
				setField("f_name", getInput("edit_name"));
				setField("f_display_name", getInput("edit_display_name"));
				return "stage_update";
			}
			if (tab === "item_category") {
				setField("f_name", getInput("edit_name"));
				setField("f_description", getInput("edit_description"));
				return "cat_update";
			}
			if (tab === "way") {
				setField("f_title", getInput("edit_title"));
				return "way_update";
			}
			// defect_mode
			setField("f_name_th", getInput("edit_name_th"));
			setField("f_name_en", getInput("edit_name_en"));
			setField("f_name_jp", getInput("edit_name_jp"));
			setField("f_description_th", getInput("edit_description_th"));
			setField("f_description_en", getInput("edit_description_en"));
			setField("f_description_jp", getInput("edit_description_jp"));
			return "defect_update";
		};

		const deleteAction = () => {
			if (tab === "item_stage") return "stage_delete";
			if (tab === "item_category") return "cat_delete";
			if (tab === "way") return "way_delete";
			return "defect_delete";
		};

		// Submit guard — disables a button after first click to prevent
		// the double-submit that produces duplicate rows when a user
		// clicks twice before the page redirects.
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
			// reset inputs in add modal
			addModal.querySelectorAll("input[type=text], input:not([type]), input[type=email], select").forEach((el) => { el.value = ""; });
			addModal.querySelectorAll("input[type=checkbox]").forEach((el) => { el.checked = false; });
			openModal(addModal);
		});
		$("addSubmit")?.addEventListener("click", () => {
			// Category is required when adding a defect mode.
			if (tab === "defect_mode" && !getInput("add_category_id")) {
				const sel = $("add_category_id");
				if (sel) { sel.classList.add("ring-2", "ring-red-500", "border-red-500"); sel.focus(); }
				alert("กรุณาเลือก Category");
				return;
			}
			submitOnce($("addSubmit"), () => {
				actionField.value = collectAdd();
				idField.value = "";
				actionForm.submit();
			});
		});

		// Edit
		document.querySelectorAll("[data-open-edit]").forEach((btn) => {
			btn.addEventListener("click", () => {
				const ds = btn.dataset;
				idField.value = ds.id || "";
				if (tab === "item_stage") {
					setField("edit_name", ds.name);
					setField("edit_display_name", ds.displayName);
				} else if (tab === "item_category") {
					setField("edit_name", ds.name);
					setField("edit_description", ds.description);
				} else if (tab === "defect_mode") {
					setField("edit_name_th", ds.nameTh);
					setField("edit_name_en", ds.nameEn);
					setField("edit_name_jp", ds.nameJp);
					setField("edit_description_th", ds.descriptionTh);
					setField("edit_description_en", ds.descriptionEn);
					setField("edit_description_jp", ds.descriptionJp);
				} else if (tab === "way") {
					setField("edit_title", ds.title);
				} else {
					setField("edit_category_id", ds.categoryId);
					setField("edit_defect_mode_id", ds.defectModeId);
					setField("edit_title", ds.title);
					setField("edit_description", ds.description);
					const cb = $("edit_is_inlist");
					if (cb) cb.checked = ds.isInlist === "1";
				}
				openModal(editModal);
			});
		});
		$("editSubmit")?.addEventListener("click", () => submitOnce($("editSubmit"), () => {
			actionField.value = collectEdit();
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
			actionField.value = deleteAction();
			actionForm.submit();
		}));
	};

	if (document.readyState === "loading") {
		document.addEventListener("DOMContentLoaded", init);
	} else {
		init();
	}
})();

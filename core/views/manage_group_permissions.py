from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.models import Group, Permission
from django.db import IntegrityError, transaction
from django.db.models import Count, Q
from django.http import Http404
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView

from core.auth.decorators import admin_required
from core.services.auditlog import log_event


@method_decorator(admin_required, name="dispatch")
class ManageGroupPermissionsViews(TemplateView):
	"""List/create/rename/delete Group records (the coarse-grained roles that
	permissions and users attach to). Assigning individual permissions to a
	group happens on ManageGroupPermissionsDetailView."""

	template_name = "core/manage_group_permissions.html"

	# ------------------------------------------------------------------ GET

	def get_context_data(self, **kwargs):
		ctx = super().get_context_data(**kwargs)
		request = self.request

		q = (request.GET.get("q") or "").strip()
		qs = Group.objects.annotate(
			permission_count=Count("permissions", distinct=True),
			user_count=Count("user", distinct=True),
		)
		if q:
			qs = qs.filter(Q(name__icontains=q))
		qs = qs.order_by("name")

		ctx["q"] = q
		ctx["groups"] = list(qs)
		ctx["total_count"] = qs.count()
		return ctx

	# ------------------------------------------------------------------ POST

	def post(self, request, *args, **kwargs):
		action = (request.POST.get("action") or "").strip().lower()
		handler = {
			"group_create": self._group_create,
			"group_rename": self._group_rename,
			"group_delete": self._group_delete,
		}.get(action)
		if handler is None:
			messages.error(request, "ไม่รู้จัก action")
			return redirect(request.get_full_path())
		return handler(request, *args, **kwargs)

	def _group_create(self, request, *args, **kwargs):
		name = (request.POST.get("name") or "").strip()
		if not name:
			messages.error(request, "กรุณากรอกชื่อ Group")
			return redirect(request.get_full_path())
		try:
			with transaction.atomic():
				group = Group.objects.create(name=name)
				transaction.on_commit(
					lambda: log_event(request, action="group:create", message="เพิ่ม Group", metadata={"id": group.pk, "name": name})
				)
			messages.success(request, "เพิ่ม Group สำเร็จ")
		except IntegrityError:
			messages.error(request, "ข้อมูลซ้ำ: ชื่อ Group นี้มีอยู่แล้ว")
		except Exception as e:
			messages.error(request, f"เกิดข้อผิดพลาด: {e}")
		return redirect(request.get_full_path())

	def _group_rename(self, request, *args, **kwargs):
		group_id = (request.POST.get("id") or "").strip()
		if not group_id.isdigit():
			messages.error(request, "ไม่พบรหัส Group")
			return redirect(request.get_full_path())
		name = (request.POST.get("name") or "").strip()
		if not name:
			messages.error(request, "กรุณากรอกชื่อ Group")
			return redirect(request.get_full_path())
		group = Group.objects.filter(pk=group_id).first()
		if group is None:
			messages.error(request, "ไม่พบ Group")
			return redirect(request.get_full_path())
		try:
			with transaction.atomic():
				if group.name != name:
					old_name = group.name
					group.name = name
					group.save(update_fields=["name"])
					transaction.on_commit(
						lambda: log_event(request, action="group:rename", message="แก้ไขชื่อ Group", metadata={"id": group.pk, "old_name": old_name, "new_name": name})
					)
					messages.success(request, "บันทึกการแก้ไขสำเร็จ")
				else:
					messages.info(request, "ไม่มีการเปลี่ยนแปลง")
		except IntegrityError:
			messages.error(request, "ข้อมูลซ้ำ: ชื่อ Group นี้มีอยู่แล้ว")
		except Exception as e:
			messages.error(request, f"เกิดข้อผิดพลาด: {e}")
		return redirect(request.get_full_path())

	def _group_delete(self, request, *args, **kwargs):
		group_id = (request.POST.get("id") or "").strip()
		if not group_id.isdigit():
			messages.error(request, "ไม่พบรหัส Group")
			return redirect(request.get_full_path())
		group = Group.objects.filter(pk=group_id).first()
		if group is None:
			messages.error(request, "ไม่พบ Group")
			return redirect(request.get_full_path())
		name = group.name
		try:
			group.delete()
			transaction.on_commit(
				lambda: log_event(request, action="group:delete", message="ลบ Group", metadata={"id": group_id, "name": name})
			)
			messages.success(request, "ลบสำเร็จ")
		except Exception as e:
			messages.error(request, f"เกิดข้อผิดพลาด: {e}")
		return redirect(request.get_full_path())


@method_decorator(admin_required, name="dispatch")
class ManageGroupPermissionsDetailView(TemplateView):
	"""Pick-list editor: tick which Permissions belong to a Group.

	Every Permission in the system is rendered as a checkbox, grouped by app
	label, so the save can safely reconcile the group's permission set against
	the full catalogue (same pattern as ManageSettingsDefectByCategoryView).
	"""

	template_name = "core/manage_group_permissions_detail.html"

	def _get_group(self):
		group_id = self.kwargs.get("group_id")
		group = Group.objects.filter(pk=group_id).first()
		if group is None:
			raise Http404("Group not found")
		return group

	# ------------------------------------------------------------------ GET

	def get_context_data(self, **kwargs):
		ctx = super().get_context_data(**kwargs)
		group = self._get_group()

		checked_ids = set(group.permissions.values_list("id", flat=True))

		perms = (
			Permission.objects.select_related("content_type")
			.order_by("content_type__app_label", "content_type__model", "codename")
		)

		apps: dict[str, dict] = {}
		for p in perms:
			app_label = p.content_type.app_label
			bucket = apps.setdefault(app_label, {"app_label": app_label, "permissions": []})
			bucket["permissions"].append({
				"id": p.id,
				"name": p.name,
				"codename": p.codename,
				"model": p.content_type.model,
				"checked": p.id in checked_ids,
			})

		ctx["group"] = group
		ctx["app_groups"] = sorted(apps.values(), key=lambda a: a["app_label"])
		ctx["selected_count"] = len(checked_ids)
		ctx["total_count"] = perms.count()
		ctx["back_url"] = reverse("manage_group_permissions")
		return ctx

	# ------------------------------------------------------------------ POST

	def post(self, request, *args, **kwargs):
		group = self._get_group()

		submitted_ids = set()
		for raw in request.POST.getlist("permission_ids"):
			raw = (raw or "").strip()
			if raw.isdigit():
				submitted_ids.add(int(raw))

		valid_ids = set(
			Permission.objects.filter(pk__in=submitted_ids).values_list("id", flat=True)
		)

		try:
			with transaction.atomic():
				before_ids = set(group.permissions.values_list("id", flat=True))
				group.permissions.set(valid_ids)
				added = len(valid_ids - before_ids)
				removed = len(before_ids - valid_ids)
				transaction.on_commit(
					lambda: log_event(
						request,
						action="group:set_permissions",
						message="แก้ไขสิทธิ์ของ Group",
						metadata={"id": group.pk, "name": group.name, "added": added, "removed": removed},
					)
				)
			if added or removed:
				messages.success(request, f"บันทึกสิทธิ์ของ Group “{group.name}” สำเร็จ")
			else:
				messages.info(request, "ไม่มีการเปลี่ยนแปลง")
		except Exception as e:
			messages.error(request, f"เกิดข้อผิดพลาด: {e}")

		return redirect("manage_group_permissions_detail", group_id=group.pk)

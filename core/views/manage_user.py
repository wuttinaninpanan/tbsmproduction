from django.contrib.auth import get_user_model
from django.contrib import messages
from django.db.models import Q
from django.views.generic import TemplateView
from django.utils.decorators import method_decorator

from core.decorators import admin_required


@method_decorator(admin_required, name='dispatch')
class ManageUserViews(TemplateView):
	template_name = "manage_user.html"

	def get_context_data(self, **kwargs):
		ctx = super().get_context_data(**kwargs)
		request = self.request
		q = (request.GET.get("q") or "").strip()
		role = (request.GET.get("role") or "").strip().lower()
		status = (request.GET.get("status") or "").strip().lower()

		User = get_user_model()
		qs = User.objects.all().order_by("username")

		if q:
			qs = qs.filter(
				Q(username__icontains=q)
				| Q(email__icontains=q)
				| Q(first_name__icontains=q)
				| Q(last_name__icontains=q)
			)

		if role == "admin":
			qs = qs.filter(is_superuser=True)
		elif role == "staff":
			qs = qs.filter(is_staff=True, is_superuser=False)
		elif role == "user":
			qs = qs.filter(is_staff=False, is_superuser=False)

		if status == "active":
			qs = qs.filter(is_active=True)
		elif status == "disabled":
			qs = qs.filter(is_active=False)

		total_count = qs.count()

		ctx["users"] = list(qs[:500])
		ctx["q"] = q
		ctx["role"] = role
		ctx["status"] = status
		ctx["total_count"] = total_count
		# Optional: override in backend to point at a delete endpoint.
		ctx.setdefault("delete_action", "")
		return ctx

	def post(self, request, *args, **kwargs):
		action = (request.POST.get("action") or "").strip().lower()
		user_id = (request.POST.get("id") or "").strip()
		User = get_user_model()

		if not user_id.isdigit():
			messages.error(request, "ไม่พบรหัสผู้ใช้งาน")
			return self.get(request, *args, **kwargs)

		try:
			target_user = User.objects.get(pk=int(user_id))
		except User.DoesNotExist:
			messages.error(request, "ไม่พบผู้ใช้งาน")
			return self.get(request, *args, **kwargs)

		if action == "update":
			full_name = (request.POST.get("full_name") or "").strip()
			first_name = (request.POST.get("first_name") or "").strip()
			last_name = (request.POST.get("last_name") or "").strip()
			email = (request.POST.get("email") or "").strip()
			role = (request.POST.get("role") or "").strip().lower()
			shift = (request.POST.get("shift") or "shift_day").strip()
			is_active = (request.POST.get("is_active") or "") == "on"
			new_password = (request.POST.get("password") or "").strip()

			# Prefer full_name if provided (supports popup UI)
			if full_name:
				parts = [p for p in full_name.split() if p]
				if len(parts) == 1:
					first_name = parts[0]
					last_name = ""
				else:
					first_name = parts[0]
					last_name = " ".join(parts[1:])

			# Apply fields
			target_user.first_name = first_name
			target_user.last_name = last_name
			target_user.email = email
			target_user.is_active = is_active

			# Role mapping
			if role == "admin":
				target_user.is_superuser = True
				target_user.is_staff = True
			elif role == "staff":
				target_user.is_superuser = False
				target_user.is_staff = True
			else:
				target_user.is_superuser = False
				target_user.is_staff = False

			if new_password:
				target_user.set_password(new_password)

			target_user.save()
			
			# Update UserProfile shift
			from core.models import UserProfile
			profile, _ = UserProfile.objects.get_or_create(user=target_user)
			profile.shift = shift
			profile.save()
			
			messages.success(request, f"อัปเดตผู้ใช้งาน {target_user.username} สำเร็จ")
			return self.get(request, *args, **kwargs)

		if action == "delete":
			# Safety: prevent deleting yourself (if authenticated)
			if getattr(request, "user", None) is not None and request.user.is_authenticated:
				if request.user.pk == target_user.pk:
					messages.error(request, "ไม่สามารถลบบัญชีที่กำลังใช้งานอยู่")
					return self.get(request, *args, **kwargs)

			target_username = target_user.username
			target_user.delete()
			messages.success(request, f"ลบผู้ใช้งาน {target_username} สำเร็จ")
			return self.get(request, *args, **kwargs)

		messages.error(request, "คำสั่งไม่ถูกต้อง")
		return self.get(request, *args, **kwargs)

from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.views.generic import TemplateView
from django.utils.decorators import method_decorator
from django.shortcuts import redirect

from core.auth.decorators import user_required
from core.services.auditlog import log_event


@method_decorator(user_required, name='dispatch')
class ProfileViews(TemplateView):
    template_name = "core/profile.html"

    def post(self, request, *args, **kwargs):
        action = (request.POST.get("action") or "").strip().lower()

        if action == "update_profile":
            first_name = (request.POST.get("first_name") or "").strip()
            last_name = (request.POST.get("last_name") or "").strip()
            email = (request.POST.get("email") or "").strip()

            user = request.user
            user.first_name = first_name
            user.last_name = last_name
            user.email = email
            user.save(update_fields=["first_name", "last_name", "email"])

            log_event(
                request,
                action="profile:update",
                status="success",
                message="อัปเดตโปรไฟล์",
                metadata={"user_id": user.pk, "username": user.username},
            )
            messages.success(request, "อัปเดตโปรไฟล์สำเร็จ")
            return redirect(request.get_full_path())
        if action == "change_password":
            current_password = request.POST.get("current_password") or ""
            new_password = (request.POST.get("new_password") or "").strip()
            confirm_password = (request.POST.get("confirm_password") or "").strip()

            user = request.user

            if not user.check_password(current_password):
                messages.error(request, "รหัสผ่านปัจจุบันไม่ถูกต้อง")
                return redirect(request.get_full_path())
            if len(new_password) < 8:
                messages.error(request, "รหัสผ่านใหม่ต้องมีอย่างน้อย 8 ตัวอักษร")
                return redirect(request.get_full_path())
            if new_password != confirm_password:
                messages.error(request, "รหัสผ่านใหม่และยืนยันรหัสผ่านไม่ตรงกัน")
                return redirect(request.get_full_path())
            user.set_password(new_password)
            user.save()
            update_session_auth_hash(request, user)

            log_event(
                request,
                action="profile:change_password",
                status="success",
                message="เปลี่ยนรหัสผ่าน",
                metadata={"user_id": user.pk, "username": user.username},
            )
            messages.success(request, "เปลี่ยนรหัสผ่านสำเร็จ")
            return redirect(request.get_full_path())
        messages.error(request, "คำสั่งไม่ถูกต้อง")
        return redirect(request.get_full_path())
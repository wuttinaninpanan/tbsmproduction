from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.shortcuts import redirect, render
from django.views.generic import TemplateView

from core.services.auditlog import log_event


class LoginViews(TemplateView):
    template_name = "core/login.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["next"] = (self.request.GET.get("next") or "").strip()
        return ctx

    def post(self, request, *args, **kwargs):
        username = (request.POST.get("username") or "").strip()
        password = (request.POST.get("password") or "").strip()
        next_url = (request.POST.get("next") or request.GET.get("next") or "/").strip() or "/"
        remember = (request.POST.get("remember") or "") in {"on", "1", "true", "True"}

        if not username or not password:
            return render(
                request,
                self.template_name,
                {"error": "กรุณากรอกชื่อผู้ใช้และรหัสผ่าน", "next": next_url},
            )

        user = authenticate(request, username=username, password=password)
        if user is None:
            log_event(
                request,
                action="login",
                status="failure",
                actor_username=username,
                message="Invalid credentials",
            )
            return render(
                request,
                self.template_name,
                {"error": "ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง", "next": next_url},
            )

        if not user.is_active:
            log_event(
                request,
                action="login",
                status="failure",
                actor_username=username,
                message="Inactive account",
            )
            return render(
                request,
                self.template_name,
                {"error": "บัญชีนี้ถูกปิดใช้งาน", "next": next_url},
            )

        login(request, user)
        log_event(
            request,
            action="login",
            status="success",
            message="User logged in",
            metadata={"remember": bool(remember)},
        )
        if not remember:
            # Expire session on browser close
            request.session.set_expiry(0)
        messages.success(request, f"ยินดีต้อนรับ {user.username}")
        return redirect(next_url)


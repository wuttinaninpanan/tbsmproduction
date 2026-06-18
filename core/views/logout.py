from django.contrib import messages
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.views import View

from core.services.auditlog import log_event


class LogoutView(View):
    def get(self, request, *args, **kwargs):
        log_event(request, action="logout", status="success", message="User logged out")
        logout(request)
        messages.success(request, "ออกจากระบบเรียบร้อยแล้ว")
        return redirect("/")

    def post(self, request, *args, **kwargs):
        log_event(request, action="logout", status="success", message="User logged out")
        logout(request)
        messages.success(request, "ออกจากระบบเรียบร้อยแล้ว")
        return redirect("/")

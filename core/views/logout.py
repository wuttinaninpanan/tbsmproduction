from django.contrib import messages
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.views import View


class LogoutView(View):
    def get(self, request, *args, **kwargs):
        logout(request)
        messages.success(request, "ออกจากระบบเรียบร้อยแล้ว")
        return redirect("/")

    def post(self, request, *args, **kwargs):
        logout(request)
        messages.success(request, "ออกจากระบบเรียบร้อยแล้ว")
        return redirect("/")

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps


def user_required(view_func):
    """Decorator for views that requires user to be logged in (any authenticated user)."""

    @wraps(view_func)
    @login_required(login_url="/login/")
    def wrapper(request, *args, **kwargs):
        return view_func(request, *args, **kwargs)

    return wrapper


def staff_required(view_func):
    """Decorator for views that requires user to be staff or superuser."""

    @wraps(view_func)
    @login_required(login_url="/login/")
    def wrapper(request, *args, **kwargs):
        if not (request.user.is_staff or request.user.is_superuser):
            messages.error(request, "คุณไม่มีสิทธิ์เข้าถึงหน้านี้ (ต้องการสิทธิ์ Staff)")
            return redirect("/")
        return view_func(request, *args, **kwargs)

    return wrapper


def admin_required(view_func):
    """Decorator for views that requires user to be superuser (admin)."""

    @wraps(view_func)
    @login_required(login_url="/login/")
    def wrapper(request, *args, **kwargs):
        if not request.user.is_superuser:
            messages.error(request, "คุณไม่มีสิทธิ์เข้าถึงหน้านี้ (ต้องการสิทธิ์ Admin)")
            return redirect("/")
        return view_func(request, *args, **kwargs)

    return wrapper

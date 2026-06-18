from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps


def permissions_required(
    perms,
    *,
    any_perm: bool = False,
    login_url: str = "/login/",
    redirect_url: str = "/",
    message: str | None = None,
):
    """Decorator for views that require Django auth permissions.

    This uses the standard Django permission system which is backed by the
    `<user>_groups` and `<user>_user_permissions` many-to-many tables (for this
    project: `core_user_groups` and `core_user_user_permissions`).

    Args:
        perms: A permission codename (e.g. "core.add_user") or an iterable of them.
        any_perm: If True, user must have at least one permission in perms.
        login_url: Where to redirect unauthenticated users.
        redirect_url: Where to redirect unauthorized users.
        message: Optional custom denial message.
    """

    if isinstance(perms, str):
        perm_list = [perms]
    else:
        perm_list = [p for p in (perms or []) if p]

    def decorator(view_func):
        @wraps(view_func)
        @login_required(login_url=login_url)
        def wrapper(request, *args, **kwargs):
            user = getattr(request, "user", None)
            # Superuser bypasses all permission checks.
            if user is not None and getattr(user, "is_superuser", False):
                return view_func(request, *args, **kwargs)

            has = False
            if user is not None and getattr(user, "is_authenticated", False):
                if not perm_list:
                    has = True
                elif any_perm:
                    has = any(user.has_perm(p) for p in perm_list)
                else:
                    has = all(user.has_perm(p) for p in perm_list)

            if not has:
                messages.error(request, message or "คุณไม่มีสิทธิ์ดำเนินการนี้")
                return redirect(redirect_url)
            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator


def permission_required(
    perm: str,
    *,
    login_url: str = "/login/",
    redirect_url: str = "/",
    message: str | None = None,
):
    """Shortcut for requiring a single permission."""
    return permissions_required(
        perm,
        any_perm=False,
        login_url=login_url,
        redirect_url=redirect_url,
        message=message,
    )


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

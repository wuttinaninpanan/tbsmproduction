from django.db import models  # type:ignore
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin  # type:ignore


class UserManager(BaseUserManager):
    def create_user(self, username: str, password: str | None = None, **extra_fields):
        if not username:
            raise ValueError("username is required")
        user = self.model(username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username: str, password: str | None = None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True")
        return self.create_user(username=username, password=password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(blank=True, null=True)
    first_name = models.CharField(max_length=150, blank=True, default="")
    last_name = models.CharField(max_length=150, blank=True, default="")
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    company_name = models.CharField(max_length=255, blank=True, null=True)
    has_password = models.BooleanField(default=True)
    telephone_number = models.CharField(max_length=150, blank=True)
    must_change_password = models.BooleanField(default=True)
    totp_secret = models.CharField(max_length=64, blank=True, null=True)
    totp_enabled = models.BooleanField(default=False)
    totp_backup_codes = models.JSONField(default=list, blank=True)
    employee_role = models.ForeignKey(
        "core.EmployeeRole",
        on_delete=models.PROTECT,
        related_name="users",
        null=True,
        blank=True,
    )

    objects = UserManager()

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS: list[str] = []

    def get_full_name(self) -> str:
        return (f"{self.first_name} {self.last_name}").strip()

    def get_short_name(self) -> str:
        return self.first_name.strip() or self.username

    def __str__(self) -> str:
        return self.username

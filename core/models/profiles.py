from django.conf import settings
from django.db import models


class UserProfile(models.Model):
    SHIFT_CHOICES = [
        ("shift_a", "กะ A"),
        ("shift_b", "กะ B"),
        ("shift_day", "กะ Day"),
    ]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    shift = models.CharField(
        max_length=20,
        choices=SHIFT_CHOICES,
        default="shift_day",
        help_text="เลือกกะการทำงาน",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"{self.user.username} - {self.get_shift_display()}"

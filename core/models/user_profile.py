import uuid
from django.conf import settings  # type:ignore
from django.db import models  # type:ignore
from core.models.base import BaseModel


class UserProfile(BaseModel):
    class Shift(models.TextChoices):
        SHIFT_A = "shift_a", "กะ A"
        SHIFT_B = "shift_b", "กะ B"
        SHIFT_DAY = "shift_day", "กะ Day"

    class Gender(models.TextChoices):
        MALE = "MALE", "Male"
        FEMALE = "FEMALE", "Female"
        OTHER = "OTHER", "Other"
        NOT_SPECIFIED = "NOT_SPECIFIED", "Not specified"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile"
    )

    display_name = models.CharField(
        max_length=255
    )

    shift = models.CharField(
        max_length=20,
        choices=Shift.choices,
        default=Shift.SHIFT_DAY,
    )

    avatar_url = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    language = models.CharField(
        max_length=8,
        blank=True,
        null=True,
        help_text="th ,ja, en"
    )

    gender = models.CharField(
        max_length=50,
        choices=Gender.choices,
        default=Gender.NOT_SPECIFIED
    )
    timezone = models.CharField(max_length=50, blank=True, null=True)
    country_code = models.CharField(max_length=50, blank=True, null=True)
    occupation = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        db_table = "user_profile"
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"

    def __str__(self):
        return f"{self.display_name} ({self.user_id})"

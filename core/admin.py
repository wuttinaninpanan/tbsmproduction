from __future__ import annotations

from django import forms
from django.apps import apps
from django.contrib import admin
from django.contrib.admin.sites import AlreadyRegistered
from django.contrib.auth.forms import ReadOnlyPasswordHashField

from core.models import User


class UserCreationForm(forms.ModelForm):
	password1 = forms.CharField(label="Password", widget=forms.PasswordInput)
	password2 = forms.CharField(label="Password confirmation", widget=forms.PasswordInput)

	class Meta:
		model = User
		fields = ("username", "email", "first_name", "last_name", "company_name", "telephone_number")

	def clean_password2(self):
		password1 = self.cleaned_data.get("password1")
		password2 = self.cleaned_data.get("password2")
		if password1 and password2 and password1 != password2:
			raise forms.ValidationError("Passwords don't match")
		return password2

	def save(self, commit=True):
		user = super().save(commit=False)
		user.set_password(self.cleaned_data["password1"])
		if commit:
			user.save()
			self.save_m2m()
		return user


class UserChangeForm(forms.ModelForm):
	password = ReadOnlyPasswordHashField(
		label="Password",
		help_text=(
			"Raw passwords are not stored, so there is no way to see this user's password. "
			"You can change the password using <a href=\"../password/\">this form</a>."
		),
	)

	class Meta:
		model = User
		fields = (
			"username",
			"email",
			"first_name",
			"last_name",
			"company_name",
			"telephone_number",
			"password",
			"is_active",
			"is_staff",
			"is_superuser",
			"groups",
			"user_permissions",
		)


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
	form = UserChangeForm
	add_form = UserCreationForm

	list_display = (
		"username",
		"email",
		"first_name",
		"last_name",
		"is_staff",
		"is_superuser",
		"is_active",
	)
	list_filter = ("is_staff", "is_superuser", "is_active")
	search_fields = ("username", "email", "first_name", "last_name", "company_name", "telephone_number")
	ordering = ("username",)
	filter_horizontal = ("groups", "user_permissions")

	fieldsets = (
		(None, {"fields": ("username", "password")}),
		("Personal info", {"fields": ("first_name", "last_name", "email", "company_name", "telephone_number")}),
		(
			"Permissions",
			{"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")},
		),
	)
	add_fieldsets = (
		(
			None,
			{
				"classes": ("wide",),
				"fields": (
					"username",
					"email",
					"first_name",
					"last_name",
					"company_name",
					"telephone_number",
					"password1",
					"password2",
					"is_active",
					"is_staff",
					"is_superuser",
					"groups",
					"user_permissions",
				),
			},
		),
	)


def _register_core_models():
	app_config = apps.get_app_config("core")
	for model in app_config.get_models():
		if model is User:
			continue
		try:
			admin.site.register(model)
		except AlreadyRegistered:
			pass


_register_core_models()


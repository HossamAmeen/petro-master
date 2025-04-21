from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _

from .models import CompanyUser, FirebaseToken, User


class CustomUserChangeForm(forms.ModelForm):
    password1 = forms.CharField(
        label=_("Password"),
        widget=forms.PasswordInput,
        required=False,
        help_text=_("Leave empty to keep the current password."),
    )
    password2 = forms.CharField(
        label=_("Confirm Password"), widget=forms.PasswordInput, required=False
    )

    class Meta:
        model = User
        fields = ("name", "email", "phone_number", "role", "is_active")

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")

        if password1 and password2:
            if password1 != password2:
                raise forms.ValidationError("Passwords don't match.")

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        if self.cleaned_data["password1"]:
            user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class CustomUserAdmin(UserAdmin):
    form = CustomUserChangeForm
    list_display = (
        "id",
        "name",
        "email",
        "phone_number",
        "role",
        "is_active",
        "is_staff",
        "is_superuser",
        "created",
    )
    search_fields = ("name", "email", "phone_number")
    list_filter = ("role", "created", "is_active", "is_staff", "is_superuser")

    fieldsets = (
        (
            "User Info",
            {"fields": ("name", "email", "phone_number", "password1", "password2")},
        ),
        ("Permissions", {"fields": ("role", "is_active")}),
    )

    add_fieldsets = (
        (
            "User Info",
            {"fields": ("name", "email", "phone_number", "password1", "password2")},
        ),
        ("Permissions", {"fields": ("role", "is_active")}),
    )

    ordering = ("-created",)
    filter_horizontal = ()

    def has_delete_permission(self, request, obj=None):
        return False

    def created(self, obj):
        return obj.created

    created.admin_order_field = "created"
    created.short_description = _("Created")


class CompanyUserForm(forms.ModelForm):
    password1 = forms.CharField(
        label=_("Password"),
        widget=forms.PasswordInput,
        required=False,
        help_text=_("Leave empty to keep the current password."),
    )
    password2 = forms.CharField(
        label=_("Confirm Password"), widget=forms.PasswordInput, required=False
    )

    class Meta:
        model = CompanyUser
        fields = (
            "name",
            "email",
            "phone_number",
            "password1",
            "password2",
            "is_active",
            "is_staff",
        )

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")

        if password1 and password2:
            if password1 != password2:
                raise forms.ValidationError("Passwords don't match.")

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = User.UserRoles.CompanyOwner
        if self.cleaned_data["password1"]:
            user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class CompanyUserInterface(admin.ModelAdmin):
    form = CompanyUserForm
    list_display = (
        "id",
        "name",
        "email",
        "phone_number",
        "role",
        "is_active",
        "is_staff",
        "company",
        "created",
    )
    search_fields = ("name", "email", "phone_number", "company__name")
    list_filter = ("role", "created", "is_active", "is_staff", "company")

    fieldsets = (
        (
            "User Info",
            {
                "fields": (
                    "name",
                    "email",
                    "phone_number",
                    "password1",
                    "password2",
                    "company",
                    "is_active",
                )
            },
        ),
    )

    add_fieldsets = (
        (
            "User Info",
            {
                "fields": (
                    "name",
                    "email",
                    "phone_number",
                    "password1",
                    "password2",
                    "company",
                    "is_active",
                )
            },
        ),
    )

    ordering = ("-created",)
    filter_horizontal = ()

    def has_delete_permission(self, request, obj=None):
        return False

    def created(self, obj):
        return obj.created

    created.admin_order_field = "created"
    created.short_description = _("Created")


admin.site.register(User, CustomUserAdmin)
admin.site.register(CompanyUser, CompanyUserInterface)
admin.site.register(
    FirebaseToken,
)

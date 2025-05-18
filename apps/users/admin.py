from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Group
from django.utils.translation import gettext_lazy as _

from .models import (
    CompanyUser,
    FirebaseToken,
    StationBranchManager,
    StationOwner,
    User,
    Worker,
)


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
        fields = ("name", "email", "phone_number", "is_active")

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
        user.role = User.UserRoles.Admin
        user.is_staff = True
        user.is_superuser = True
        if self.cleaned_data["password1"]:
            user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()

        return user


@admin.register(User)
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
    list_filter = ("is_active",)

    fieldsets = (
        (
            "User Info",
            {"fields": ("name", "email", "phone_number", "password1", "password2")},
        ),
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

    def get_queryset(self, request):
        return super().get_queryset(request).filter(role=User.UserRoles.Admin)


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
    role = forms.ChoiceField(
        choices=[
            (User.UserRoles.CompanyOwner, "Company Owner"),
            (User.UserRoles.CompanyBranchManager, "Company Branch Manager"),
        ],
        widget=forms.RadioSelect,
        initial=User.UserRoles.CompanyOwner,
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
            "role",
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
        if self.cleaned_data["password1"]:
            user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


@admin.register(CompanyUser)
class CompanyUserInterface(admin.ModelAdmin):
    list_per_page = 10
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
    list_filter = ("company",)

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
                    "role",
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
                    "role",
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


class StationOwnerForm(forms.ModelForm):
    password1 = forms.CharField(
        label=_("Password"),
        widget=forms.PasswordInput,
        required=False,
        help_text=_("Leave empty to keep the current password."),
    )
    password2 = forms.CharField(
        label=_("Confirm Password"), widget=forms.PasswordInput, required=False
    )
    role = forms.ChoiceField(
        choices=[
            (User.UserRoles.StationOwner, "Station Owner"),
            (User.UserRoles.StationBranchManager, "Station Manager"),
        ],
        widget=forms.RadioSelect,
        initial=User.UserRoles.StationOwner,
    )

    class Meta:
        model = StationOwner
        fields = (
            "name",
            "email",
            "phone_number",
            "station",
            "password1",
            "password2",
            "is_active",
            "role",
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
        if self.cleaned_data["password1"]:
            user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


@admin.register(StationOwner)
class StationOwnerInterface(admin.ModelAdmin):
    form = StationOwnerForm
    list_display = (
        "id",
        "name",
        "email",
        "phone_number",
        "role",
        "station",
        "is_active",
        "created",
    )
    search_fields = ("name", "email", "phone_number")
    list_filter = ("is_active", "station")
    ordering = ("-created",)
    list_per_page = 10


class StationManagerForm(forms.ModelForm):
    class Meta:
        model = StationBranchManager
        fields = (
            "user",
            "station_branch",
        )


@admin.register(StationBranchManager)
class StationBranchManagerInterface(admin.ModelAdmin):
    form = StationManagerForm
    list_display = ("user", "station_branch")
    search_fields = ("user", "station_branch")
    list_filter = ("user", "station_branch")
    hidden_fields = ("created",)
    list_per_page = 10

    class Meta:
        model = StationBranchManager
        fields = ("user", "station_branch")

    def save_model(self, request, obj, form, change):
        """
        Automatically assign the logged-in user as the
        'created_by' when creating a new Driver.
        """
        if not obj.pk:  # Only set created_by on creation, not updates
            obj.created_by = request.user
        obj.updated_by = request.user
        obj.save()


class WorkerForm(forms.ModelForm):
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
        model = Worker
        fields = (
            "name",
            "email",
            "phone_number",
            "station_branch",
            "password1",
            "password2",
            "is_active",
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
        user.role = User.UserRoles.StationWorker
        if self.cleaned_data["password1"]:
            user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


@admin.register(Worker)
class WorkerInterface(admin.ModelAdmin):
    form = WorkerForm
    list_display = (
        "id",
        "name",
        "phone_number",
        "is_active",
    )
    search_fields = ("name", "phone_number")
    list_filter = ("is_active",)
    ordering = ("-created",)
    list_per_page = 10

    def has_delete_permission(self, request, obj=None):
        return False

    def created(self, obj):
        return obj.created

    created.admin_order_field = "created"
    created.short_description = _("Created")

    def save_model(self, request, obj, form, change):
        """
        Automatically assign the logged-in user as the
        'created_by' when creating a new Driver.
        """
        if not obj.pk:  # Only set created_by on creation, not updates
            obj.created_by = request.user
        obj.updated_by = request.user
        obj.save()


admin.site.register(
    FirebaseToken,
)


admin.site.unregister(Group)

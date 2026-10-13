import pytest
from django.contrib import admin

from apps.users.admin import CustomerSupportForm
from apps.users.models import CustomerSupport, User

pytestmark = pytest.mark.django_db


class TestCustomerSupportModel:
    def test_is_a_proxy_without_its_own_table_success(self):
        assert CustomerSupport._meta.proxy is True
        assert CustomerSupport._meta.db_table == User._meta.db_table

    def test_save_forces_the_role_success(self):
        support = CustomerSupport.objects.create(
            name="Support",
            phone_number="01700000010",
            email="support-model@example.com",
            role=User.UserRoles.Admin,
        )

        support.refresh_from_db()
        assert support.role == User.UserRoles.CustomerSupport

    def test_manager_returns_only_customer_support_success(
        self, admin_user, finance_user, customer_support_user
    ):
        assert list(CustomerSupport.objects.all()) == [customer_support_user]


class TestCustomerSupportAdmin:
    def setup_method(self):
        self.data = {
            "name": "Admin Made Support",
            "email": "admin-support@example.com",
            "phone_number": "01700000020",
            "is_active": True,
            "password1": "s3cret-pass",
            "password2": "s3cret-pass",
        }

    def test_registered_success(self):
        assert CustomerSupport in admin.site._registry

    def test_add_sets_role_and_hashes_password_success(self, rf, admin_user):
        form = CustomerSupportForm(data=self.data)
        model_admin = admin.site._registry[CustomerSupport]
        request = rf.post("/")
        request.user = admin_user

        assert form.is_valid(), form.errors
        support = form.save(commit=False)
        model_admin.save_model(request, support, form, change=False)

        support.refresh_from_db()
        assert support.role == User.UserRoles.CustomerSupport
        assert support.check_password("s3cret-pass")
        assert support.is_superuser is False
        assert support.created_by_id == admin_user.id
        assert support.updated_by_id == admin_user.id

    def test_edit_without_password_keeps_it_success(
        self, rf, admin_user, finance_user, customer_support_user
    ):
        customer_support_user.set_password("old-pass")
        customer_support_user.save()
        data = {
            **self.data,
            "phone_number": customer_support_user.phone_number,
            "email": customer_support_user.email,
            "password1": "",
            "password2": "",
        }
        form = CustomerSupportForm(data=data, instance=customer_support_user)
        model_admin = admin.site._registry[CustomerSupport]
        request = rf.post("/")
        request.user = finance_user

        assert form.is_valid(), form.errors
        model_admin.save_model(request, form.save(commit=False), form, change=True)

        customer_support_user.refresh_from_db()
        assert customer_support_user.name == "Admin Made Support"
        assert customer_support_user.check_password("old-pass")
        assert customer_support_user.created_by_id == admin_user.id
        assert customer_support_user.updated_by_id == finance_user.id

    def test_add_without_password_fail(self):
        form = CustomerSupportForm(data={**self.data, "password1": "", "password2": ""})

        assert not form.is_valid()
        assert form.non_field_errors() == ["Password is required."]

    def test_passwords_mismatch_fail(self):
        form = CustomerSupportForm(data={**self.data, "password2": "other"})

        assert not form.is_valid()
        assert form.non_field_errors() == ["Passwords don't match."]

    def test_delete_disabled_fail(self, rf, admin_user):
        request = rf.get("/")
        request.user = admin_user

        assert not admin.site._registry[CustomerSupport].has_delete_permission(request)

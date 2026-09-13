import pytest

from apps.users.models import User

pytestmark = pytest.mark.django_db


class TestCustomUserManager:

    def test_create_superuser_sets_staff_flags_and_hashes_password_success(self):
        user = User.objects.create_superuser(
            "01099999999", name="Root", password="s3cret-pass"
        )

        user.refresh_from_db()
        assert user.is_staff is True
        assert user.is_superuser is True
        assert user.name == "Root"
        assert user.phone_number == "01099999999"
        assert user.password != "s3cret-pass"
        assert user.check_password("s3cret-pass") is True

    def test_create_superuser_defaults_empty_name_to_admin_success(self):
        user = User.objects.create_superuser("01099999998", name="", password="x")

        assert user.name == "Admin"

    def test_create_superuser_without_phone_number_fail(self):
        with pytest.raises(ValueError, match="phone number must be set"):
            User.objects.create_superuser("", password="x")

        assert User.objects.count() == 0

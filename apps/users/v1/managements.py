from django.contrib.auth.models import UserManager


class CustomUserManager(UserManager):
    def create_superuser(self, phone_number, name, password=None, email=None, **extra_fields):
        extra_fields["is_staff"] = True
        extra_fields["is_superuser"] = True
        return self._create_user(phone_number, name, password, **extra_fields)

    def _create_user(self, phone_number, name, password, email=None, **extra_fields):
        if not phone_number:
            raise ValueError("The given phone number must be set")
        if not name:
            raise ValueError("The given name must be set")
        email = self.normalize_email(email)
        user = self.model(phone_number=phone_number, name=name, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

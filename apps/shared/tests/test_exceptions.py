from django.core.exceptions import PermissionDenied
from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError

from apps.shared.base_exception_class import CustomValidationError
from apps.shared.exceptions import custom_exception_handler


class TestCustomExceptionHandler:

    def test_custom_validation_error_is_returned_unchanged_success(self):
        exc = CustomValidationError("Bad input", errors=[{"field": "x"}])

        response = custom_exception_handler(exc, {})

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data == {
            "code": "validation_error",
            "message": "Bad input",
            "errors": [{"field": "x"}],
        }

    def test_validation_error_list_messages_are_flattened_success(self):
        exc = ValidationError({"name": ["This field is required."]})

        response = custom_exception_handler(exc, {})

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data == {
            "code": "validation_error",
            "message": "Validation failed",
            "errors": [{"field": "name", "message": "This field is required."}],
        }

    def test_validation_error_nested_dict_messages_are_flattened_success(self):
        exc = ValidationError({"address": {"city": "Required.", "street": "Too long."}})

        response = custom_exception_handler(exc, {})

        assert response.data["errors"] == [
            {"field": "address", "message": "Required."},
            {"field": "address", "message": "Too long."},
        ]

    def test_django_permission_denied_is_formatted_success(self):
        exc = PermissionDenied("Not allowed.")

        response = custom_exception_handler(exc, {})

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data == {
            "code": "permission_denied",
            "message": "Not allowed.",
            "errors": [],
        }

    def test_other_api_exceptions_keep_default_body_success(self):
        response = custom_exception_handler(NotFound(), {})

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data == {"detail": "Not found."}

    def test_non_api_exception_returns_none_success(self):
        assert custom_exception_handler(ValueError("boom"), {}) is None

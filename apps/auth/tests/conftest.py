from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def disable_django_template_context_copy():
    """Django's test client copies template context; that copy fails on Python 3.14."""
    with patch("django.test.client.copy", side_effect=lambda value: value):
        yield

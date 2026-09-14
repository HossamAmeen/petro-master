import pytest

from apps.users.tests.helpers import workers_detail_url

pytestmark = [pytest.mark.api, pytest.mark.django_db]


class TestWorkerUpdate:

    def test_full_update_raises_type_error_fail(
        self, auth_client, admin_user, station_worker
    ):
        """Documents actual (buggy) behavior: `WorkerViewSet` allows PUT, but
        `get_serializer_class` only handles GET, POST and PATCH and returns `None`
        otherwise, so PUT crashes with an unhandled `TypeError` (HTTP 500)."""
        with pytest.raises(TypeError, match="not callable"):
            auth_client(admin_user).put(
                workers_detail_url(station_worker.id),
                {"name": "Replaced Worker"},
                format="json",
            )

        station_worker.refresh_from_db()
        assert station_worker.name != "Replaced Worker"

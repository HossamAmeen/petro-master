# Petro Master Backend Guide

## Testing

- Use `pytest` with `pytest-django`; run the suite with `venv/bin/python -m pytest`.
- Keep shared API clients, JWT-claim helpers, and cross-domain fixtures in the root `conftest.py`.
- Keep domain-specific fixtures in that app's test `conftest.py`.
- Reuse factories from `apps/companies/factories.py`; add a factory before repeating model setup in tests.
- API tests must cover successful requests and relevant authentication, authorization, validation, and ownership boundaries.
- Exercise application code against the test database. Mock only network-bound third-party adapters, such as Firebase Cloud Messaging and email/SMS providers.

## API conventions

- Tests target the versioned `/api/v1/` endpoints and use DRF's `APIClient`.
- Set `company_id` or `station_id` JWT claims through the shared `auth_client` fixture for scoped endpoints.

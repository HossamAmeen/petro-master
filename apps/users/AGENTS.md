# Users App — Agent Guide

## Purpose

Identity and access management for the entire Petro Master platform. All user types, roles, permissions, and authentication flows are defined here.

## Architecture

### Model Hierarchy

```
User (AbstractUser + TimeStampedModel)
├── CompanyUser          → FK to Company
├── StationOwner         → FK to Station
├── Worker               → FK to StationBranch
├── Supervisor           → M2M to District, credit_limit
└── Agent                → M2M to District, FK to Supervisor, credit_limit

Junction / Support Models:
├── CompanyBranchManager  → CompanyUser ↔ CompanyBranch
├── StationBranchManager  → StationOwner ↔ StationBranch
└── FirebaseToken         → User ↔ FCM token
```

### Key Design Decisions

- **Multi-table inheritance**: Each user type is a separate model inheriting from `User`. This allows type-specific fields (e.g., `station` on `StationOwner`) while sharing the base auth system.
- **Role field on User**: A `CharField` with `TextChoices` that determines permissions. Set automatically in `save()` for `Worker`, `Supervisor`, and `Agent`.
- **JWT claims for scoping**: `company_id` and `station_id` are embedded in JWT tokens and extracted by `CompanyMiddleware` to scope queries without extra DB hits.
- **Phone number as username**: `USERNAME_FIELD = "phone_number"`. Email is optional and defaults to `{phone_number}@petro.com`.

## File Map

| File | Purpose |
|---|---|
| `models.py` | User hierarchy, FirebaseToken, junction models |
| `middleware.py` | `CompanyMiddleware` — extracts company_id/station_id from JWT |
| `admin.py` | Custom admin for all user types (delete disabled) |
| `v1/urls.py` | DRF router registrations |
| `v1/managements.py` | `CustomUserManager` — phone_number-based user creation |
| `v1/filters.py` | `UserFilter`, `CompanyBranchManagerFilter`, `StationOwnerFilter`, `StationBranchManagerFilter` |
| `v1/views/users_view.py` | `UserViewSet` (dashboard users), `FirebaseTokenViewSet` |
| `v1/views/company_users_view.py` | `CompanyOwnerViewSet`, `CompanyBranchManagerViewSet` |
| `v1/views/station_users_view.py` | `StationOwnerViewSet`, `StationBranchManagerViewSet`, `WorkerViewSet` |
| `v1/views/agent_views.py` | `SupervisorViewSet` |
| `v1/views/statistics_view.py` | `StatisticsViewSet` — dashboard counts |
| `v1/serializers/user_serializers.py` | `CreateUserSerializer`, `ListUserSerializer`, `FirebaseTokenSerializer` |
| `v1/serializers/company_user_serializer.py` | Company owner/manager serializers |
| `v1/serializers/station_serializer.py` | Station owner/manager/worker serializers |
| `v1/serializers/agent_serializer.py` | Supervisor serializers |
| `test/conftest.py` | User fixtures (admin, finance, support, driver, supervisor, agent) |
| `test/test_users.py` | Dashboard user CRUD tests |
| `test/test_station.py` | Station owner & branch manager tests |
| `test/test_worker.py` | Worker scoping & permission tests |

## API Endpoints

All under `/api/v1/users/`:

| Endpoint | ViewSet | Permission |
|---|---|---|
| `/users/` | `UserViewSet` | Admin |
| `/company-owners/` | `CompanyOwnerViewSet` | Dashboard |
| `/company-branch-managers/` | `CompanyBranchManagerViewSet` | Company or Dashboard |
| `/station-owners/` | `StationOwnerViewSet` | Station or Dashboard |
| `/station-branch-managers/` | `StationBranchManagerViewSet` | Station or Dashboard |
| `/workers/` | `WorkerViewSet` | Station or Dashboard |
| `/supervisors/` | `SupervisorViewSet` | Admin |
| `/firebase-tokens/` | `FirebaseTokenViewSet` | Authenticated |

## Permission System

Permissions are defined in `apps/shared/permissions.py` and use role-based checks:

```python
AdminPermission        → role == "admin"
DashboardPermission    → role in ["admin", "finance", "customer_support"]
CompanyPermission      → role in ["company_owner", "company_branch_manager"]
StationPermission      → role in ["station_owner", "station_branch_manager", "station_worker"]
EitherPermission([A, B]) → A or B
```

## Data Scoping

| User Role | Scoping Mechanism |
|---|---|
| Company Owner | `request.company_id` from JWT |
| Company Branch Manager | `request.company_id` from JWT |
| Station Owner | `request.station_id` from JWT |
| Station Branch Manager | `station_branch__managers__user` reverse relation |
| Dashboard roles | No scoping (see all) |

## Common Patterns

### Creating a new user type
1. Add role to `User.UserRoles`
2. Create model inheriting from `User` (or `AbstractBaseModel` for junctions)
3. Override `save()` to auto-set role if needed
4. Create serializer with `make_password()` for password hashing
5. Create ViewSet with appropriate permissions
6. Register in `v1/urls.py`
7. Add admin class in `admin.py`

### Password handling
- Always use `make_password()` before saving
- Always validate `confirm_password` matches
- Never return password in API responses (`write_only=True` or `to_representation` pop)

### Email defaults
When email is not provided, it defaults to `{phone_number}@petro.com`.

### Audit fields
Use `InjectUserMixin` to auto-set `created_by` and `updated_by`:
```python
class MyViewSet(InjectUserMixin, viewsets.ModelViewSet):
    ...
```

## Testing

```bash
# Run all users tests
venv/bin/python -m pytest apps/users/test/ -v

# Run specific test file
venv/bin/python -m pytest apps/users/test/test_worker.py -v
```

### Test fixtures
- Root `conftest.py`: `api_client`, `auth_client`, `geo_data`, `mock_firebase_notifications`
- `apps/users/test/conftest.py`: `admin_user`, `finance_user`, `customer_support_user`, `driver_user`, `supervisor`, `agent`

### Auth in tests
```python
client = auth_client(user)                    # Basic auth
client = auth_client(user, station.id)        # With station_id claim
client = auth_client(user, company_id=co.id)  # With company_id claim
```

## Dependencies

- `apps/shared/constants.py` — Role groups (DASHBOARD_ROLES, COMPANY_ROLES, STATION_ROLES)
- `apps/shared/permissions.py` — Permission classes
- `apps/shared/mixins/inject_user_mixins.py` — InjectUserMixin
- `apps/shared/base_exception_class.py` — CustomValidationError
- `apps/companies/models/` — Company, CompanyBranch
- `apps/stations/models/` — Station, StationBranch
- `apps/geo/models/` — District

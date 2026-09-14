# Users App — Workflow Documentation

## Overview

The `apps/users` app is the identity and access management core of Petro Master. It defines the user model hierarchy, role-based access control, and all user-related API endpoints. Every other app in the system depends on this module for authentication and authorization.

---

## Model Hierarchy

```
AbstractUser (Django)
  └── User (base model)
        ├── CompanyUser          → linked to a Company
        ├── StationOwner         → linked to a Station
        ├── Worker               → linked to a StationBranch
        ├── Supervisor           → linked to Districts (M2M)
        └── Agent                → linked to Districts (M2M) + Supervisor (FK)

Standalone models:
  ├── FirebaseToken            → FCM push notification tokens per user
  ├── CompanyBranchManager     → links CompanyUser ↔ CompanyBranch
  └── StationBranchManager     → links StationOwner ↔ StationBranch
```

### User Roles

| Role | Description | Scope |
|---|---|---|
| `admin` | Platform administrator | Dashboard |
| `finance` | Finance team member | Dashboard |
| `customer_support` | Support team member | Dashboard |
| `company_owner` | Owns a company | Company-scoped |
| `company_branch_manager` | Manages company branches | Company-scoped |
| `driver` | Company driver | Company-scoped |
| `station_owner` | Owns a station | Station-scoped |
| `station_branch_manager` | Manages station branches | Station-scoped |
| `station_worker` | Works at a station branch | Station-scoped |
| `supervisor` | Field supervisor | District-scoped |
| `agent` | Field agent under a supervisor | District-scoped |

### Role Groups (from `apps/shared/constants.py`)

- **DASHBOARD_ROLES**: `admin`, `finance`, `customer_support`
- **COMPANY_ROLES**: `company_owner`, `company_branch_manager`
- **STATION_ROLES**: `station_owner`, `station_branch_manager`, `station_worker`
- **STATION_ADMIN_ROLES**: `station_owner`, `station_branch_manager`

---

## Authentication Flow

```
Client Request
  │
  ├─→ JWT Access Token (phone_number as USERNAME_FIELD)
  │     │
  │     ├─→ CompanyMiddleware extracts company_id / station_id from JWT claims
  │     │     → sets request.company_id
  │     │     → sets request.station_id
  │     │
  │     └─→ DRF Permission Classes check user.role
  │           │
  │           ├─→ AdminPermission        → role == admin
  │           ├─→ DashboardPermission    → role in DASHBOARD_ROLES
  │           ├─→ CompanyPermission      → role in COMPANY_ROLES
  │           ├─→ StationPermission      → role in STATION_ROLES
  │           └─→ EitherPermission       → any of the above
  │
  └─→ ViewSet processes request with role-scoped queryset
```

### Password Reset Flow

```
User requests reset
  → User.create_password_reset_token() generates UUID token
  → Token stored with timestamp (24-hour expiry)
  → User submits token + new password
  → User.is_valid_password_reset_token(token) validates
  → Password updated
```

---

## API Endpoints

All endpoints are under `/api/v1/users/`.

### Dashboard Users (`/users/`)

| Method | Endpoint | Permission | Description |
|---|---|---|---|
| GET | `/users/` | Admin | List dashboard users (admin, finance, support) |
| POST | `/users/` | Admin | Create dashboard user |
| GET | `/users/{id}/` | Admin | Retrieve user |
| PATCH | `/users/{id}/` | Admin | Update user |
| DELETE | `/users/{id}/` | Admin | Delete user |

**Query params**: `role`, `is_active` (via `UserFilter`)

### Company Owners (`/company-owners/`)

| Method | Endpoint | Permission | Description |
|---|---|---|---|
| GET | `/company-owners/` | Dashboard | List company owners |
| POST | `/company-owners/` | Dashboard | Create company owner |
| GET | `/company-owners/{id}/` | Dashboard | Retrieve |
| PATCH | `/company-owners/{id}/` | Dashboard | Update |
| DELETE | `/company-owners/{id}/` | Dashboard | Delete |

**Query params**: `search` (name, phone_number, email)

### Company Branch Managers (`/company-branch-managers/`)

| Method | Endpoint | Permission | Description |
|---|---|---|---|
| GET | `/company-branch-managers/` | Company or Dashboard | List branch managers |
| POST | `/company-branch-managers/` | Company or Dashboard | Create branch manager |
| GET | `/company-branch-managers/{id}/` | Company or Dashboard | Retrieve (includes branches) |
| PATCH | `/company-branch-managers/{id}/` | Company or Dashboard | Update |
| DELETE | `/company-branch-managers/{id}/` | Company or Dashboard | Delete |

**Scoping**: Company owners see only their own company's managers.

### Station Owners (`/station-owners/`)

| Method | Endpoint | Permission | Description |
|---|---|---|---|
| GET | `/station-owners/` | Station or Dashboard | List station owners |
| POST | `/station-owners/` | Station or Dashboard | Create station owner |
| GET | `/station-owners/{id}/` | Station or Dashboard | Retrieve |
| PATCH | `/station-owners/{id}/` | Station or Dashboard | Update |
| DELETE | `/station-owners/{id}/` | Station or Dashboard | Delete |

### Station Branch Managers (`/station-branch-managers/`)

| Method | Endpoint | Permission | Description |
|---|---|---|---|
| GET | `/station-branch-managers/` | Station or Dashboard | List branch managers |
| POST | `/station-branch-managers/` | Station or Dashboard | Create branch manager |
| GET | `/station-branch-managers/{id}/` | Station or Dashboard | Retrieve |
| PATCH | `/station-branch-managers/{id}/` | Station or Dashboard | Update |
| DELETE | `/station-branch-managers/{id}/` | Station or Dashboard | Delete |

**Scoping**: Station owners see only their own station's managers.

### Workers (`/workers/`)

| Method | Endpoint | Permission | Description |
|---|---|---|---|
| GET | `/workers/` | Station or Dashboard | List workers |
| POST | `/workers/` | Station or Dashboard | Create worker |
| GET | `/workers/{id}/` | Station or Dashboard | Retrieve |
| PATCH | `/workers/{id}/` | Station or Dashboard | Update |
| DELETE | `/workers/{id}/` | Station or Dashboard | Delete |

**Scoping**:
- Station owners → workers in their station's branches
- Branch managers → workers in branches they manage
- Dashboard → all workers

### Supervisors (`/supervisors/`)

| Method | Endpoint | Permission | Description |
|---|---|---|---|
| GET | `/supervisors/` | Admin | List supervisors |
| POST | `/supervisors/` | Admin | Create supervisor |
| GET | `/supervisors/{id}/` | Admin | Retrieve |
| PATCH | `/supervisors/{id}/` | Admin | Update |
| DELETE | `/supervisors/{id}/` | Admin | Delete |

### Firebase Tokens (`/firebase-tokens/`)

| Method | Endpoint | Permission | Description |
|---|---|---|---|
| POST | `/firebase-tokens/` | Authenticated | Register FCM token |
| DELETE | `/firebase-tokens/delete-by-token/` | Authenticated | Delete FCM token by value |

---

## Data Scoping Rules

### Company-Scoped Queries
```
CompanyOwner requests → filtered by request.company_id (from JWT)
Dashboard requests   → unfiltered (see all)
```

### Station-Scoped Queries
```
StationOwner requests        → filtered by request.station_id (from JWT)
StationBranchManager requests → filtered by managed branches
Dashboard requests            → unfiltered (see all)
```

### InjectUserMixin
Used by `UserViewSet`, `CompanyBranchManagerViewSet`, and `SupervisorViewSet` to automatically set `created_by` and `updated_by` on create/update operations.

---

## Serializer Patterns

### Create vs. List Serializers
Each viewset uses different serializers for read vs. write:

| ViewSet | List/Retrieve | Create/Update |
|---|---|---|
| `UserViewSet` | `ListUserSerializer` | `CreateUserSerializer` |
| `CompanyOwnerViewSet` | `ListCompanyOwnerSerializer` | `CreateCompanyOwnerSerializer` |
| `CompanyBranchManagerViewSet` | `ListCompanyBranchManagerSerializer` / `RetrieveCompanyBranchManagerSerializer` | `CreateCompanyOwnerSerializer` / `CompanyBranchManagerSerializer` |
| `StationOwnerViewSet` | `ListStationOwnerSerializer` | `StationOwnerSerializer` |
| `StationBranchManagerViewSet` | `ListStationBranchManagerSerializer` | `StationBranchManagerCreationSerializer` |
| `WorkerViewSet` | `ListWorkerSerializer` | `CreateWorkerSerializer` / `UpdateWorkerSerializer` |
| `SupervisorViewSet` | `ListSupervisorSerializer` | `CreateSupervisorSerializer` |

### Common Patterns
- Passwords are hashed with `make_password()` before saving
- `confirm_password` is validated but never stored
- Default email: `{phone_number}@petro.com` when not provided
- `created_by` / `updated_by` are set via `InjectUserMixin` or `perform_create`

---

## Middleware

### CompanyMiddleware
Extracts `company_id` and `station_id` from JWT access token claims and attaches them to the request object. This enables scoped queries without additional database lookups.

```python
request.company_id  # Set from JWT claim
request.station_id  # Set from JWT claim
```

---

## Admin Interface

The Django admin is customized for all user types:
- **User**: Dashboard users only (filtered by `DASHBOARD_ROLES`)
- **CompanyUser**: Company owners and branch managers
- **StationOwner**: Station owners and branch managers
- **Worker**: Station workers
- **Supervisor**: Field supervisors
- **CompanyBranchManager** / **StationBranchManager**: Junction table management
- **FirebaseToken**: FCM token management

All admin classes disable delete permission (`has_delete_permission` returns `False`).

---

## Testing

### Test Structure
```
apps/users/test/
  ├── conftest.py          → User fixtures (admin, finance, support, driver, supervisor, agent)
  ├── test_users.py        → Dashboard user CRUD tests
  ├── test_station.py      → Station owner & branch manager tests
  └── test_worker.py       → Worker scoping & permission tests
```

### Key Fixtures (from root `conftest.py`)
- `api_client` → DRF `APIClient`
- `auth_client(user, station_id, company_id)` → Authenticated client with JWT claims
- `geo_data` → Country, City, District fixtures
- `mock_firebase_notifications` → Auto-mocks FCM calls

### Running Tests
```bash
venv/bin/python -m pytest apps/users/test/ -v
```

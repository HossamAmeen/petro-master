from apps.users.models import User

COMPANY_ROLES = [
    User.UserRoles.CompanyOwner,
    User.UserRoles.CompanyBranchManager,
]

STATION_ROLES = [
    User.UserRoles.StationOwner,
    User.UserRoles.StationBranchManager,
]

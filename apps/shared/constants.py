from apps.stations.models.service_models import Service
from apps.users.models import User

COMPANY_ROLES = [
    User.UserRoles.CompanyOwner,
    User.UserRoles.CompanyBranchManager,
]

STATION_ROLES = [
    User.UserRoles.StationOwner,
    User.UserRoles.StationBranchManager,
    User.UserRoles.StationWorker,
]


SERVICE_UNIT_CHOICES = {
    Service.ServiceUnit.OTHER: "اخري",
    Service.ServiceUnit.LITRE: "لتر",
    Service.ServiceUnit.UNIT: "وحدة",
}

from apps.companies.models.company_models import Car
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


COLOR_CHOICES_HEX = {
    Car.PlateColor.RED: "#FF0000",
    Car.PlateColor.BLUE: "#0000FF",
    Car.PlateColor.ORANGE: "#FFA500",
    Car.PlateColor.YELLOW: "#FFFF00",
    Car.PlateColor.GREEN: "#008000",
    Car.PlateColor.GOLD: "#FFD700",
}

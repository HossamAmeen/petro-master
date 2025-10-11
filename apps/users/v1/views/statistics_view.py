from rest_framework import mixins, status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounting.models import KhaznaTransaction
from apps.companies.models.company_models import Company, CompanyBranch
from apps.stations.models.stations_models import Station, StationBranch
from apps.users.models import User


class StatisticsViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request):
        """
        Get counts for common tables
        """
        try:
            stats = {
                "users": {
                    "total_users": User.objects.count(),
                    "admin_users": User.objects.filter(
                        role=User.UserRoles.Admin
                    ).count(),
                    "company_owners": User.objects.filter(
                        role=User.UserRoles.CompanyOwner
                    ).count(),
                    "station_owners": User.objects.filter(
                        role=User.UserRoles.StationOwner
                    ).count(),
                    "station_workers": User.objects.filter(
                        role=User.UserRoles.StationWorker
                    ).count(),
                },
                "companies": {
                    "total_companies": Company.objects.count(),
                    "active_companies": Company.objects.filter(is_active=True).count(),
                },
                "company_branches": {
                    "total_branches": CompanyBranch.objects.count(),
                },
                "stations": {
                    "total_stations": Station.objects.count(),
                    "active_stations": Station.objects.filter(is_active=True).count(),
                },
                "station_branches": {
                    "total_branches": StationBranch.objects.count(),
                    "active_branches": StationBranch.objects.filter(
                        is_active=True
                    ).count(),
                },
                "transactions": {
                    "total_transactions": KhaznaTransaction.objects.count(),
                },
            }

            return Response(
                {"status": "success", "data": stats}, status=status.HTTP_200_OK
            )

        except Exception as e:
            return Response(
                {"status": "error", "message": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

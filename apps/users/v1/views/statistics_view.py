from django.db.models import Sum
from rest_framework import mixins, status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounting.models import (
    CompanyKhaznaTransaction,
    KhaznaTransaction,
    StationKhaznaTransaction,
)
from apps.companies.models.company_cash_models import CompanyCashRequest
from apps.companies.models.company_models import Car, Company, CompanyBranch, Driver
from apps.companies.models.operation_model import CarOperation
from apps.geo.models import City, Country, District
from apps.shared.helpers import today
from apps.stations.models.service_models import Service
from apps.stations.models.stations_models import Station, StationBranch
from apps.users.models import User


class StatisticsViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request):
        """
        Get counts for common tables
        """
        try:
            data = {
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
                "geo": {
                    "total_countries": Country.objects.count(),
                    "total_cities": City.objects.count(),
                    "total_districts": District.objects.count(),
                },
                "companies": {
                    "total_companies": Company.objects.count(),
                    "active_companies": Company.objects.filter(is_active=True).count(),
                    "total_cars": Car.objects.count(),
                    "total_drivers": Driver.objects.count(),
                    "total_cash_requests": CompanyCashRequest.objects.filter(
                        status=CompanyCashRequest.Status.APPROVED
                    ).count(),
                    "total_cash_requests_today": CompanyCashRequest.objects.filter(
                        status=CompanyCashRequest.Status.APPROVED, created__date=today()
                    ).count(),
                    "total_operations": CarOperation.objects.filter(
                        status=CarOperation.OperationStatus.COMPLETED
                    ).count(),
                    "total_today_operations": CarOperation.objects.filter(
                        status=CarOperation.OperationStatus.COMPLETED,
                        created__date=today(),
                    ).count(),
                    "total_profit": CarOperation.objects.filter(
                        status=CompanyKhaznaTransaction.TransactionStatus.APPROVED
                    ).aggregate(Sum("profits"))["profits__sum"]
                    or 0,
                    "total_profit_today": CarOperation.objects.filter(
                        status=CompanyKhaznaTransaction.TransactionStatus.APPROVED,
                        created__date=today(),
                    ).aggregate(Sum("profits"))["profits__sum"]
                    or 0,
                },
                "company_branches": {
                    "total_branches": CompanyBranch.objects.count(),
                },
                "stations": {
                    "total_stations": Station.objects.count(),
                },
                "station_branches": {
                    "total_branches": StationBranch.objects.count(),
                },
                "transactions": {
                    "total_transactions": KhaznaTransaction.objects.count(),
                    "total_today_transactions": KhaznaTransaction.objects.filter(
                        created__date=today()
                    ).count(),
                    "total_incoming_today_transactions": KhaznaTransaction.objects.filter(
                        is_incoming=True, created__date=today()
                    ).count(),
                    "total_incoming_transactions": KhaznaTransaction.objects.filter(
                        is_incoming=True
                    ).count(),
                    "total_outgoing_transactions": KhaznaTransaction.objects.filter(
                        is_incoming=False
                    ).count(),
                    "total_outgoing_today_transactions": KhaznaTransaction.objects.filter(
                        is_incoming=False, created__date=today()
                    ).count(),
                    "total_approved_transactions": KhaznaTransaction.objects.filter(
                        status=KhaznaTransaction.TransactionStatus.APPROVED
                    ).count(),
                    "total_company_transactions": CompanyKhaznaTransaction.objects.count(),
                    "total_station_transactions": StationKhaznaTransaction.objects.count(),
                },
                "services": {
                    "total_services": Service.objects.count(),
                },
            }

            return Response(data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"status": "error", "message": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

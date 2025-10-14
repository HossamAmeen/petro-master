from django.db.models import Sum
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

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
from apps.shared.permissions import AdminPermission
from apps.stations.models.service_models import Service
from apps.stations.models.stations_models import Station, StationBranch
from apps.users.models import User
from configrations.serializers import (
    ConfigrationsSerializer,
    ContactUsSerializer,
    SliderSerializer,
)

from .models import ConfigrationsModel, Slider


class ConfigrationsView(APIView):
    permission_classes = []
    authentication_classes = []

    @extend_schema(
        responses={
            200: {
                "type": "object",
                "properties": {
                    "term_conditions": {"type": "string"},
                    "privacy_policy": {"type": "string"},
                    "about_us": {"type": "string"},
                    "faq": {"type": "string"},
                },
            }
        }
    )
    def get(self, request):
        configrations = ConfigrationsModel.objects.first()
        if not configrations:
            return Response(
                {"term_conditions": "", "privacy_policy": "", "about_us": "", "faq": ""}
            )
        serializer = ConfigrationsSerializer(configrations)
        return Response(serializer.data)


class SliderView(ListAPIView):
    queryset = Slider.objects.order_by("order")
    serializer_class = SliderSerializer
    permission_classes = []
    authentication_classes = []


class StatisticsViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated, AdminPermission]

    def list(self, request):
        data = {
            "users": {
                "total_users": User.objects.count(),
                "admin_users": User.objects.filter(role=User.UserRoles.Admin).count(),
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
                    status=CarOperation.OperationStatus.COMPLETED, created__date=today()
                ).count(),
                "total_profit": CarOperation.objects.filter(
                    status=CompanyKhaznaTransaction.TransactionStatus.APPROVED
                ).aggregate(Sum("profits"))["profits__sum"],
                "total_profit_today": CarOperation.objects.filter(
                    status=CompanyKhaznaTransaction.TransactionStatus.APPROVED,
                    created__date=today(),
                ).aggregate(Sum("profits"))["profits__sum"],
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


@extend_schema(
    request=ContactUsSerializer,
    responses={
        200: OpenApiResponse(
            response={
                "type": "object",
                "properties": {"message": {"type": "string"}},
                "required": ["message"],
            },
            description="Contact us message sent successfully.",
        )
    },
)
class ContactUsView(APIView):
    def post(self, request):
        serializer = ContactUsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(status=status.HTTP_200_OK)

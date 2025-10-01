import os

from django.conf import settings
from django.http import FileResponse, Http404
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiResponse,
    OpenApiTypes,
    extend_schema,
)
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter
from rest_framework.response import Response

from apps.companies.api.v1.filters import CarOperationFilter
from apps.companies.api.v1.serializers.car_operation_serializer import (
    ListCarOperationSerializer,
    SingleCarOperationSerializer,
)
from apps.companies.helper import export_car_operations, get_car_operations_data
from apps.companies.models.company_models import CompanyBranch
from apps.companies.models.operation_model import CarOperation
from apps.notifications.models import Notification
from apps.shared.base_exception_class import CustomValidationError
from apps.shared.permissions import (
    CompanyPermission,
    DashboardPermission,
    StationPermission,
    StationWorkerPermission,
)
from apps.stations.models.service_models import Service
from apps.users.models import User


class CarOperationViewSet(viewsets.ModelViewSet):
    queryset = CarOperation.objects.select_related(
        "car",
        "driver",
        "station_branch",
        "worker__station_branch__district__city",
        "service",
    ).order_by("-id")
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_class = CarOperationFilter
    serializer_class = ListCarOperationSerializer
    search_fields = [
        "code",
        "car__code",
        "driver__name",
        "station_branch__name",
        "worker__name",
    ]

    def get_permissions(self):
        if self.action == "export":
            return [CompanyPermission()]
        if self.action == "download_excel":
            return [CompanyPermission()]
        if self.action == "list":
            return [CompanyPermission(), DashboardPermission(), StationPermission()]
        if self.action == "retrieve":
            return [CompanyPermission(), DashboardPermission(), StationPermission()]
        if self.action == "create":
            return [CompanyPermission(), DashboardPermission()]
        if self.action == "partial_update":
            return [
                CompanyPermission(),
                DashboardPermission(),
                StationWorkerPermission(),
            ]

    def get_serializer_class(self):
        if self.action == "list":
            return ListCarOperationSerializer
        if self.action == "retrieve":
            return SingleCarOperationSerializer
        return ListCarOperationSerializer

    def get_queryset(self):
        if self.request.user.role == User.UserRoles.CompanyOwner:
            return self.queryset.filter(
                car__branch__company=self.request.company_id,
                service__type__in=[
                    Service.ServiceType.PETROL,
                    Service.ServiceType.DIESEL,
                ],
            )
        if self.request.user.role == User.UserRoles.CompanyBranchManager:
            return self.queryset.filter(
                car__branch__managers__user=self.request.user,
                service__type__in=[
                    Service.ServiceType.PETROL,
                    Service.ServiceType.DIESEL,
                ],
            )
        return self.queryset.distinct()

    def destroy(self, request, *args, **kwargs):
        raise CustomValidationError("disallowed delete method")

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="car",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Filter by car code",
            ),
            OpenApiParameter(
                name="date_from",
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                description="Filter operations from this date (YYYY-MM-DD)",
            ),
            OpenApiParameter(
                name="date_to",
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                description="Filter operations to this date (YYYY-MM-DD)",
            ),
        ],
        responses={
            200: OpenApiResponse(
                response={
                    "type": "object",
                    "properties": {
                        "message": {"type": "string"},
                        "download_url": {"type": "string"},
                    },
                },
                description="Current car balance after the update.",
            )
        },
    )
    @action(detail=False, methods=["get"], url_path="export")
    def export(self, request, *args, **kwargs):
        date_from = request.query_params.get("date_from")
        date_to = request.query_params.get("date_to")

        branches = []
        if request.user.role == User.UserRoles.CompanyOwner:
            branches = CompanyBranch.objects.filter(company_id=request.company_id)
        elif request.user.role == User.UserRoles.CompanyBranchManager:
            branches = CompanyBranch.objects.filter(
                managers__user=request.user, company_id=request.company_id
            )
        branches = branches.values_list("id", flat=True)
        branches = set(branches)
        queryset = get_car_operations_data(
            company_id=request.company_id,
            branches=branches,
            car=request.query_params.get("car"),
            date_from=date_from,
            date_to=date_to,
        )

        error_message = "لا توجد بيانات للاستخراج"
        if date_from:
            error_message = "لا توجد بيانات للاستخراج من تاريخ {}".format(date_from)
        if date_to:
            error_message = "لا توجد بيانات للاستخراج ل {}".format(date_to)

        if not queryset:
            raise CustomValidationError(
                message=error_message, status_code=status.HTTP_400_BAD_REQUEST
            )

        filename = export_car_operations(
            company_id=request.company_id, branches=branches
        )

        # Create download URL
        base_url = request.build_absolute_uri("/")[:-1]
        download_url = f"{base_url}/api/v1/companies/car-operations/download-excel/?file={filename}"

        Notification.objects.create(
            user=request.user,
            title="يتم الان استخراج العمليات",
            description="يتم الان استخراج العمليات وسوف يتم ارسال اليك اشعار لك لتحميل الملف بعد الانتهاء",
            type=Notification.NotificationType.GENERAL,
            url=download_url,  # Store the download URL
        )

        # Return both message and download URL
        return Response(
            {
                "message": "يتم الان استخراج العمليات وسوف يتم ارسال اليك اشعار لك لتحميل الملف بعد الانتهاء",
                "download_url": download_url,
            }
        )

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="file",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Filename to download",
                required=True,
            )
        ],
        responses={200: OpenApiTypes.BINARY, 404: OpenApiTypes.OBJECT},
        description="Download Excel file by filename",
    )
    @action(detail=False, methods=["get"], url_path="download-excel")
    def download_excel(self, request):
        filename = request.GET.get("file")
        if not filename:
            raise Http404("File not specified")

        filepath = os.path.join(settings.MEDIA_ROOT, "excel_exports", filename)

        if not os.path.exists(filepath):
            raise Http404("File not found")

        response = FileResponse(open(filepath, "rb"))
        response["Content-Disposition"] = f'attachment; filename="{filename}"'  # noqa
        return response

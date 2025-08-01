import os

from django.conf import settings
from django.http import FileResponse, Http404
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import OpenApiParameter, OpenApiTypes, extend_schema
from openpyxl import Workbook
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter
from rest_framework.response import Response

from apps.companies.api.v1.filters import CarOperationFilter
from apps.companies.api.v1.serializers.car_operation_serializer import (
    ListCarOperationSerializer,
    SingleCarOperationSerializer,
)
from apps.companies.models.operation_model import CarOperation
from apps.notifications.models import Notification
from apps.shared.base_exception_class import CustomValidationError
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
        return self.queryset.filter(car__branch__company=self.request.company_id)

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
    )
    @action(detail=False, methods=["get"], url_path="export")
    def export(self, request, *args, **kwargs):

        queryset = (
            CarOperation.objects.filter(car__branch__company=request.company_id)
            .select_related("car", "driver", "station_branch", "worker", "service")
            .order_by("-id")
        )
        if request.query_params.get("car"):
            queryset = queryset.filter(car_id=request.query_params.get("car"))
        date_from = request.query_params.get("date_from")
        if date_from:
            try:
                date_from = timezone.localtime().strptime(date_from, "%Y-%m-%d").date()
                queryset = queryset.filter(start_time__date__gte=date_from)
            except ValueError:
                raise CustomValidationError(
                    message="Invalid date from format",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )
        date_to = request.query_params.get("date_to")
        if date_to:
            try:
                date_to = timezone.localtime().strptime(date_to, "%Y-%m-%d").date()
                queryset = queryset.filter(start_time__date__lte=date_to)
            except ValueError:
                raise CustomValidationError(
                    message="Invalid date to format",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

        queryset = queryset[:100]
        data = ListCarOperationSerializer(queryset, many=True).data

        if not data:
            raise CustomValidationError(
                message="No data to export", status_code=status.HTTP_400_BAD_REQUEST
            )

        # Create the Excel workbook and sheet
        wb = Workbook()
        ws = wb.active
        ws.title = "Data Export"

        # Write headers (first row)
        headers = list(data[0].keys())
        cleaned_headers = [str(header) for header in headers]
        ws.append(cleaned_headers)

        # Write data rows
        for row in data:
            cleaned_row = []
            for value in row.values():
                if value is None:
                    cleaned_value = ""
                elif isinstance(value, (dict, list)):
                    cleaned_value = str(value)
                else:
                    cleaned_value = str(value)
                cleaned_row.append(cleaned_value)
            ws.append(cleaned_row)

        # Generate filename with timestamp
        timestamp = timezone.localtime().strftime("%Y%m%d_%H%M%S")
        filename = f"export_{timestamp}.xlsx"
        excel_dir = os.path.join(settings.MEDIA_ROOT, "excel_exports")
        os.makedirs(excel_dir, exist_ok=True)
        filepath = os.path.join(excel_dir, filename)

        # Save workbook to media folder
        wb.save(filepath)

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

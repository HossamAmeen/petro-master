from django.db.models import Count, Q
from rest_framework import viewsets
from rest_framework.views import APIView, Response

from apps.stations.models.stations_models import Station, StationBranch
from apps.stations.v1.serializers import ListStationSerializer
from apps.users.models import User


class StationViewSet(viewsets.ModelViewSet):
    queryset = Station.objects.prefetch_related("station_services").order_by("-id")
    serializer_class = ListStationSerializer


class StationHomeAPIView(APIView):
    def get(self, request):

        if request.user.role == User.UserRoles.StationOwner:
            station_branches_id = StationBranch.objects.filter(
                station_id=request.station_id
            ).values_list("id", flat=True)

        if request.user.role == User.UserRoles.StationBranchManager:
            station_branches_id = StationBranch.objects.filter(
                managers__user=request.user
            ).values_list("id", flat=True)

        branches_filter = Q(branches__id__in=station_branches_id)

        station = (
            Station.objects.filter(id=request.station_id)
            .annotate(
                workers_count=Count(
                    "branches__workers", distinct=True, filter=branches_filter
                ),
            )
            .first()
        )

        if request.user.role == User.UserRoles.StationOwner:
            base_balance = station.balance
        if request.user.role == User.UserRoles.StationBranchManager:
            base_balance = 0

        response_data = {
            "id": station.id,
            "name": station.name,
            "address": station.address,
            "balance": base_balance,
            "workers_count": station.workers_count,
        }
        return Response(response_data)

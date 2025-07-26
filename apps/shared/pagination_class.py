from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response


class CustomLimitOffsetPagination(LimitOffsetPagination):
    limit_query_param = "limit"
    offset_query_param = "offset"
    default_limit = 10

    def paginate_queryset(self, queryset, request, view=None):
        self.request = request

        if request.query_params.get("no_paginate", "").lower() == "true":
            return queryset
        return super().paginate_queryset(queryset, request, view)

    def get_paginated_response(self, data):
        if self.request.query_params.get("no_paginate", "").lower() == "true":
            return Response({"results": data})
        return super().get_paginated_response(data)

from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from rest_framework_simplejwt.tokens import AccessToken


class CompanyMiddleware(MiddlewareMixin):
    def process_request(self, request):
        auth_header = request.headers.get("Authorization")

        if auth_header and auth_header.startswith("Bearer "):
            token_str = auth_header.split(" ")[1]  # Extract token
            try:
                token = AccessToken(token_str)
                company_id = token.get("company_id")
                if company_id == 63:
                    return JsonResponse(
                        {
                            "detail": "You do not have permission to perform this action."
                        },
                        status=403,
                    )
                request.company_id = company_id
                request.station_id = token.get("station_id")
            except Exception:
                request.company_id = None
                request.station_id = None

        return None

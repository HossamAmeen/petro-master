from apps.utilities.enhancement_request import enhance_request


class InjectUserMixin:
    def create(self, request, *args, **kwargs):
        request = enhance_request(request)
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        request = enhance_request(request)
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        request = enhance_request(request)
        return super().partial_update(request, *args, **kwargs)

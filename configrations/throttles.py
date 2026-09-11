from rest_framework.throttling import UserRateThrottle


class ContactUsRateThrottle(UserRateThrottle):
    rate = "5/minute"

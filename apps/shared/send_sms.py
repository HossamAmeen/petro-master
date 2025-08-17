import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def send_sms(message, receiver):
    if settings.ENVIRONMENT != "PRODUCTION":
        return
    url = f"https://smssmartegypt.com/sms/api/?username={settings.SMS_SMART_EGYPT_USERNAME}&password={settings.SMS_SMART_EGYPT_PASSWORD}&sendername={settings.SMS_SMART_EGYPT_SENDER_NAME}&message={message}&mobiles={receiver}"  # noqa
    response = requests.request("GET", url)
    logger.info(response.text)

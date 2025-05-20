# flake8: noqa


def generate_company_transaction():
    import random
    import uuid

    from apps.accounting.models import CompanyKhaznaTransaction
    from apps.companies.models.company_models import Company

    company_ids = list(Company.objects.values_list("id", flat=True))
    for _ in range(100):
        for_what = random.choice(CompanyKhaznaTransaction.ForWhat.values + [None])
        CompanyKhaznaTransaction.objects.create(
            amount=random.randint(100, 5000),
            is_incoming=True,
            status=CompanyKhaznaTransaction.TransactionStatus.APPROVED,
            reference_code=str(uuid.uuid4())[:10].upper(),
            description="Test transaction",
            method=CompanyKhaznaTransaction.TransactionMethod.BANK,
            company_id=random.choice(company_ids),
            for_what=for_what,
            created_by_id=1,
            updated_by_id=1,
        )


def generate_notification():
    import random

    from apps.notifications.models import Notification
    from apps.users.models import User

    users = User.objects.all()
    notification_types = [t[0] for t in Notification.NotificationType.choices]
    for user in users:
        for _ in range(random.randint(1, 5)):
            for notification_type in notification_types:
                if notification_type == "fuel":
                    title = "Fuel Notification"
                    describe = "Fuel Notification Description"
                elif notification_type == "money":
                    title = "Money Notification"
                    describe = "Money Notification Description"
                elif notification_type == "general":
                    title = "General Notification"
                    describe = "General Notification Description"
                elif notification_type == "station_worker":
                    title = "Station Worker Notification"
                    describe = "Station Worker Notification Description"
                elif notification_type == "station_service":
                    title = "Station Service Notification"
                    describe = "Station Service Notification Description"
                Notification.objects.create(
                    user=user,
                    title=title,
                    description=describe,
                    type=notification_type,
                    is_success=random.choice([True, False]),
                    is_read=random.choice([True, False]),
                    url=None,
                )

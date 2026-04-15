from apps.cars.models import Car
from django.db.models import Sum

from apps.companies.models import CompanyKhaznaTransaction


def sync_cars_balance():
    for car in Car.objects.order_by("created"):
        sync_car_balance(car)

def sync_car_balance(car):
    pull_amount = CompanyKhaznaTransaction.objects.filter(
        company=car.branch.company, description__icontains=f"{car.plate_character} " + car.car_number).filter(description__icontains="سحب").order_by("created").aggregate(Sum("amount"))['amount__sum']
    charge_amount = CompanyKhaznaTransaction.objects.filter(company=car.branch.company, description__icontains=f"{car.plate_character} " + car.car_number).filter(description__icontains="شحن").order_by("created").aggregate(Sum("amount"))['amount__sum']
    fuel_amount = CompanyKhaznaTransaction.objects.filter(company=car.branch.company, description__icontains=f"{car.plate_character} " + car.car_number).filter(description__icontains="تفويل").order_by("created").aggregate(Sum("amount"))['amount__sum']
    car.balance = charge_amount - pull_amount - fuel_amount
    car.save()

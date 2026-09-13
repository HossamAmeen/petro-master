from decimal import Decimal


def set_balance(instance, amount):
    instance.balance = Decimal(amount)
    instance.save(update_fields=["balance"])

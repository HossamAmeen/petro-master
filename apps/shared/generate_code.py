import random


def generate_unique_code(model, look_up="code", min_value=100000, max_value=999999):
    while True:
        new_code = str(random.randint(min_value, max_value))
        # `_base_manager` also sees soft-deleted rows, which keep their codes.
        if not model._base_manager.filter(**{look_up: new_code}).exists():
            return new_code

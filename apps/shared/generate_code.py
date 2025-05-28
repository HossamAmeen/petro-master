import random


def generate_unique_code(model, look_up="code", min_value=100000, max_value=999999):
    while True:
        new_code = str(random.randint(min_value, max_value))
        if not model.objects.filter(**{look_up: new_code}).exists():
            return new_code

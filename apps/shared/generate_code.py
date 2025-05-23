import random


def generate_unique_code(model):
    while True:
        new_code = str(random.randint(100000, 999999))
        if not model.objects.filter(code=new_code).exists():
            return new_code

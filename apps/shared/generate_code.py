import uuid


def generate_unique_code(model):
    while True:
        new_code = f"{model.__name__.lower()}-{uuid.uuid4().hex[:6].upper()}"  # Example: DR-ABC123
        if not model.objects.filter(code=new_code).exists():
            return new_code

from django.db import models
from apps.utilities.models.abstract_base_model import AbstractBaseModel
from apps.companies.models.operation_model import CarOperation

class AIApiResponse(AbstractBaseModel):
    car_operation = models.ForeignKey(CarOperation, on_delete=models.CASCADE, related_name="ai_api_responses")
    image_size = models.CharField(max_length=100, null=True, blank=True)
    extracted_number = models.CharField(max_length=255, null=True, blank=True)
    token_taken = models.IntegerField(null=True, blank=True)
    estimated_money = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)
    raw_response = models.JSONField(null=True, blank=True)

    class Meta:
        verbose_name = "AI API Response"
        verbose_name_plural = "AI API Responses"

    def __str__(self):
        return f"AI Response for {self.car_operation}"

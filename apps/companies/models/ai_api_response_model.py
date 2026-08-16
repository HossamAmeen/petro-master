from django.db import models

from apps.companies.models.operation_model import CarOperation
from apps.utilities.models.abstract_base_model import AbstractBaseModel


class AIApiResponse(AbstractBaseModel):
    car_operation = models.ForeignKey(
        CarOperation, on_delete=models.SET_NULL, related_name="ai_api_responses",
        null=True,
        blank=True,
        help_text="The car operation that this AI API response is for. If the car operation is deleted, the AI API response will be set to null."
    )
    image_size = models.CharField(max_length=100, null=True, blank=True)
    extracted_number = models.CharField(max_length=255, null=True, blank=True)
    match_score = models.PositiveSmallIntegerField(null=True, blank=True)
    token_taken = models.IntegerField(null=True, blank=True)
    estimated_money = models.DecimalField(
        max_digits=10, decimal_places=6, null=True, blank=True
    )
    model_name = models.CharField(max_length=100, null=True, blank=True)
    request_time = models.FloatField(
        null=True, blank=True, help_text="API request duration in seconds"
    )
    raw_response = models.JSONField(null=True, blank=True)

    class Meta:
        verbose_name = "AI API Response"
        verbose_name_plural = "AI API Responses"

    def __str__(self):
        return f"AI Response for {self.car_operation}"

from apps.users.models import User
import base64
import json
import os

import requests
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from openai import OpenAI

from apps.companies.models.ai_api_response_model import AIApiResponse
from apps.companies.models.operation_model import CarOperation


class Command(BaseCommand):
    help = "Process a specific number of CarOperations and send their images to the AI API."

    MODEL = "gpt-4o"
    MAX_TOKENS = 50
    PROMPT = "Extract only the fuel number/reading from this image. Reply with the number only."
    INPUT_PRICE_PER_MILLION = 5.0
    OUTPUT_PRICE_PER_MILLION = 15.0
    MEDIA_BASE_URL = getattr(settings, "MEDIA_PUBLIC_BASE_URL", "https://api.staging.petro-master.org")

    def add_arguments(self, parser):
        parser.add_argument("limit", type=int, help="The number of CarOperations to process")
        parser.add_argument(
            "--image-field",
            type=str,
            default="fuel_image",
            help="Image field to use (e.g. car_image, motor_image, fuel_image)",
        )

    def handle(self, *args, **options):
        api_key = getattr(settings, "OPENAI_API_KEY", None) or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise CommandError("OPENAI_API_KEY is not set in settings or environment variables.")

        self.client = OpenAI(api_key=api_key)
        image_field = options["image_field"]
        limit = options["limit"]
        
        branch_ids = CarOperation.objects.filter(
            ai_api_responses__isnull=True
        ).values_list('station_branch_id', flat=True).distinct()
        
        operations = []
        for branch_id in branch_ids:
            branch_ops = CarOperation.objects.filter(
                ai_api_responses__isnull=True, 
                station_branch_id=branch_id
            ).order_by("-id")[:limit]
            operations.extend(branch_ops)

        if not operations:
            self.stdout.write(self.style.SUCCESS("No pending CarOperations found."))
            return

        user_id = User.objects.filter(phone_number="01010079798").first().id
        success_count = 0
        for operation in operations:
            try:
                self.process_operation(operation, image_field, user_id)
                success_count += 1
                self.stdout.write(self.style.SUCCESS(f"Successfully processed {operation.code}"))
            except Exception as exc:
                self.stdout.write(self.style.ERROR(f"Failed to process {operation.code}: {exc}"))

        self.stdout.write(self.style.SUCCESS(f"Finished processing {success_count} operations."))

    def process_operation(self, operation, image_field: str, user_id: int) -> None:
        image_file = getattr(operation, image_field, None)
        if not image_file:
            raise ValueError(f"CarOperation {operation.code} has no {image_field}.")

        image_url = self.build_image_url(image_file)
        image_bytes, media_type = self.download_image(image_url)
        # result = self.extract_fuel_number(image_bytes, media_type)
        result = {}
        self.save_response(operation, result, len(image_bytes), created_by=user_id)

    def build_image_url(self, image_file) -> str:
        return "https://api.petro-master.org/media/fuel_images/CAP2351827349112984160.jpg"
        url = image_file.url
        if url.startswith(("http://", "https://")):
            return url
        return f"{self.MEDIA_BASE_URL.rstrip('/')}{url}"

    def download_image(self, url: str) -> tuple[bytes, str]:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        content_type = response.headers.get("Content-Type", "image/jpeg")
        media_type = content_type.split(";")[0].strip() or "image/jpeg"
        return response.content, media_type

    def extract_fuel_number(self, image_bytes: bytes, media_type: str) -> dict:
        b64 = base64.b64encode(image_bytes).decode("utf-8")
        response = self.client.chat.completions.create(
            model=self.MODEL,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": self.PROMPT},
                    {"type": "image_url", "image_url": {"url": f"data:{media_type};base64,{b64}"}},
                ],
            }],
            max_tokens=self.MAX_TOKENS,
        )

        usage = response.usage
        prompt_tokens = usage.prompt_tokens if usage else 0
        completion_tokens = usage.completion_tokens if usage else 0
        total_tokens = usage.total_tokens if usage else 0
        content = response.choices[0].message.content if response.choices else None

        return {
            "extracted_number": content.strip() if content else None,
            "raw_response": json.loads(response.model_dump_json()),
            "token_taken": total_tokens,
            "estimated_money": self.estimate_cost(prompt_tokens, completion_tokens),
        }

    def estimate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        return (
            (prompt_tokens / 1_000_000.0) * self.INPUT_PRICE_PER_MILLION
            + (completion_tokens / 1_000_000.0) * self.OUTPUT_PRICE_PER_MILLION
        )

    def save_response(self, operation, result: dict, image_size: int, created_by: int) -> None:
        try:
            AIApiResponse.objects.create(
                car_operation=operation,
                raw_response=result.get("raw_response",{}),
                extracted_number=result.get("extracted_number"),
                image_size=str(image_size),
                token_taken=result.get("token_taken"),
                estimated_money=result.get("estimated_money"),
                created_by_id=created_by
            )
        except Exception as exc:
            print(exc)

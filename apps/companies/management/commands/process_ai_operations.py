from apps.users.models import User
import base64
import json
import os
import time
from decimal import Decimal, InvalidOperation

import requests
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Count
from openai import OpenAI, RateLimitError

from apps.companies.models.ai_api_response_model import AIApiResponse
from apps.companies.models.operation_model import CarOperation


class Command(BaseCommand):
    help = "Process a specific number of CarOperations and send their images to the AI API."

    MODEL = "gpt-4o"
    MAX_TOKENS = 50
    PROMPT = (
        "Extract only the fuel number/reading from this image. "
        "Reply with the number only. "
        "The car tank capacity is {tank_capacity}. "
        "Do not return a number greater than the car tank capacity."
    )
    PRICE_PER_MILLION_TOKENS_USD = 5.0
    USD_TO_EGP = 50.0
    MEDIA_BASE_URL = getattr(settings, "MEDIA_PUBLIC_BASE_URL", "https://api.petro-master.org")
    MAX_RESPONSES_PER_BRANCH = 100
    BATCH_SIZE = 20
    BATCH_SLEEP_SECONDS = 5
    MAX_RETRIES = 5
    RETRY_BASE_SECONDS = 2

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

        self.api_key = api_key
        self.client = OpenAI(api_key=api_key)
        image_field = options["image_field"]
        limit = options["limit"]

        branch_ids = list(
            CarOperation.objects.filter(
                ai_api_responses__isnull=True,
                fuel_image__isnull=False,
            )
            .values_list("station_branch_id", flat=True)
            .distinct()
        )

        existing_counts = {
            row["car_operation__station_branch_id"]: row["total"]
            for row in (
                AIApiResponse.objects.filter(
                    car_operation__station_branch_id__in=branch_ids
                )
                .values("car_operation__station_branch_id")
                .annotate(total=Count("id"))
            )
        }

        # Collect pending ops per branch (respect max 100 AIApiResponse per branch).
        branch_queues = []
        for branch_id in branch_ids:
            existing_count = existing_counts.get(branch_id, 0)
            remaining_capacity = self.MAX_RESPONSES_PER_BRANCH - existing_count
            if remaining_capacity <= 0:
                self.stdout.write(
                    self.style.WARNING(
                        f"Station branch {branch_id} already has "
                        f"{existing_count} AIApiResponse records (max "
                        f"{self.MAX_RESPONSES_PER_BRANCH}). Skipping."
                    )
                )
                continue

            branch_limit = min(limit, remaining_capacity)
            branch_ops = list(
                CarOperation.objects.filter(
                    ai_api_responses__isnull=True,
                    station_branch_id=branch_id,
                    fuel_image__isnull=False,
                )
                .exclude(fuel_image="")
                .select_related("car")
                .order_by("-id")[:branch_limit]
            )
            if branch_ops:
                branch_queues.append(branch_ops)

        # Round-robin: one op from each branch per round.
        # Round 1: branchA, branchB, branchC...
        # Round 2: branchA, branchB, branchC...
        operations = []
        for round_index in range(limit):
            for branch_ops in branch_queues:
                if round_index < len(branch_ops):
                    operations.append(branch_ops[round_index])

        if not operations:
            self.stdout.write(self.style.SUCCESS("No pending CarOperations found."))
            return

        user_id = User.objects.filter(phone_number="01010079798").first().id
        success_count = 0
        for index, operation in enumerate(operations, start=1):
            try:
                self.process_operation(operation, image_field, user_id)
                success_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f"Successfully processed {operation.code}")
                )
            except Exception as exc:
                self.stdout.write(
                    self.style.ERROR(f"Failed to process {operation.code}: {exc}")
                )

            if index % self.BATCH_SIZE == 0 and index < len(operations):
                self.stdout.write(
                    self.style.WARNING(
                        f"Processed {index} requests. Sleeping "
                        f"{self.BATCH_SLEEP_SECONDS}s to avoid rate limits..."
                    )
                )
                time.sleep(self.BATCH_SLEEP_SECONDS)

        self.stdout.write(
            self.style.SUCCESS(f"Finished processing {success_count} operations.")
        )

    def process_operation(self, operation, image_field: str, user_id: int) -> None:
        image_file = getattr(operation, image_field, None)
        if not image_file:
            raise ValueError(f"CarOperation {operation.code} has no {image_field}.")
        if not operation.car or operation.car.tank_capacity is None:
            raise ValueError(
                f"CarOperation {operation.code} has no car tank capacity."
            )

        image_url = self.build_image_url(image_file)
        image_bytes, media_type = self.download_image(image_url)
        result = self.extract_fuel_number(
            image_bytes, media_type, tank_capacity=operation.car.tank_capacity
        )
        self.save_response(operation, result, len(image_bytes), created_by=user_id)

    def build_prompt(self, tank_capacity: int) -> str:
        return self.PROMPT.format(tank_capacity=tank_capacity)

    def build_image_url(self, image_file) -> str:
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

    def extract_fuel_number(
        self, image_bytes: bytes, media_type: str, tank_capacity: int
    ) -> dict:
        b64 = base64.b64encode(image_bytes).decode("utf-8")
        prompt = self.build_prompt(tank_capacity)
        started_at = time.perf_counter()
        response = self.create_completion_with_retry(prompt, b64, media_type)
        request_time = time.perf_counter() - started_at

        usage = response.usage
        total_tokens = usage.total_tokens if usage else 0
        content = response.choices[0].message.content if response.choices else None

        return {
            "extracted_number": content.strip() if content else None,
            "raw_response": json.loads(response.model_dump_json()),
            "token_taken": total_tokens,
            "estimated_money": self.estimate_cost(total_tokens),
            "model_name": getattr(response, "model", None) or self.MODEL,
            "request_time": request_time,
        }

    def create_completion_with_retry(self, prompt: str, b64: str, media_type: str):
        last_error = None
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                return self.client.chat.completions.create(
                    model=self.MODEL,
                    messages=[{
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{media_type};base64,{b64}"
                                },
                            },
                        ],
                    }],
                    max_tokens=self.MAX_TOKENS,
                )
            except RateLimitError as exc:
                last_error = exc
                wait_seconds = self.get_retry_wait_seconds(exc, attempt)
                self.stdout.write(
                    self.style.WARNING(
                        f"Rate limit hit (attempt {attempt}/{self.MAX_RETRIES}). "
                        f"Retrying in {wait_seconds:.1f}s..."
                    )
                )
                time.sleep(wait_seconds)

        raise last_error

    def get_retry_wait_seconds(self, exc: RateLimitError, attempt: int) -> float:
        headers = getattr(exc, "response", None)
        headers = getattr(headers, "headers", {}) if headers else {}
        retry_after = headers.get("retry-after") or headers.get("Retry-After")
        if retry_after:
            try:
                return max(float(retry_after), 1.0)
            except (TypeError, ValueError):
                pass
        return self.RETRY_BASE_SECONDS * (2 ** (attempt - 1))

    def estimate_cost(self, total_tokens: int) -> Decimal:
        """Estimate request cost in EGP. $5 per 1M tokens, $1 = 50 EGP."""
        cost_usd = (Decimal(total_tokens) / Decimal("1000000")) * Decimal(
            str(self.PRICE_PER_MILLION_TOKENS_USD)
        )
        return cost_usd * Decimal(str(self.USD_TO_EGP))

    def calculate_match_score(self, extracted_number, amount) -> int | None:
        if extracted_number is None or amount is None:
            return None
        try:
            extracted = Decimal(str(extracted_number).strip())
            actual = Decimal(str(amount))
        except (InvalidOperation, ValueError, TypeError):
            return None

        difference = abs(extracted - actual)
        if difference <= 1:
            return 100
        if difference <= 5:
            return 50
        return 0

    def save_response(self, operation, result: dict, image_size: int, created_by: int) -> None:
        extracted_number = result.get("extracted_number")
        try:
            AIApiResponse.objects.create(
                car_operation=operation,
                raw_response=result.get("raw_response", {}),
                extracted_number=extracted_number,
                match_score=self.calculate_match_score(extracted_number, operation.amount),
                image_size=str(image_size),
                token_taken=result.get("token_taken"),
                estimated_money=result.get("estimated_money"),
                model_name=result.get("model_name"),
                request_time=result.get("request_time"),
                created_by_id=created_by,
            )
        except Exception as exc:
            print(exc)

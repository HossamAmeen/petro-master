import os

from django.conf import settings
from django.utils import timezone
from openpyxl import Workbook


def export_car_operations(data):
    # Create the Excel workbook and sheet
    wb = Workbook()
    ws = wb.active
    ws.title = "Data Export"

    # Write headers (first row)
    headers = list(data[0].keys())
    cleaned_headers = [str(header) for header in headers]
    ws.append(cleaned_headers)

    # Write data rows
    for row in data:
        cleaned_row = []
        for value in row.values():
            if value is None:
                cleaned_value = ""
            elif isinstance(value, (dict, list)):
                cleaned_value = str(value)
            else:
                cleaned_value = str(value)
            cleaned_row.append(cleaned_value)
        ws.append(cleaned_row)

    # Generate filename with timestamp
    timestamp = timezone.localtime().strftime("%Y%m%d_%H%M%S")
    filename = f"export_{timestamp}.xlsx"
    excel_dir = os.path.join(settings.MEDIA_ROOT, "excel_exports")
    os.makedirs(excel_dir, exist_ok=True)
    filepath = os.path.join(excel_dir, filename)

    # Save workbook to media folder
    wb.save(filepath)
    return filename

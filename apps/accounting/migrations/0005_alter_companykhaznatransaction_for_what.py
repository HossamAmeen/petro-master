# Generated by Django 4.2 on 2025-05-11 15:27

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounting", "0004_remove_khaznatransaction_polymorphic_ctype"),
    ]

    operations = [
        migrations.AlterField(
            model_name="companykhaznatransaction",
            name="for_what",
            field=models.CharField(
                blank=True,
                choices=[("Branch", "Branch"), ("Car", "Car")],
                default="Branch",
                max_length=20,
                null=True,
            ),
        ),
    ]

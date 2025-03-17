# Generated by Django 4.2 on 2025-03-13 22:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('companies', '0002_car'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='car',
            options={'verbose_name': 'Car', 'verbose_name_plural': 'Cars'},
        ),
        migrations.AlterField(
            model_name='car',
            name='fuel_type',
            field=models.CharField(choices=[('Diesel', 'Diesel'), ('Gasoline', 'Gasoline'), ('Electric', 'Electric'), ('Hydrogen', 'Hydrogen')], max_length=20),
        ),
    ]

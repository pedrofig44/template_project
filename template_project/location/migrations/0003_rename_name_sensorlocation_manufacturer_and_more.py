# Generated by Django 4.2.15 on 2024-09-14 14:51

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("location", "0002_coordinates_concelho_distrito_location_id_and_more"),
    ]

    operations = [
        migrations.RenameField(
            model_name="sensorlocation",
            old_name="name",
            new_name="manufacturer",
        ),
        migrations.RemoveField(
            model_name="sensorlocation",
            name="country",
        ),
        migrations.RemoveField(
            model_name="sensorlocation",
            name="district",
        ),
        migrations.AddField(
            model_name="sensorlocation",
            name="model",
            field=models.CharField(default=1, max_length=255),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="sensorlocation",
            name="sensor_id",
            field=models.CharField(
                default=1,
                max_length=8,
                validators=[
                    django.core.validators.RegexValidator(
                        "^\\d{8}$", "Sensor ID must be an 8-digit number."
                    )
                ],
            ),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name="distrito",
            name="location_id",
            field=models.CharField(
                max_length=7,
                unique=True,
                validators=[
                    django.core.validators.RegexValidator(
                        "^\\d{7}$", "Location ID must be a 7-digit number."
                    )
                ],
            ),
        ),
    ]

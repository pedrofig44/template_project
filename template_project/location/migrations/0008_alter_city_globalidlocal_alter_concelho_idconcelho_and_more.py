# Generated by Django 4.2.15 on 2025-02-14 10:06

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        (
            "location",
            "0007_city_alter_country_options_remove_distrito_country_and_more",
        ),
    ]

    operations = [
        migrations.AlterField(
            model_name="city",
            name="globalIdLocal",
            field=models.CharField(
                max_length=7,
                unique=True,
                validators=[django.core.validators.RegexValidator("^\\d{7}$")],
            ),
        ),
        migrations.AlterField(
            model_name="concelho",
            name="idConcelho",
            field=models.IntegerField(unique=True),
        ),
        migrations.AlterField(
            model_name="distrito",
            name="idDistrito",
            field=models.IntegerField(unique=True),
        ),
        migrations.AlterField(
            model_name="distrito",
            name="location_id",
            field=models.CharField(
                max_length=7,
                unique=True,
                validators=[django.core.validators.RegexValidator("^\\d{7}$")],
            ),
        ),
        migrations.AlterField(
            model_name="region",
            name="idRegiao",
            field=models.IntegerField(unique=True),
        ),
        migrations.AlterField(
            model_name="weatherstation",
            name="station_id",
            field=models.CharField(max_length=50, unique=True),
        ),
    ]

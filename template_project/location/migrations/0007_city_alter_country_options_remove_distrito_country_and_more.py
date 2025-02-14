# Generated by Django 4.2.15 on 2025-02-11 16:15

import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("location", "0006_alter_sensorinfo_manufacturer_alter_sensorinfo_model"),
    ]

    operations = [
        migrations.CreateModel(
            name="City",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=100)),
                (
                    "globalIdLocal",
                    models.CharField(
                        max_length=7,
                        unique=True,
                        validators=[
                            django.core.validators.RegexValidator(
                                "^\\d{7}$",
                                "Global Location ID must be a 7-digit number.",
                            )
                        ],
                    ),
                ),
                ("latitude", models.FloatField()),
                ("longitude", models.FloatField()),
            ],
            options={
                "verbose_name_plural": "Cities",
            },
        ),
        migrations.AlterModelOptions(
            name="country",
            options={"verbose_name_plural": "Countries"},
        ),
        migrations.RemoveField(
            model_name="distrito",
            name="country",
        ),
        migrations.AddField(
            model_name="concelho",
            name="idConcelho",
            field=models.IntegerField(
                blank=True,
                null=True,
                unique=True,
                verbose_name="Municipality ID from IPMA API",
            ),
        ),
        migrations.AddField(
            model_name="distrito",
            name="idDistrito",
            field=models.IntegerField(
                default=1, unique=True, verbose_name="District ID from IPMA API"
            ),
            preserve_default=False,
        ),
        migrations.CreateModel(
            name="WeatherStation",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=100)),
                (
                    "station_id",
                    models.CharField(
                        max_length=50,
                        unique=True,
                        verbose_name="Station ID from IPMA API",
                    ),
                ),
                ("latitude", models.FloatField()),
                ("longitude", models.FloatField()),
                (
                    "city",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="weather_stations",
                        to="location.city",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Region",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=100)),
                (
                    "idRegiao",
                    models.IntegerField(
                        unique=True, verbose_name="Region ID from IPMA API"
                    ),
                ),
                (
                    "country",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="regions",
                        to="location.country",
                    ),
                ),
            ],
        ),
        migrations.AddField(
            model_name="city",
            name="concelho",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="cities",
                to="location.concelho",
            ),
        ),
        migrations.AddField(
            model_name="distrito",
            name="region",
            field=models.ForeignKey(
                default=1,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="distritos",
                to="location.region",
            ),
            preserve_default=False,
        ),
    ]

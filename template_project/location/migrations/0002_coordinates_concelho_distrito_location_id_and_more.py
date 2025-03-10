# Generated by Django 4.2.15 on 2024-09-13 21:40

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0004_alter_profile_profile_picture"),
        ("location", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="coordinates",
            name="concelho",
            field=models.ForeignKey(
                default=1,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="coordinates",
                to="location.concelho",
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="distrito",
            name="location_id",
            field=models.CharField(default=1, max_length=7, unique=True),
            preserve_default=False,
        ),
        migrations.CreateModel(
            name="SensorLocation",
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
                ("name", models.CharField(max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "coordinates",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="sensor_locations",
                        to="location.coordinates",
                    ),
                ),
                (
                    "country",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="sensor_locations",
                        to="location.country",
                    ),
                ),
                (
                    "district",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="sensor_locations",
                        to="location.distrito",
                    ),
                ),
                (
                    "organization",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="sensor_locations",
                        to="accounts.organization",
                    ),
                ),
            ],
        ),
    ]

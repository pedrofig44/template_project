# Generated by Django 4.2.15 on 2025-02-18 09:31

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("location", "0013_alter_weatherstation_concelho"),
        ("climate", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="FireRisk",
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
                (
                    "forecast_day",
                    models.IntegerField(choices=[(0, "Today"), (1, "Tomorrow")]),
                ),
                ("forecast_date", models.DateField()),
                ("model_run_date", models.DateField()),
                ("update_date", models.DateTimeField()),
                (
                    "risk_level",
                    models.IntegerField(
                        choices=[
                            (1, "Reduced Risk"),
                            (2, "Moderate Risk"),
                            (3, "High Risk"),
                            (4, "Very High Risk"),
                            (5, "Maximum Risk"),
                        ]
                    ),
                ),
                (
                    "concelho",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="fire_risks",
                        to="location.concelho",
                        to_field="dico_code",
                    ),
                ),
            ],
            options={
                "verbose_name": "Fire Risk",
                "verbose_name_plural": "Fire Risks",
                "ordering": ["forecast_day", "concelho"],
                "unique_together": {("concelho", "forecast_day")},
            },
        ),
    ]

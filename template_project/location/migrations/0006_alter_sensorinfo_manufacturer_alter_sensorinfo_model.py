# Generated by Django 4.2.15 on 2024-09-15 21:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("location", "0005_rename_sensorlocation_sensorinfo"),
    ]

    operations = [
        migrations.AlterField(
            model_name="sensorinfo",
            name="manufacturer",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name="sensorinfo",
            name="model",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]

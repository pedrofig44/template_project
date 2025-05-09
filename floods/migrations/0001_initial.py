# Generated by Django 4.2.15 on 2025-04-21 10:26

import django.contrib.gis.db.models.fields
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('location', '0013_alter_weatherstation_concelho'),
    ]

    operations = [
        migrations.CreateModel(
            name='WaterBody',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('water_body_type', models.CharField(choices=[('river', 'River'), ('lake', 'Lake'), ('reservoir', 'Reservoir'), ('stream', 'Stream'), ('coastal', 'Coastal Water')], max_length=20)),
                ('description', models.TextField(blank=True, null=True)),
                ('geometry', django.contrib.gis.db.models.fields.LineStringField(blank=True, null=True, srid=4326)),
                ('normal_level', models.FloatField(blank=True, help_text='Normal water level (m)', null=True)),
                ('warning_level', models.FloatField(blank=True, help_text='Level that triggers warnings (m)', null=True)),
                ('danger_level', models.FloatField(blank=True, help_text='Level that constitutes flooding (m)', null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('concelho', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='water_bodies', to='location.concelho')),
            ],
            options={
                'verbose_name': 'Water Body',
                'verbose_name_plural': 'Water Bodies',
            },
        ),
        migrations.CreateModel(
            name='WaterStation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('station_id', models.CharField(max_length=50, unique=True)),
                ('level_channel_id', models.CharField(blank=True, help_text='API channel ID for level data', max_length=50, null=True)),
                ('flow_channel_id', models.CharField(blank=True, help_text='API channel ID for flow data', max_length=50, null=True)),
                ('measurement_type', models.CharField(choices=[('level', 'Water Level Only'), ('flow', 'Water Flow Only'), ('combined', 'Level and Flow')], max_length=20)),
                ('location', django.contrib.gis.db.models.fields.PointField(blank=True, null=True, srid=4326)),
                ('is_active', models.BooleanField(default=True)),
                ('last_reading_time', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('concelho', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='water_stations', to='location.concelho')),
                ('water_body', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='stations', to='floods.waterbody')),
            ],
            options={
                'verbose_name': 'Water Station',
                'verbose_name_plural': 'Water Stations',
            },
        ),
        migrations.CreateModel(
            name='WaterReading',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('timestamp', models.DateTimeField()),
                ('water_level', models.FloatField(blank=True, help_text='Water level in meters', null=True)),
                ('level_change', models.FloatField(blank=True, help_text='Change in level since last reading (m)', null=True)),
                ('flow_rate', models.FloatField(blank=True, help_text='Flow rate in liters per second (l/s)', null=True)),
                ('flow_change', models.FloatField(blank=True, help_text='Change in flow since last reading (l/s)', null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('station', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='readings', to='floods.waterstation')),
            ],
            options={
                'verbose_name': 'Water Reading',
                'verbose_name_plural': 'Water Readings',
            },
        ),
        migrations.CreateModel(
            name='FloodWarning',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('warning_level', models.CharField(choices=[('watch', 'Watch'), ('advisory', 'Advisory'), ('warning', 'Warning'), ('emergency', 'Emergency')], max_length=20)),
                ('title', models.CharField(max_length=255)),
                ('description', models.TextField()),
                ('start_time', models.DateTimeField()),
                ('end_time', models.DateTimeField(blank=True, null=True)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('station', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='flood_warnings', to='floods.waterstation')),
                ('triggered_by_reading', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='floods.waterreading')),
                ('water_body', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='flood_warnings', to='floods.waterbody')),
            ],
            options={
                'verbose_name': 'Flood Warning',
                'verbose_name_plural': 'Flood Warnings',
            },
        ),
        migrations.AddIndex(
            model_name='waterreading',
            index=models.Index(fields=['timestamp'], name='floods_wate_timesta_bfb92e_idx'),
        ),
        migrations.AddIndex(
            model_name='waterreading',
            index=models.Index(fields=['station', 'timestamp'], name='floods_wate_station_e2ee4d_idx'),
        ),
        migrations.AlterUniqueTogether(
            name='waterreading',
            unique_together={('station', 'timestamp')},
        ),
    ]

# Generated by Django 4.2.17 on 2025-06-24 13:21

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('location', '0017_alter_concelholandoccupation_concelho'),
        ('analytics', '0003_alter_concelhoriskanalytics_options_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='ConcelhoWildfireRecovery',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('analysis_date', models.DateField(help_text='Date for which this recovery analysis applies')),
                ('significant_burn_recovery', models.IntegerField(choices=[(0, 'No significant burn recovery'), (1, 'Significant burn recovery')], help_text='Indicator if region had significant wildfire in last 7 years (0 or 1)')),
                ('wildfire_season_year', models.IntegerField(help_text='Wildfire season year this analysis applies to')),
                ('lookback_period_start', models.DateField(blank=True, help_text='Start date of 7-year lookback period for recovery analysis', null=True)),
                ('lookback_period_end', models.DateField(blank=True, help_text='End date of 7-year lookback period for recovery analysis', null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('concelho', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='wildfire_recovery', to='location.concelho')),
            ],
            options={
                'verbose_name': 'Concelho Wildfire Recovery',
                'verbose_name_plural': 'Concelho Wildfire Recovery',
                'ordering': ['-analysis_date', 'concelho'],
                'indexes': [models.Index(fields=['analysis_date'], name='analytics_c_analysi_347ffa_idx'), models.Index(fields=['concelho', 'analysis_date'], name='analytics_c_concelh_bacf96_idx'), models.Index(fields=['wildfire_season_year'], name='analytics_c_wildfir_b01c9b_idx'), models.Index(fields=['significant_burn_recovery'], name='analytics_c_signifi_fe4c0e_idx')],
                'unique_together': {('concelho', 'analysis_date')},
            },
        ),
    ]

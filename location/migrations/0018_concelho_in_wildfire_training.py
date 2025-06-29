# Generated by Django 4.2.17 on 2025-06-26 14:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('location', '0017_alter_concelholandoccupation_concelho'),
    ]

    operations = [
        migrations.AddField(
            model_name='concelho',
            name='in_wildfire_training',
            field=models.BooleanField(default=False, help_text='Whether this concelho was included in wildfire prediction model training data (251 out of 308 concelhos)'),
        ),
    ]

# Generated by Django 5.2.1 on 2025-06-03 16:00

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Nurse',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('FREE', 'Free'), ('BUSY', 'Busy'), ('ON_BREAK', 'On Break')], default='ON_BREAK', help_text='Current availability status of the nurse.', max_length=10)),
                ('fcm_token', models.CharField(blank=True, help_text='Firebase Cloud Messaging device token for push notifications.', max_length=255, null=True)),
                ('employee_id', models.CharField(blank=True, max_length=20, null=True, unique=True)),
                ('specialty', models.CharField(blank=True, max_length=100, null=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='nurse_profile', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Nurse',
                'verbose_name_plural': 'Nurses',
            },
        ),
    ]

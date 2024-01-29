# Generated by Django 2.2.14 on 2021-12-20 19:22

from django.db import migrations, models
import kobo.apps.open_rosa_server.apps.logger.fields


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0006_add_creation_and_modification_dates_to_metadata'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='is_mfa_active',
            field=kobo.apps.open_rosa_server.apps.logger.fields.LazyDefaultBooleanField(default=False),
        ),
    ]

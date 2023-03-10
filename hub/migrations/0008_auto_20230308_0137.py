# Generated by Django 3.2.15 on 2023-03-08 01:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('hub', '0007_alter_jsonfield_to_jsonbfield'),
    ]

    operations = [
        migrations.AlterField(
            model_name='configurationfile',
            name='content',
            field=models.FileField(help_text='Stored in a PUBLIC location where authentication is NOT required for access', upload_to='__public/'),
        ),
        migrations.AlterField(
            model_name='perusersetting',
            name='name',
            field=models.CharField(default='INTERCOM_APP_ID', max_length=255, unique=True),
        ),
    ]
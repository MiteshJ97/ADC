# Generated by Django 4.2 on 2024-02-28 17:27

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0002_rename_researchdocument_syncfromsource'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='syncfromsource',
            name='bureau_code',
        ),
    ]

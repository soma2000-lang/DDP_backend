# Generated by Django 4.1.7 on 2024-03-20 14:52

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("ddpui", "0061_alter_orgdbtmodel_display_name_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="orgdbtmodel",
            name="schema",
            field=models.CharField(max_length=300, null=True),
        ),
        migrations.AlterField(
            model_name="orgdbtmodel",
            name="source_name",
            field=models.CharField(max_length=300, null=True),
        ),
    ]

# Generated by Django 5.2 on 2025-04-29 07:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('stocks', '0002_portfolio'),
    ]

    operations = [
        migrations.AlterField(
            model_name='portfolio',
            name='symbol',
            field=models.CharField(max_length=30),
        ),
        migrations.AlterField(
            model_name='stockprice',
            name='symbol',
            field=models.CharField(max_length=30),
        ),
    ]

# Generated by Django 5.0.4 on 2024-05-13 22:03

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('work', '0010_rename_insurancesum_contract_insurance_sum'),
    ]

    operations = [
        migrations.AlterField(
            model_name='contract',
            name='cost',
            field=models.DecimalField(decimal_places=2, max_digits=20, validators=[django.core.validators.MinValueValidator(0, 'Стоимость договора слишком мала')], verbose_name='Стоимость договора'),
        ),
        migrations.AlterField(
            model_name='contract',
            name='insurance_sum',
            field=models.DecimalField(decimal_places=2, max_digits=20, validators=[django.core.validators.MinValueValidator(100, 'Страховая сумма слишком мала')], verbose_name='Страховая сумма'),
        ),
        migrations.AlterField(
            model_name='incidentdecision',
            name='sum',
            field=models.DecimalField(decimal_places=2, max_digits=20, verbose_name='Сумма страховой выплаты'),
        ),
    ]
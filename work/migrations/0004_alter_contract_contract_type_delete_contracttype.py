# Generated by Django 5.0.4 on 2024-05-10 06:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('work', '0003_remove_employee_first_name_remove_employee_last_name_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='contract',
            name='contract_type',
            field=models.CharField(choices=[('house', 'Страхование недвижимости'), ('person', 'Страхование жизни')], verbose_name='Тип договора'),
        ),
        migrations.DeleteModel(
            name='ContractType',
        ),
    ]
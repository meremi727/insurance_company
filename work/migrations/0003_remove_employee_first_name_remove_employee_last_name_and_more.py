# Generated by Django 5.0.4 on 2024-05-09 16:14

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('work', '0002_alter_employee_person'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='employee',
            name='first_name',
        ),
        migrations.RemoveField(
            model_name='employee',
            name='last_name',
        ),
        migrations.AlterField(
            model_name='employee',
            name='person',
            field=models.OneToOneField(on_delete=django.db.models.deletion.DO_NOTHING, to='work.person', verbose_name='Персона'),
        ),
    ]

# Generated by Django 3.0.7 on 2020-12-04 16:40

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('ssp', '0001_squashed_0003_auto_20201015_1419'),
    ]

    operations = [
        migrations.AlterField(
            model_name='nist_control_statement',
            name='nist_control',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='ssp.nist_control'),
        ),
    ]

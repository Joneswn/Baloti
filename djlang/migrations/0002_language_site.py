# Generated by Django 3.1 on 2021-07-30 11:35

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('djlang', '0001_initial'),
        ('electeez_sites', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='language',
            name='site',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='electeez_sites.site'),
        ),
    ]
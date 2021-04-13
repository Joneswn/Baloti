# Generated by Django 3.1.7 on 2021-04-09 05:40

from django.db import migrations, models
import timezone_field.fields


class Migration(migrations.Migration):

    dependencies = [
        ('djelectionguard', '0016_remove_field_decentralized'),
    ]

    operations = [
        migrations.AddField(
            model_name='candidate',
            name='description',
            field=models.CharField(blank=True, max_length=1024, null=True),
        ),
        migrations.AddField(
            model_name='candidate',
            name='picture',
            field=models.ImageField(blank=True, null=True, upload_to='candidates'),
        ),
    ]
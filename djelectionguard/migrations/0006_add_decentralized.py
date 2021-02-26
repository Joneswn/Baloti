# Generated by Django 3.1.7 on 2021-02-26 13:30

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('djelectionguard', '0005_artifacts_and_ipfs'),
    ]

    operations = [
        migrations.AddField(
            model_name='contest',
            name='decentralized',
            field=models.BooleanField(default=False),
            preserve_default=False,
        ),
        migrations.AlterUniqueTogether(
            name='guardian',
            unique_together={('contest', 'user')},
        ),
    ]

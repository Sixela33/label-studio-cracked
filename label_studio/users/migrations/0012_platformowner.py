from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def backfill_platform_owner(apps, schema_editor):
    User = apps.get_model('users', 'User')
    PlatformOwner = apps.get_model('users', 'PlatformOwner')

    if PlatformOwner.objects.exists():
        return

    first_user = User.objects.order_by('id').first()
    if first_user is not None:
        PlatformOwner.objects.create(user=first_user)


def remove_backfilled_platform_owner(apps, schema_editor):
    PlatformOwner = apps.get_model('users', 'PlatformOwner')
    PlatformOwner.objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [
        ('users', '0011_user_custom_hotkeys'),
    ]

    operations = [
        migrations.CreateModel(
            name='PlatformOwner',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='created at')),
                (
                    'user',
                    models.OneToOneField(
                        help_text='User with instance-level owner privileges.',
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='platform_owner',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                'verbose_name': 'platform owner',
                'verbose_name_plural': 'platform owners',
                'db_table': 'platform_owner',
            },
        ),
        migrations.RunPython(backfill_platform_owner, remove_backfilled_platform_owner),
    ]

# Generated for minimal OSS RBAC.

from django.db import migrations, models


def backfill_existing_members_as_admin(apps, schema_editor):
    OrganizationMember = apps.get_model('organizations', 'OrganizationMember')
    OrganizationMember.objects.filter(role='annotator').update(role='admin')


class Migration(migrations.Migration):
    dependencies = [
        ('organizations', '0006_alter_organizationmember_deleted_at'),
    ]

    operations = [
        migrations.AddField(
            model_name='organizationmember',
            name='role',
            field=models.CharField(
                choices=[('admin', 'Admin'), ('manager', 'Manager'), ('annotator', 'Annotator')],
                db_index=True,
                default='annotator',
                help_text='Organization role used for role-based access control.',
                max_length=32,
                verbose_name='role',
            ),
        ),
        migrations.RunPython(backfill_existing_members_as_admin, migrations.RunPython.noop),
    ]

from django.db import migrations


def create_analyzer_group(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Group.objects.using(schema_editor.connection.alias).get_or_create(name='Analyzer')


class Migration(migrations.Migration):
    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
        ('worth_to_buy_analyzer', '0004_clothing_reference'),
    ]

    operations = [
        # Create the role only; never grant it to existing users automatically.
        # Preserve memberships if schema migrations are rolled back.
        migrations.RunPython(create_analyzer_group, migrations.RunPython.noop),
    ]

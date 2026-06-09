from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("merits", "0001_initial"),
    ]

    operations = [
        migrations.RenameField(
            model_name="meritrecord",
            old_name="points",
            new_name="count",
        ),
        migrations.RenameField(
            model_name="demeritrecord",
            old_name="points",
            new_name="count",
        ),
    ]

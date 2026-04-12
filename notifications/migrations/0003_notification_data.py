# -*- coding: utf-8 -*-
from django.db import models, migrations

try:
    import jsonfield.fields
except ImportError:
    # jsonfield was replaced by Django's built-in JSONField in migration 0011.
    from django.db import models as _models
    class jsonfield:
        class fields:
            JSONField = _models.JSONField


class Migration(migrations.Migration):

    dependencies = [
        ('notifications', '0002_auto_20150224_1134'),
    ]

    operations = [
        migrations.AddField(
            model_name='notification',
            name='data',
            field=jsonfield.fields.JSONField(null=True, blank=True),
            preserve_default=True,
        ),
    ]

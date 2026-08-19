from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('sample_notifications', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Tag',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=32)),
            ],
        ),
        migrations.AddField(
            model_name='notification',
            name='attachment',
            field=models.FileField(blank=True, upload_to='attachments/'),
        ),
        migrations.AddField(
            model_name='notification',
            name='tags',
            field=models.ManyToManyField(blank=True, related_name='notifications', to='sample_notifications.tag'),
        ),
    ]

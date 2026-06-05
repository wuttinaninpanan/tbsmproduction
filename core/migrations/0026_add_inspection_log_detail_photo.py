import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0025_add_inspection_ok_ng_log'),
    ]

    operations = [
        migrations.CreateModel(
            name='InspectionOKLogDetailPhoto',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_active', models.BooleanField(default=True)),
                ('image_path', models.TextField()),
                ('caption', models.CharField(blank=True, default='', max_length=100)),
                ('photo_order', models.PositiveSmallIntegerField(default=1)),
                ('detail', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='photos',
                    to='core.inspectionoklogdetail',
                )),
            ],
            options={
                'ordering': ['photo_order'],
            },
        ),
        migrations.CreateModel(
            name='InspectionNGLogDetailPhoto',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_active', models.BooleanField(default=True)),
                ('image_path', models.TextField()),
                ('caption', models.CharField(blank=True, default='', max_length=100)),
                ('photo_order', models.PositiveSmallIntegerField(default=1)),
                ('detail', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='photos',
                    to='core.inspectionnglogdetail',
                )),
            ],
            options={
                'ordering': ['photo_order'],
            },
        ),
    ]

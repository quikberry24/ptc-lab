from django.db import migrations


EN_MAP = {
    'Терапия': 'Therapy',
    'Хирургия': 'Surgery',
    'Кардиология': 'Cardiology',
    'Дерматология': 'Dermatology',
    'Стоматология': 'Dentistry',
    'Офтальмология': 'Ophthalmology',
    'Неврология': 'Neurology',
    'Эндокринология': 'Endocrinology',
    'Онкология': 'Oncology',
    'Реабилитация': 'Rehabilitation',
    'Диагностика': 'Diagnostics',
    'Урология': 'Urology',
    'Ортопедия': 'Orthopedics',
    'Гастроэнтерология': 'Gastroenterology',
    'Анестезиология': 'Anesthesiology',
    'Груминг': 'Grooming',
    'Грумминг': 'Grooming',
}


def forwards(apps, schema_editor):
    Specialty = apps.get_model('doctors', 'Specialty')
    for sp in Specialty.objects.all():
        sp.name_en = EN_MAP.get(sp.name, sp.name)
        sp.save(update_fields=['name_en'])


def backwards(apps, schema_editor):
    Specialty = apps.get_model('doctors', 'Specialty')
    Specialty.objects.update(name_en='')


class Migration(migrations.Migration):

    dependencies = [
        ('doctors', '0004_add_name_en_favorites'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]

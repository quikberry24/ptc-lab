from django.db import migrations


EN_MAP = {
    'Вакцинация 2': 'Vaccination 2',
    'Кастрация кота': 'Cat neutering',
    'Лечение аллергии': 'Allergy treatment',
    'Лечение конъюнктивита': 'Conjunctivitis treatment',
    'Осмотр офтальмолога': 'Ophthalmologist examination',
    'Первичный приём терапевта': 'Initial therapist appointment',
    'Повторный приём терапевта': 'Follow-up therapist appointment',
    'Приём дерматолога': 'Dermatologist appointment',
    'Стерилизация кошки': 'Cat spaying',
    'Удаление зуба': 'Tooth extraction',
    'Удаление новообразования': 'Tumor removal',
    'Ультразвуковая чистка зубов': 'Ultrasonic teeth cleaning',
    'ЭКГ': 'ECG',
    'ЭхоКГ': 'Echocardiography',
    # Fallbacks для возможных будущих сидов
    'Консультация': 'Consultation',
    'Вакцинация': 'Vaccination',
    'Стрижка когтей': 'Nail trimming',
    'Чистка зубов': 'Teeth cleaning',
    'УЗИ': 'Ultrasound',
    'Рентген': 'X-ray',
    'Анализы': 'Lab tests',
    'Стерилизация': 'Spaying',
    'Кастрация': 'Neutering',
    'Чипирование': 'Microchipping',
    'Хирургия': 'Surgery',
    'Терапия': 'Therapy',
    'Груминг': 'Grooming',
    'Диагностика': 'Diagnostics',
}


def forwards(apps, schema_editor):
    Service = apps.get_model('services', 'Service')
    for srv in Service.objects.all():
        srv.name_en = EN_MAP.get(srv.name, srv.name)
        srv.save(update_fields=['name_en'])


def backwards(apps, schema_editor):
    Service = apps.get_model('services', 'Service')
    Service.objects.update(name_en='')


class Migration(migrations.Migration):

    dependencies = [
        ('services', '0003_service_name_en'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]

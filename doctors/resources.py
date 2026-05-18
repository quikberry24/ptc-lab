from import_export import fields, resources
from import_export.widgets import ForeignKeyWidget

from doctors.models import Doctor
from users.models import User


class DoctorResource(resources.ModelResource):
    """Экспорт справочника врачей в Excel/CSV. Только read-only поля + email."""
    email = fields.Field(
        column_name='email',
        attribute='user',
        widget=ForeignKeyWidget(User, 'email'),
        readonly=True,
    )
    full_name = fields.Field(column_name='ФИО', readonly=True)
    specialties_list = fields.Field(column_name='специализации', readonly=True)

    class Meta:
        model = Doctor
        fields = (
            'id', 'email', 'full_name',
            'experience_years', 'consultation_price', 'is_available',
            'specialties_list',
        )
        export_order = fields

    def dehydrate_full_name(self, doctor: Doctor) -> str:
        full = doctor.user.get_full_name().strip()
        return full or doctor.user.email

    def dehydrate_specialties_list(self, doctor: Doctor) -> str:
        return ', '.join(s.name for s in doctor.specialties.all())

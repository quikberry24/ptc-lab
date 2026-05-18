from import_export import fields, resources
from import_export.widgets import ForeignKeyWidget

from doctors.models import Specialty
from services.models import Service


class ServiceResource(resources.ModelResource):
    """
    Импорт/экспорт каталога услуг. Поддерживает массовое обновление прайса:
    выгрузил xlsx → отредактировал цены → залил обратно.
    """
    specialty = fields.Field(
        column_name='специализация',
        attribute='specialty',
        widget=ForeignKeyWidget(Specialty, 'name'),
    )

    class Meta:
        model = Service
        fields = (
            'id', 'name', 'name_en', 'description',
            'price', 'duration_minutes', 'specialty', 'is_active',
        )
        export_order = fields
        import_id_fields = ('id',)

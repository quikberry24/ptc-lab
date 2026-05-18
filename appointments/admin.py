import io

from django.contrib import admin
from django.http import HttpResponse
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from simple_history.admin import SimpleHistoryAdmin

from .models import Appointment, MedicalRecord
from .pdf_utils import register_fonts


@admin.register(Appointment)
class AppointmentAdmin(SimpleHistoryAdmin):
    history_list_display = ['status']
    list_display = ('__str__', 'client', 'doctor', 'service', 'date', 'status', 'show_is_upcoming')
    list_display_links = ('__str__',)
    list_filter = ('status', 'date')
    search_fields = ('client__email', 'doctor__user__last_name', 'pet__name')
    raw_id_fields = ('client', 'doctor', 'pet', 'service')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'date'

    @admin.display(description='Предстоит', boolean=True)
    def show_is_upcoming(self, obj):
        return obj.is_upcoming()

    @admin.action(description='Экспортировать в PDF')
    def export_pdf(self, request, queryset):
        font_regular, font_bold = register_fonts()

        buf = io.BytesIO()
        p = canvas.Canvas(buf, pagesize=A4)
        width, height = A4
        y = height - 50

        p.setFont(font_bold, 16)
        p.drawString(50, y, 'PetCare — экспорт записей на приём')
        y -= 40

        p.setFont(font_regular, 10)
        for apt in queryset:
            if y < 50:
                p.showPage()
                p.setFont(font_regular, 10)
                y = height - 50
            p.drawString(50, y, f'{apt.date} | {apt.client} | {apt.doctor} | {apt.service} | {apt.get_status_display()}')
            y -= 18

        p.showPage()
        p.save()
        buf.seek(0)

        response = HttpResponse(buf, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="appointments.pdf"'
        return response

    @admin.action(description='Подтвердить выбранные')
    def mark_confirmed(self, request, queryset):
        updated = queryset.filter(status=Appointment.Status.PENDING).update(
            status=Appointment.Status.CONFIRMED,
        )
        self.message_user(request, f'Подтверждено записей: {updated}')

    @admin.action(description='Пометить завершёнными')
    def mark_completed(self, request, queryset):
        updated = queryset.filter(
            status__in=[Appointment.Status.CONFIRMED, Appointment.Status.IN_PROGRESS],
        ).update(status=Appointment.Status.COMPLETED)
        self.message_user(request, f'Завершено записей: {updated}')

    @admin.action(description='Отменить выбранные')
    def mark_cancelled(self, request, queryset):
        updated = queryset.exclude(
            status__in=[Appointment.Status.COMPLETED, Appointment.Status.CANCELLED],
        ).update(status=Appointment.Status.CANCELLED)
        self.message_user(request, f'Отменено записей: {updated}')

    actions = ['export_pdf', 'mark_confirmed', 'mark_completed', 'mark_cancelled']


@admin.register(MedicalRecord)
class MedicalRecordAdmin(SimpleHistoryAdmin):
    history_list_display = ['diagnosis', 'treatment']
    list_display = ('__str__', 'pet', 'doctor', 'date', 'show_diagnosis_short', 'created_at')
    list_filter = ('date', 'doctor')
    search_fields = ('diagnosis', 'treatment', 'pet__name', 'pet__owner__email')
    raw_id_fields = ('appointment', 'pet', 'doctor')
    readonly_fields = ('created_at',)
    fieldsets = (
        (None, {'fields': ('pet', 'appointment', 'doctor', 'date')}),
        ('Данные приёма', {'fields': ('diagnosis', 'treatment', 'recommendations', 'attachment')}),
        ('Служебное', {'fields': ('created_at',)}),
    )

    @admin.display(description='Диагноз (кратко)')
    def show_diagnosis_short(self, obj):
        if len(obj.diagnosis) > 80:
            return obj.diagnosis[:80] + '...'
        return obj.diagnosis

    def save_model(self, request, obj, form, change):
        if obj.appointment_id and not change:
            if not obj.pet_id:
                obj.pet_id = obj.appointment.pet_id
            if not obj.doctor_id:
                obj.doctor_id = obj.appointment.doctor_id
            if not obj.date:
                obj.date = obj.appointment.date
        obj.full_clean()
        super().save_model(request, obj, form, change)

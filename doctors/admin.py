from django.contrib import admin
from import_export.admin import ImportExportModelAdmin

from .models import Specialty, Doctor, DoctorSpecialty, Schedule
from .resources import DoctorResource


@admin.register(Specialty)
class SpecialtyAdmin(admin.ModelAdmin):
    list_display = ('name', 'name_en', 'show_doctors_count')
    search_fields = ('name', 'name_en')

    @admin.display(description='Врачей')
    def show_doctors_count(self, obj):
        return obj.doctors.count()


class ScheduleInline(admin.TabularInline):
    model = Schedule
    extra = 1


class DoctorSpecialtyInline(admin.TabularInline):
    model = DoctorSpecialty
    extra = 1


@admin.register(Doctor)
class DoctorAdmin(ImportExportModelAdmin):
    resource_classes = [DoctorResource]
    list_display = ('__str__', 'get_email', 'experience_years', 'consultation_price', 'is_available')
    list_display_links = ('__str__', 'get_email')
    list_filter = ('is_available', 'specialties')
    search_fields = ('user__first_name', 'user__last_name', 'user__email')
    raw_id_fields = ('user',)
    readonly_fields = ('get_email',)
    inlines = [DoctorSpecialtyInline, ScheduleInline]

    @admin.display(description='Email')
    def get_email(self, obj):
        return obj.user.email


@admin.register(Schedule)
class ScheduleAdmin(admin.ModelAdmin):
    list_display = ('doctor', 'day_of_week', 'start_time', 'end_time')
    list_filter = ('day_of_week',)
    raw_id_fields = ('doctor',)

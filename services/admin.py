from django.contrib import admin
from import_export.admin import ImportExportModelAdmin

from services.models import Service
from services.resources import ServiceResource


@admin.register(Service)
class ServiceAdmin(ImportExportModelAdmin):
    resource_classes = [ServiceResource]
    list_display = ('name', 'name_en', 'price', 'duration_minutes', 'specialty', 'is_active')
    list_display_links = ('name',)
    list_filter = ('is_active', 'specialty')
    search_fields = ('name', 'name_en', 'description')

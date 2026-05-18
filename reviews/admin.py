from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from .models import Review


@admin.register(Review)
class ReviewAdmin(SimpleHistoryAdmin):
    history_list_display = ['is_approved', 'rating']
    list_display = ('author', 'doctor', 'rating', 'is_approved', 'created_at')
    list_display_links = ('author',)
    list_filter = ('is_approved', 'rating')
    search_fields = ('author__email', 'text', 'doctor__user__last_name')
    raw_id_fields = ('author', 'doctor', 'appointment')
    readonly_fields = ('created_at', 'updated_at')

    @admin.action(description='Одобрить выбранные отзывы')
    def approve_reviews(self, request, queryset):
        updated = queryset.update(is_approved=True)
        self.message_user(request, f'Одобрено отзывов: {updated}')

    actions = [approve_reviews]

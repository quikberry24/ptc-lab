from django.db.models import Count, Q
from django.shortcuts import render

from appointments.models import Appointment
from doctors.models import Doctor, Specialty
from reviews.models import Review
from services.models import Service


def _site_stats() -> dict:
    return {
        'doctors_total': Doctor.objects.available().count(),
        'services_total': Service.objects.filter(is_active=True).count(),
        'completed_appointments': Appointment.objects.filter(
            status=Appointment.Status.COMPLETED,
        ).count(),
        'specialties_total': Specialty.objects.count(),
    }


def index(request):
    """
    Главная страница. Виджеты:
      - Статистика (счётчики из 4 таблиц)
      - Топ врачей (weighted ranking — сложная бизнес-логика)
      - Популярные услуги (агрегат Count)
      - Ближайшие свободные приёмы (Schedule × Appointment — даты + 2 доп. таблицы)
      - Направления (Specialty с агрегатом + distinct)
      - Свежие одобренные отзывы
    """
    return render(request, 'index.html', {
        'top_doctors': Doctor.objects.top_weighted(limit=5),
        'popular_services': (
            Service.objects
            .filter(is_active=True)
            .annotate(popularity=Count('appointments'))
            .order_by('-popularity', 'name')[:5]
        ),
        'free_slots': Doctor.objects.next_free_slots(limit=5),
        'latest_reviews': (
            Review.approved
            .select_related('author', 'doctor__user')
            .order_by('-created_at')[:3]
        ),
        'specialties': (
            Specialty.objects
            .annotate(doctors_count=Count('doctors'))
            .exclude(doctors_count=0)
            .order_by('-doctors_count', 'name')[:6]
        ),
        'stats': _site_stats(),
    })


def _ci_q(field: str, query: str) -> Q:
    """
    Case-insensitive contains для SQLite + кириллицы.
    Дефолтный __icontains в SQLite опускает регистр только для ASCII,
    поэтому собираем OR по всем вариантам регистра запроса.
    """
    variants = {query, query.lower(), query.upper(), query.capitalize(), query.title()}
    expr = Q()
    for v in variants:
        if v:
            expr |= Q(**{f'{field}__contains': v})
    return expr


def search(request):
    query = request.GET.get('q', '').strip()
    doctors = []
    services = []
    specialties = []

    if query:
        doctors = (
            Doctor.objects.available()
            .filter(
                _ci_q('user__first_name', query)
                | _ci_q('user__last_name', query)
                | _ci_q('bio', query)
            )
            .select_related('user')
            .distinct()[:10]
        )
        services = (
            Service.objects
            .filter(is_active=True)
            .filter(
                _ci_q('name', query)
                | _ci_q('name_en', query)
                | _ci_q('description', query)
            )[:10]
        )
        specialties = (
            Specialty.objects
            .filter(
                _ci_q('name', query)
                | _ci_q('name_en', query)
                | _ci_q('description', query)
            )[:10]
        )

    return render(request, 'search.html', {
        'query': query,
        'doctors': doctors,
        'services': services,
        'specialties': specialties,
    })

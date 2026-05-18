from datetime import date, time, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from appointments.models import Appointment
from doctors.models import Doctor, Schedule, Specialty
from doctors.scheduling import get_available_slots
from pets.models import Pet
from reviews.models import Review
from services.models import Service


User = get_user_model()


class AvailableSlotsTest(TestCase):
    def setUp(self):
        self.doctor_user = User.objects.create_user(
            email='doc@test.ru', password='pass1234', role='veterinarian',
            first_name='Тест', last_name='Доктор',
        )
        self.doctor = Doctor.objects.create(
            user=self.doctor_user, experience_years=5,
            consultation_price=Decimal('1000'),
        )
        for day in range(7):
            Schedule.objects.create(
                doctor=self.doctor, day_of_week=day,
                start_time=time(9, 0), end_time=time(12, 0),
            )

    def test_returns_slots(self):
        slots = get_available_slots(self.doctor, days_ahead=2)
        self.assertGreater(len(slots), 0)

    def test_excludes_busy_slot(self):
        from appointments.models import Appointment
        from pets.models import Pet
        from services.models import Service

        client_user = User.objects.create_user(email='c@t.ru', password='p')
        pet = Pet.objects.create(owner=client_user, name='P', species='cat', age=24)
        svc = Service.objects.create(
            name='S', price=Decimal('100'), duration_minutes=30,
        )
        tomorrow = timezone.localtime().date() + timedelta(days=1)
        Appointment.objects.create(
            client=client_user, doctor=self.doctor, pet=pet, service=svc,
            date=tomorrow, time_slot=time(9, 0), status='confirmed',
        )
        slots = get_available_slots(self.doctor, days_ahead=2)
        match = [s for s in slots if s['date'] == tomorrow and s['time'] == time(9, 0)]
        self.assertEqual(match, [])


class TopDoctorsWeightedTest(TestCase):
    """
    Weighted ranking учитывает и средний рейтинг, и количество отзывов.
    Доктор с 1 отзывом 5/5 не должен побеждать доктора с 20 отзывами по 4.
    """

    def setUp(self):
        self.specialty = Specialty.objects.create(name='Терапия-test')
        self.service = Service.objects.create(
            name='Консультация-test', price=Decimal('1000'),
            specialty=self.specialty,
        )

    def _create_doctor(self, suffix: str) -> Doctor:
        user = User.objects.create_user(
            email=f'doc-{suffix}@p.ru', password='x',
            first_name='Doc', last_name=suffix,
            role='veterinarian',
        )
        return Doctor.objects.create(user=user, experience_years=1)

    def _give_review(self, doctor: Doctor, rating: int) -> Review:
        idx = Review.objects.count() + 1
        client = User.objects.create_user(email=f'cli-{idx}@p.ru', password='x')
        pet = Pet.objects.create(owner=client, name=f'P{idx}', species='cat', age=12)
        apt = Appointment.objects.create(
            client=client, doctor=doctor, pet=pet, service=self.service,
            date=date(2026, 1, 1), time_slot=time(10, 0),
            status=Appointment.Status.COMPLETED,
        )
        return Review.objects.create(
            author=client, doctor=doctor, appointment=apt,
            rating=rating, text='ok', is_approved=True,
        )

    def test_many_reviews_4_beats_one_review_5(self):
        weak = self._create_doctor('weak')
        self._give_review(weak, 5)  # 1 отзыв, avg=5.0

        strong = self._create_doctor('strong')
        for _ in range(20):
            self._give_review(strong, 4)  # 20 отзывов, avg=4.0

        top = list(Doctor.objects.top_weighted(limit=5))
        self.assertGreater(len(top), 0)
        self.assertEqual(
            top[0].pk, strong.pk,
            'врач с 20 отзывами по 4 должен обходить врача с одним 5/5',
        )


class FreeSlotsWidgetTest(TestCase):
    """Виджет «Ближайшие свободные приёмы» возвращает доктора со слотом на день."""

    def test_returns_doctor_with_today_schedule(self):
        u = User.objects.create_user(
            email='free@p.ru', password='x',
            first_name='Free', last_name='Doc', role='veterinarian',
        )
        d = Doctor.objects.create(user=u, experience_years=1, is_available=True)
        today = timezone.localtime().date()
        Schedule.objects.create(
            doctor=d, day_of_week=today.weekday(),
            start_time=time(10, 0), end_time=time(18, 0),
        )
        slots = list(Doctor.objects.next_free_slots(limit=5))
        self.assertTrue(
            any(s['doctor'].pk == d.pk for s in slots),
            'свободный врач со слотом на сегодня должен попасть в виджет',
        )

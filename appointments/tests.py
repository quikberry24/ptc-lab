from datetime import date, time, timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from users.models import User
from doctors.models import Doctor, Specialty
from pets.models import Pet
from services.models import Service
from appointments.models import Appointment, MedicalRecord


class MedicalRecordPdfAuthzTest(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            email='owner@test.ru', password='pwd12345',
            first_name='Owner', last_name='Test',
        )
        self.stranger = User.objects.create_user(
            email='stranger@test.ru', password='pwd12345',
            first_name='Stranger', last_name='Test',
        )
        vet_user = User.objects.create_user(
            email='vet@test.ru', password='pwd12345',
            first_name='Vet', last_name='Test',
            role=User.Role.VETERINARIAN,
        )
        specialty = Specialty.objects.create(name='Терапия')
        self.doctor = Doctor.objects.create(user=vet_user, consultation_price=Decimal('1000'))
        self.doctor.specialties.add(specialty)
        self.pet = Pet.objects.create(owner=self.owner, name='Барсик', species='cat', age=24)
        self.service = Service.objects.create(name='Осмотр', price=Decimal('1000'), duration_minutes=30)
        self.appointment = Appointment.objects.create(
            client=self.owner, doctor=self.doctor, pet=self.pet, service=self.service,
            date=date.today() - timedelta(days=1), time_slot=time(10, 0),
            status=Appointment.Status.COMPLETED,
        )
        self.record = MedicalRecord.objects.create(
            appointment=self.appointment, pet=self.pet, doctor=self.doctor,
            diagnosis='test', treatment='test',
        )

    def test_owner_can_download_pdf(self):
        self.client.force_login(self.owner)
        response = self.client.get(reverse('medical-record-pdf', args=[self.record.pk]))
        self.assertEqual(response.status_code, 200)

    def test_stranger_cannot_download_pdf(self):
        self.client.force_login(self.stranger)
        response = self.client.get(reverse('medical-record-pdf', args=[self.record.pk]))
        self.assertEqual(response.status_code, 404)


class MedicalRecordValidationTest(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(email='o@test.ru', password='pwd12345')
        other_owner = User.objects.create_user(email='other@test.ru', password='pwd12345')
        vet_user = User.objects.create_user(
            email='v@test.ru', password='pwd12345', role=User.Role.VETERINARIAN,
        )
        other_vet = User.objects.create_user(
            email='ov@test.ru', password='pwd12345', role=User.Role.VETERINARIAN,
        )
        specialty = Specialty.objects.create(name='Терапия')
        self.doctor = Doctor.objects.create(user=vet_user, consultation_price=Decimal('1000'))
        self.other_doctor = Doctor.objects.create(user=other_vet, consultation_price=Decimal('1000'))
        self.pet = Pet.objects.create(owner=self.owner, name='Барсик', species='cat', age=24)
        self.other_pet = Pet.objects.create(owner=other_owner, name='Мурка', species='cat', age=12)
        self.service = Service.objects.create(name='Осмотр', price=Decimal('1000'), duration_minutes=30)
        self.completed_apt = Appointment.objects.create(
            client=self.owner, doctor=self.doctor, pet=self.pet, service=self.service,
            date=date.today() - timedelta(days=1), time_slot=time(10, 0),
            status=Appointment.Status.COMPLETED,
        )
        self.pending_apt = Appointment.objects.create(
            client=self.owner, doctor=self.doctor, pet=self.pet, service=self.service,
            date=date.today() + timedelta(days=1), time_slot=time(11, 0),
            status=Appointment.Status.PENDING,
        )

    def test_record_without_appointment_is_valid(self):
        record = MedicalRecord(
            pet=self.pet, doctor=self.doctor,
            date=date.today(), diagnosis='standalone',
        )
        record.full_clean()

    def test_pet_mismatch_raises(self):
        record = MedicalRecord(
            appointment=self.completed_apt,
            pet=self.other_pet, doctor=self.doctor,
            date=date.today(), diagnosis='wrong pet',
        )
        with self.assertRaises(ValidationError) as ctx:
            record.full_clean()
        self.assertIn('pet', ctx.exception.error_dict)

    def test_doctor_mismatch_raises(self):
        record = MedicalRecord(
            appointment=self.completed_apt,
            pet=self.pet, doctor=self.other_doctor,
            date=date.today(), diagnosis='wrong doctor',
        )
        with self.assertRaises(ValidationError) as ctx:
            record.full_clean()
        self.assertIn('doctor', ctx.exception.error_dict)

    def test_pending_appointment_rejected(self):
        record = MedicalRecord(
            appointment=self.pending_apt,
            pet=self.pet, doctor=self.doctor,
            date=date.today(), diagnosis='too early',
        )
        with self.assertRaises(ValidationError) as ctx:
            record.full_clean()
        self.assertIn('appointment', ctx.exception.error_dict)


class AppointmentSlotUniqueTest(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(email='o@test.ru', password='pwd12345')
        self.other = User.objects.create_user(email='o2@test.ru', password='pwd12345')
        vet_user = User.objects.create_user(
            email='v@test.ru', password='pwd12345', role=User.Role.VETERINARIAN,
        )
        self.doctor = Doctor.objects.create(user=vet_user, consultation_price=Decimal('1000'))
        self.pet1 = Pet.objects.create(owner=self.owner, name='A', species='cat', age=12)
        self.pet2 = Pet.objects.create(owner=self.other, name='B', species='cat', age=12)
        self.service = Service.objects.create(name='S', price=Decimal('1000'), duration_minutes=30)

    def test_same_slot_different_clients_rejected(self):
        from django.db import IntegrityError
        Appointment.objects.create(
            client=self.owner, doctor=self.doctor, pet=self.pet1, service=self.service,
            date=date.today() + timedelta(days=1), time_slot=time(10, 0),
            status=Appointment.Status.CONFIRMED,
        )
        with self.assertRaises(IntegrityError):
            Appointment.objects.create(
                client=self.other, doctor=self.doctor, pet=self.pet2, service=self.service,
                date=date.today() + timedelta(days=1), time_slot=time(10, 0),
                status=Appointment.Status.CONFIRMED,
            )

    def test_cancelled_slot_does_not_block(self):
        Appointment.objects.create(
            client=self.owner, doctor=self.doctor, pet=self.pet1, service=self.service,
            date=date.today() + timedelta(days=1), time_slot=time(10, 0),
            status=Appointment.Status.CANCELLED,
        )
        Appointment.objects.create(
            client=self.other, doctor=self.doctor, pet=self.pet2, service=self.service,
            date=date.today() + timedelta(days=1), time_slot=time(10, 0),
            status=Appointment.Status.CONFIRMED,
        )


class AppointmentFormScheduleTest(TestCase):
    def setUp(self):
        from doctors.models import Schedule
        self.owner = User.objects.create_user(email='o@test.ru', password='pwd12345')
        vet_user = User.objects.create_user(
            email='v@test.ru', password='pwd12345', role=User.Role.VETERINARIAN,
        )
        self.doctor = Doctor.objects.create(user=vet_user, consultation_price=Decimal('1000'))
        self.pet = Pet.objects.create(owner=self.owner, name='Барсик', species='cat', age=12)
        self.service = Service.objects.create(name='Осмотр', price=Decimal('1000'), duration_minutes=30)
        Schedule.objects.create(
            doctor=self.doctor, day_of_week=0,
            start_time=time(9, 0), end_time=time(18, 0),
        )

    def _next_weekday(self, target_weekday):
        d = date.today() + timedelta(days=1)
        while d.weekday() != target_weekday:
            d += timedelta(days=1)
        return d

    def _form(self, **overrides):
        from appointments.forms import AppointmentForm
        data = {
            'doctor': self.doctor.pk,
            'pet': self.pet.pk,
            'service': self.service.pk,
            'date': self._next_weekday(0),
            'time_slot': '10:00',
            'comment': '',
        }
        data.update(overrides)
        return AppointmentForm(data=data, user=self.owner)

    def test_form_rejects_day_without_schedule(self):
        form = self._form(date=self._next_weekday(6))
        self.assertFalse(form.is_valid())

    def test_form_rejects_time_outside_schedule(self):
        form = self._form(time_slot='03:00')
        self.assertFalse(form.is_valid())

    def test_form_accepts_valid_slot(self):
        form = self._form()
        self.assertTrue(form.is_valid(), form.errors)


class AppointmentModelTest(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(email='o@test.ru', password='pwd12345')
        vet_user = User.objects.create_user(
            email='v@test.ru', password='pwd12345', role=User.Role.VETERINARIAN,
        )
        self.doctor = Doctor.objects.create(user=vet_user, consultation_price=Decimal('1000'))
        self.pet = Pet.objects.create(owner=self.owner, name='A', species='cat', age=12)
        self.service = Service.objects.create(name='S', price=Decimal('1000'), duration_minutes=30)

    def _make(self, status, offset_days=1, slot_hour=10):
        return Appointment.objects.create(
            client=self.owner, doctor=self.doctor, pet=self.pet, service=self.service,
            date=date.today() + timedelta(days=offset_days),
            time_slot=time(slot_hour, 0), status=status,
        )

    def test_can_cancel_pending(self):
        self.assertTrue(self._make(Appointment.Status.PENDING).can_cancel())

    def test_can_cancel_confirmed(self):
        self.assertTrue(self._make(Appointment.Status.CONFIRMED, slot_hour=11).can_cancel())

    def test_cannot_cancel_completed(self):
        self.assertFalse(self._make(Appointment.Status.COMPLETED, offset_days=-1).can_cancel())

    def test_is_upcoming_for_future_pending(self):
        self.assertTrue(self._make(Appointment.Status.PENDING, offset_days=5, slot_hour=12).is_upcoming())

    def test_not_upcoming_if_cancelled(self):
        self.assertFalse(self._make(Appointment.Status.CANCELLED, offset_days=5, slot_hour=13).is_upcoming())

    def test_not_upcoming_if_past(self):
        self.assertFalse(self._make(Appointment.Status.CONFIRMED, offset_days=-3, slot_hour=14).is_upcoming())


class AppointmentHistoryTest(TestCase):
    """django-simple-history фиксирует все изменения Appointment."""

    def setUp(self):
        self.client_user = User.objects.create_user(email='c@p.ru', password='x')
        doc_user = User.objects.create_user(
            email='doc@p.ru', password='x',
            first_name='D', last_name='X', role='veterinarian',
        )
        self.doctor = Doctor.objects.create(user=doc_user, experience_years=1)
        self.pet = Pet.objects.create(
            owner=self.client_user, name='Pet', species='cat', age=12,
        )
        self.svc = Service.objects.create(name='X', price=Decimal('100'))

    def test_status_changes_tracked_in_history(self):
        apt = Appointment.objects.create(
            client=self.client_user, doctor=self.doctor,
            pet=self.pet, service=self.svc,
            date=date(2026, 12, 1), time_slot=time(10, 0),
            status=Appointment.Status.PENDING,
        )
        apt.status = Appointment.Status.CONFIRMED
        apt.save()
        apt.status = Appointment.Status.COMPLETED
        apt.save()
        history = list(apt.history.all().order_by('history_date'))
        self.assertEqual(len(history), 3)
        self.assertEqual(history[0].status, Appointment.Status.PENDING)
        self.assertEqual(history[1].status, Appointment.Status.CONFIRMED)
        self.assertEqual(history[-1].status, Appointment.Status.COMPLETED)

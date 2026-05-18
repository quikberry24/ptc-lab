from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models
from django.db.models import Q, UniqueConstraint
from django.urls import reverse
from django.utils import timezone
from simple_history.models import HistoricalRecords


class Appointment(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Ожидает'
        CONFIRMED = 'confirmed', 'Подтверждена'
        IN_PROGRESS = 'in_progress', 'В процессе'
        COMPLETED = 'completed', 'Завершена'
        CANCELLED = 'cancelled', 'Отменена'

    client = models.ForeignKey(
        'users.User', on_delete=models.CASCADE,
        related_name='appointments', verbose_name='клиент',
    )
    doctor = models.ForeignKey(
        'doctors.Doctor', on_delete=models.CASCADE,
        related_name='appointments', verbose_name='врач',
    )
    pet = models.ForeignKey(
        'pets.Pet', on_delete=models.CASCADE,
        related_name='appointments', verbose_name='питомец',
    )
    service = models.ForeignKey(
        'services.Service', on_delete=models.CASCADE,
        related_name='appointments', verbose_name='услуга',
    )
    date = models.DateField('дата приёма')
    time_slot = models.TimeField('время')
    status = models.CharField(
        'статус', max_length=20,
        choices=Status.choices, default=Status.PENDING,
    )
    comment = models.TextField('комментарий', blank=True)
    cancel_reason = models.TextField('причина отмены', blank=True)
    created_at = models.DateTimeField('создана', auto_now_add=True)
    updated_at = models.DateTimeField('обновлена', auto_now=True)

    history = HistoricalRecords()

    class Meta:
        verbose_name = 'запись на приём'
        verbose_name_plural = 'записи на приём'
        ordering = ['-date', '-time_slot']
        constraints = [
            UniqueConstraint(
                fields=['doctor', 'date', 'time_slot'],
                condition=Q(status__in=['pending', 'confirmed', 'in_progress']),
                name='unique_active_slot_per_doctor',
            ),
        ]

    def __str__(self):
        return f'Запись #{self.pk} — {self.client} к {self.doctor} ({self.date})'

    def get_absolute_url(self):
        return reverse('appointment-list')

    def can_cancel(self):
        return self.status in (self.Status.PENDING, self.Status.CONFIRMED)

    def is_upcoming(self):
        from datetime import datetime
        tz = timezone.get_current_timezone()
        appointment_dt = datetime.combine(self.date, self.time_slot, tzinfo=tz)
        return appointment_dt > timezone.now() and self.status != self.Status.CANCELLED


class MedicalRecord(models.Model):
    pet = models.ForeignKey(
        'pets.Pet', on_delete=models.CASCADE,
        related_name='medical_records', verbose_name='питомец',
    )
    appointment = models.OneToOneField(
        Appointment, on_delete=models.SET_NULL,
        related_name='medical_record', verbose_name='приём',
        null=True, blank=True,
    )
    doctor = models.ForeignKey(
        'doctors.Doctor', on_delete=models.PROTECT,
        related_name='medical_records', verbose_name='врач',
    )
    date = models.DateField('дата записи', default=timezone.now)
    diagnosis = models.TextField('диагноз')
    treatment = models.TextField('лечение', blank=True)
    recommendations = models.TextField('рекомендации', blank=True)
    attachment = models.FileField(
        'файл (анализы)', upload_to='medical_records/',
        blank=True, null=True,
        validators=[FileExtensionValidator(['pdf', 'jpg', 'jpeg', 'png'])],
    )
    created_at = models.DateTimeField('создана', auto_now_add=True)

    history = HistoricalRecords()

    class Meta:
        verbose_name = 'запись в медкарте'
        verbose_name_plural = 'медицинские карты'
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f'Карта {self.pet.name} от {self.date:%d.%m.%Y}'

    def clean(self):
        if self.appointment_id is None:
            return
        apt = self.appointment
        errors = {}
        if self.pet_id != apt.pet_id:
            errors['pet'] = 'Питомец не совпадает с питомцем в приёме'
        if self.doctor_id != apt.doctor_id:
            errors['doctor'] = 'Врач не совпадает с врачом в приёме'
        if apt.status != Appointment.Status.COMPLETED:
            errors['appointment'] = 'Медкарту можно создать только для завершённого приёма'
        if errors:
            raise ValidationError(errors)

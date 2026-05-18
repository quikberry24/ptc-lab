from datetime import date, timedelta

from django.core.validators import FileExtensionValidator
from django.db import models
from django.db.models import Avg, Count, ExpressionWrapper, F, FloatField
from django.db.models.functions import Ln
from django.urls import reverse


class DoctorQuerySet(models.QuerySet):
    def available(self):
        return self.filter(is_available=True)

    def with_rating_stats(self):
        return self.annotate(
            avg_rating=Avg('reviews__rating'),
            reviews_count=Count('reviews'),
        )

    def top_weighted(self, limit: int = 5):
        """
        Сортировка по avg_rating * ln(reviews_count + 1).
        Подавляет «5 звёзд при 1 отзыве» — врач с 20 отзывами по 4 обгоняет врача с одним 5/5.
        """
        return (
            self
            .available()
            .with_rating_stats()
            .exclude(avg_rating=None)
            .annotate(
                weighted_score=ExpressionWrapper(
                    F('avg_rating') * Ln(F('reviews_count') + 1.0),
                    output_field=FloatField(),
                )
            )
            .order_by('-weighted_score')
            .select_related('user')[:limit]
        )

    def next_free_slots(self, limit: int = 5, horizon_days: int = 7):
        """
        Ближайшие свободные слоты для записи на приём: dict-ы
        {doctor, date, start_time, end_time}, отсортированы по близости даты.
        Слот считается свободным, если у врача в этот день недели есть Schedule,
        и на эту дату нет активного Appointment.
        """
        from appointments.models import Appointment
        today = date.today()
        active_statuses = (
            Appointment.Status.PENDING,
            Appointment.Status.CONFIRMED,
            Appointment.Status.IN_PROGRESS,
        )
        result = []
        for offset in range(horizon_days):
            d = today + timedelta(days=offset)
            schedules = (
                Schedule.objects
                .select_related('doctor__user')
                .filter(
                    doctor__is_available=True,
                    day_of_week=d.weekday(),
                )
            )
            for sch in schedules:
                busy = Appointment.objects.filter(
                    doctor=sch.doctor,
                    date=d,
                    status__in=active_statuses,
                ).exists()
                if busy:
                    continue
                result.append({
                    'doctor': sch.doctor,
                    'date': d,
                    'start_time': sch.start_time,
                    'end_time': sch.end_time,
                })
                if len(result) >= limit:
                    return result
        return result


class Specialty(models.Model):
    name = models.CharField('название', max_length=100, unique=True)
    name_en = models.CharField('name (en)', max_length=100, blank=True, default='')
    description = models.TextField('описание', blank=True)
    icon = models.ImageField(
        'иконка', upload_to='specialties/', blank=True, null=True,
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png', 'svg', 'webp'])],
    )

    class Meta:
        verbose_name = 'специализация'
        verbose_name_plural = 'специализации'
        ordering = ['name']

    def __str__(self):
        return self.name


class Doctor(models.Model):
    user = models.OneToOneField(
        'users.User', on_delete=models.CASCADE,
        related_name='doctor_profile', verbose_name='пользователь'
    )
    specialties = models.ManyToManyField(
        Specialty, through='DoctorSpecialty',
        related_name='doctors', verbose_name='специализации', blank=True
    )
    experience_years = models.PositiveIntegerField('стаж (лет)', default=0)
    education = models.TextField('образование', blank=True)
    bio = models.TextField('о враче', blank=True)
    photo = models.ImageField(
        'фото', upload_to='doctors/', blank=True, null=True,
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png', 'webp'])],
    )
    consultation_price = models.DecimalField(
        'цена консультации', max_digits=10, decimal_places=2, default=0
    )
    is_available = models.BooleanField('доступен', default=True)
    favorited_by = models.ManyToManyField(
        'users.User', related_name='favorite_doctors',
        blank=True, verbose_name='в избранном у',
    )

    objects = DoctorQuerySet.as_manager()

    class Meta:
        verbose_name = 'врач'
        verbose_name_plural = 'врачи'
        ordering = ['-experience_years']

    def __str__(self):
        full_name = self.user.get_full_name().strip()
        return full_name or self.user.email

    def get_absolute_url(self):
        return reverse('doctor-detail', kwargs={'pk': self.pk})

    @property
    def meta_lines(self) -> list[str]:
        lines = [f'Стаж: {self.experience_years} лет']
        if getattr(self, 'avg_rating', None) is not None:
            lines.append(f'⭐ {self.avg_rating:.1f} ({getattr(self, "reviews_count", 0)} отзыв.)')
        lines.append(f'{self.consultation_price:.0f} руб.')
        return lines


class DoctorSpecialty(models.Model):
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, verbose_name='врач')
    specialty = models.ForeignKey(Specialty, on_delete=models.CASCADE, verbose_name='специализация')
    is_primary = models.BooleanField('основная', default=False)

    class Meta:
        verbose_name = 'специализация врача'
        verbose_name_plural = 'специализации врачей'
        unique_together = ('doctor', 'specialty')

    def __str__(self):
        return str(self.specialty)


class Schedule(models.Model):
    class DayOfWeek(models.IntegerChoices):
        MONDAY = 0, 'Понедельник'
        TUESDAY = 1, 'Вторник'
        WEDNESDAY = 2, 'Среда'
        THURSDAY = 3, 'Четверг'
        FRIDAY = 4, 'Пятница'
        SATURDAY = 5, 'Суббота'
        SUNDAY = 6, 'Воскресенье'

    doctor = models.ForeignKey(
        Doctor, on_delete=models.CASCADE,
        related_name='schedules', verbose_name='врач'
    )
    day_of_week = models.IntegerField('день недели', choices=DayOfWeek.choices)
    start_time = models.TimeField('начало')
    end_time = models.TimeField('конец')

    class Meta:
        verbose_name = 'расписание'
        verbose_name_plural = 'расписания'
        unique_together = ('doctor', 'day_of_week')
        ordering = ['day_of_week', 'start_time']

    def __str__(self):
        return self.get_day_of_week_display()

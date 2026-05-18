from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from simple_history.models import HistoricalRecords


class ApprovedReviewManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_approved=True)


class Review(models.Model):
    author = models.ForeignKey(
        'users.User', on_delete=models.CASCADE,
        related_name='reviews', verbose_name='автор'
    )
    doctor = models.ForeignKey(
        'doctors.Doctor', on_delete=models.CASCADE,
        related_name='reviews', verbose_name='врач'
    )
    appointment = models.OneToOneField(
        'appointments.Appointment', on_delete=models.CASCADE,
        related_name='review', verbose_name='запись',
    )
    rating = models.PositiveIntegerField(
        'оценка',
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    text = models.TextField('текст отзыва')
    is_approved = models.BooleanField('одобрен', default=False)
    created_at = models.DateTimeField('создан', auto_now_add=True)
    updated_at = models.DateTimeField('обновлён', auto_now=True)

    history = HistoricalRecords()

    objects = models.Manager()
    approved = ApprovedReviewManager()

    class Meta:
        verbose_name = 'отзыв'
        verbose_name_plural = 'отзывы'
        ordering = ['-created_at']

    def __str__(self):
        return f'Отзыв от {self.author} на {self.doctor} ({self.rating}/5)'

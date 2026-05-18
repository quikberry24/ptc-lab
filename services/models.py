from django.core.validators import FileExtensionValidator
from django.db import models
from django.urls import reverse


class Service(models.Model):
    name = models.CharField('название', max_length=200)
    name_en = models.CharField('name (en)', max_length=200, blank=True, default='')
    description = models.TextField('описание', blank=True)
    price = models.DecimalField('цена', max_digits=10, decimal_places=2)
    duration_minutes = models.PositiveIntegerField('длительность (мин.)', default=30)
    specialty = models.ForeignKey(
        'doctors.Specialty', on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='services', verbose_name='специализация'
    )
    photo = models.ImageField(
        'фото', upload_to='services/', blank=True, null=True,
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png', 'webp'])],
    )
    is_active = models.BooleanField('активна', default=True)

    class Meta:
        verbose_name = 'услуга'
        verbose_name_plural = 'услуги'
        ordering = ['name']

    def __str__(self):
        return f'{self.name} — {self.price} руб.'

    def get_absolute_url(self):
        return reverse('service-detail', kwargs={'pk': self.pk})

    @property
    def meta_lines(self) -> list[str]:
        popularity = getattr(self, 'popularity', None)
        if popularity:
            second = f'{self.duration_minutes} мин · {popularity} записей'
        else:
            second = f'{self.duration_minutes} мин · новая услуга'
        desc_preview = ''
        if self.description:
            desc_preview = self.description[:80] + ('...' if len(self.description) > 80 else '')
        lines = []
        if desc_preview:
            lines.append(desc_preview)
        lines.append(second)
        lines.append(f'{self.price:.0f} руб.')
        return lines

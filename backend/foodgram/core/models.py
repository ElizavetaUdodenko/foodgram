from django.db import models


class TimeStampedModel(models.Model):

    created_at = models.DateTimeField(
        auto_now_add=True,
        editable=False,
        verbose_name='Добавлено'
    )

    class Meta:
        abstract = True
        ordering = ('created_at', )

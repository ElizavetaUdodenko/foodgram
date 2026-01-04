from django.contrib.auth.models import AbstractUser
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.db import models

from .constants import EMAIL_MAX_LENGTH, NAME_MAX_LENGTH
from .validators import validate_not_me


def avatar_file_name(instance, filename):
    return ''.join(['users/', str(instance.pk), '_', filename])


class User(AbstractUser):

    username = models.CharField(
        max_length=NAME_MAX_LENGTH,
        unique=True,
        blank=False,
        null=False,
        validators=[validate_not_me, UnicodeUsernameValidator()],
        help_text='Имя пользователя не может быть "me".',
        verbose_name='Имя пользователя'
    )
    email = models.EmailField(
        max_length=EMAIL_MAX_LENGTH,
        unique=True,
        blank=False,
        null=False
    )
    avatar = models.ImageField(
        'Аватар',
        upload_to=avatar_file_name,
        null=True,
        default=None
    )
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
        ordering = ('username',)
        constraints = [
            models.UniqueConstraint(
                fields=['username', 'email'],
                name='unique_username_email'
            )
        ]

    def __str__(self):
        return self.username

    def delete_avatar(self):
        if self.avatar:
            self.avatar.delete(save=False)
            self.avatar = None
            self.save()

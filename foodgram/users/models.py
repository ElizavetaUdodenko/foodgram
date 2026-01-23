from django.contrib.auth.models import AbstractUser
from django.db import models

from .constants import NAME_MAX_LENGTH


def avatar_file_name(instance, filename):
    return ''.join(['users/', str(instance.pk), '_', filename])


class User(AbstractUser):

    first_name = models.CharField(
        'First Name',
        max_length=NAME_MAX_LENGTH
    )
    last_name = models.CharField(
        'Last Name',
        max_length=NAME_MAX_LENGTH
    )
    email = models.EmailField(
        'Email',
        unique=True
    )
    avatar = models.ImageField(
        'Avatar',
        upload_to=avatar_file_name,
        null=True,
        default=None
    )
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ('username',)

    def __str__(self):
        return self.username


class Follow(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='follows',
        verbose_name='User'
    )
    follows = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='followers',
        verbose_name='Subscription'
    )

    class Meta:
        verbose_name = 'Subscription'
        verbose_name_plural = 'Subscriptions'
        ordering = ('user',)
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'follows'], name='unique_follow'
            ),
            models.CheckConstraint(
                check=~models.Q(user=models.F('follows')),
                name='restrict_self_follow'
            )
        ]

    def __str__(self):
        return f'{self.user.username} -> {self.follows.username}'

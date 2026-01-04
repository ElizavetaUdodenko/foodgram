from django.core.exceptions import ValidationError

from .constants import FORBIDDEN_USERNAMES


def validate_not_me(value: str):
    if value.lower() in FORBIDDEN_USERNAMES:
        raise ValidationError(f'Имя пользователя не может быть "{value}".')

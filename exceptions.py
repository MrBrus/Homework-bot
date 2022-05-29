class TelegramException(Exception):
    """Исклбчение для проверки работоспособности Телеграм"""

    pass


class StatusException(Exception):
    """Исключение для проверки статуса в ответе API."""

    pass


class GetAPIException(Exception):
    """Исключение для проверки запроса к API."""

    pass

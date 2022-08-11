class NoValidAnswerException(Exception):
    """Обработка исключений некорректного ответа."""

    pass


class ApiRequestException(Exception):
    """Обработка исключений ответа API."""

    pass

class SendMessageError(Exception):
    """Обработка исключений отправки сообщений"""

    pass

class NoValidTokensException(Exception):
    """Проверка наличия токенов"""

    pass

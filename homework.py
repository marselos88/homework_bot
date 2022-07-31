import os
from sys import stdout
import requests
from dotenv import load_dotenv
import time
from telegram import Bot
import logging
import http


load_dotenv()

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s, %(levelname)s, %(message)s, %(name)s'
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(stream=stdout)
logger.addHandler(handler)

URL = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
RETRY_TIME = 600
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

HOMEWORK_TEMPLATE = {
    "id": 124,
    "status": "rejected",
    "homework_name": "username__hw_python_oop.zip",
    "reviewer_comment": "Код не по PEP8, нужно исправить",
    "date_updated": "2020-02-13T16:42:47Z",
    "lesson_name": "Итоговый проект"
}

HOMEWORK_DB = {}


class NoValidAnswerException(Exception):
    """Обработка исключений некорректного ответа."""

    pass


class ApiRequestException(Exception):
    """Обработка исключений ответа API."""

    pass


def send_message(bot, message):
    """Отправить сообщение."""
    chat_id = TELEGRAM_CHAT_ID
    bot.send_message(chat_id, message)


def get_api_answer(current_timestamp=None):
    """Обратиться к API practicum."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    headers = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
    try:
        request = requests.get(URL, headers=headers, params=params)
    except Exception as e:
        raise ApiRequestException(e)
    if request.status_code != http.HTTPStatus.OK:
        raise ApiRequestException('API возвращает код, отличный от 200')
    return request.json()


def check_response(response):
    """Проверка ответа от API."""
    if not type(response['homeworks']) == list:
        raise NoValidAnswerException('В ответе отсутствует список работ')
    return response['homeworks']


def parse_status(homework):
    """Проверить сменился ли статус работы."""
    if homework["id"] in HOMEWORK_DB:
        old_status = HOMEWORK_DB["id"]
    else:
        old_status = None
    current_status = homework["status"]
    if old_status != current_status:
        HOMEWORK_DB["status"] = current_status
        homework_name = homework["homework_name"]
        verdict = HOMEWORK_STATUSES.get(current_status)
        message = (f'Изменился статус проверки работы'
                   f' "{homework_name}". {verdict}')
    else:
        message = ''
    return message


def check_tokens() -> bool:
    """Проверить наличие токенов."""
    return all((PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID))


def main():
    """Основная логика работы бота."""
    prev_timestamp = int(time.time()) - RETRY_TIME
    bot = Bot(token=TELEGRAM_TOKEN)
    while True:
        try:
            practicum_response = get_api_answer(prev_timestamp)
            print(practicum_response)
            homework_list = check_response(practicum_response)
            prev_timestamp = practicum_response["current_date"]
            for homework in homework_list:
                message = parse_status(homework)
                if message:
                    send_message(bot, message)
            time.sleep(RETRY_TIME)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
            time.sleep(RETRY_TIME)
            continue


if __name__ == '__main__':
    main()

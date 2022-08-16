import http
import logging
import os
import time
from sys import stdout

import requests
from dotenv import load_dotenv
from telegram import Bot

from exeptions import (ApiRequestException, NoValidAnswerException,
                       SendMessageError)

load_dotenv()

LOG_FORMAT = (
    '%(asctime)s, %(levelname)s, %(funcName)s,'
    '%(lineno)s, %(message)s, %(name)s'
)
logging.basicConfig(
    level=logging.DEBUG,
    format=LOG_FORMAT
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


def send_message(bot, message):
    """Отправить сообщение."""
    chat_id = TELEGRAM_CHAT_ID
    logging.info('Отправка сообщения')
    if not bot.send_message(chat_id, message):
        raise SendMessageError('Бот не смог отправить сообщение')


def get_api_answer(current_timestamp=None):
    """Обратиться к API practicum."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        request = requests.get(URL, headers=HEADERS, params=params)
    except Exception as e:
        raise ApiRequestException(e)
    if request.status_code != http.HTTPStatus.OK:
        raise ApiRequestException('API возвращает код, отличный от 200')
    return request.json()


def check_response(response):
    """Проверка ответа от API."""
    if not isinstance(response, dict):
        raise TypeError(
            'В ответе не словарь'
        )
    if not isinstance(response['homeworks'], list):
        raise TypeError(
            'Cписок работ не соответсвует ожидаемому типу'
        )
    if 'current_date' not in response:
        raise NoValidAnswerException('В ответе отсутствует метка времени')
    if 'homeworks' not in response:
        raise NoValidAnswerException('В ответе отсутствует список работ')
    return response['homeworks']


def parse_status(homework):
    """Проверить сменился ли статус работы."""
    if not homework['status']:
        raise KeyError('Отсутствует ключ "status"')
    if not homework['homework_name']:
        raise KeyError('Отсутствует ключ "homework_name"')
    homework_status = homework['status']
    homework_name = homework['homework_name']
    try:
        verdict = HOMEWORK_STATUSES[homework_status]
    except KeyError:
        raise KeyError('Некорректный статус работы')
    message = (f'Изменился статус проверки работы'
               f' "{homework_name}". {verdict}'
               )
    return(message)


def check_tokens() -> bool:
    """Проверить наличие токенов."""
    if PRACTICUM_TOKEN and TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        return True


def main():
    """Основная логика работы бота."""
    prev_timestamp = int(time.time())
    bot = Bot(token=TELEGRAM_TOKEN)
    while True:
        try:
            logging.info('Проверка токенов')
            check_tokens()
            logging.info('Токены корректны')
            logging.info('GET запрос к API')
            practicum_response = get_api_answer(prev_timestamp)
            logging.info('Ответ получен')
            logging.info('Проверка ответа от API')
            homework_list = check_response(practicum_response)
            logging.info(f'Ответа API корректен, '
                         f'колчество работ в ответе: {len(homework_list)}')
            prev_timestamp = practicum_response["current_date"]
            logging.info('Получаю статус работы')
            if not len(homework_list):
                logging.info('Нет работ с новыми статусами')
                time.sleep(RETRY_TIME)
                continue
            logging.info('Есть работы с новыми статусами')
            prev_status = ''
            message = parse_status(homework_list[0])
            if prev_status != message:
                logging.info('Статус работы изменился')
                send_message(bot, message)
                logging.info('Сообщение отправлено')
            else:
                prev_status = message
                logging.info('Статус работы не изменился')
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()

if __name__ == '__logging__':
    logging()

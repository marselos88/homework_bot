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

if __name__ == '__logging__':
    logging()


URL = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
RETRY_TIME = 60
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
    try:
        bot.send_message(chat_id, message)
    except SendMessageError:
        logging.ERROR('Бот не смог отправить сообщение')


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
    if not type(response['homeworks']) == list:
        raise NoValidAnswerException(
            'Cписок работ не соответсвует ожидаемому типу'
        )
    return response['homeworks']


def parse_status(homework):
    """Проверить сменился ли статус работы."""
    homework_status_old = ''
    if len(homework) and homework_status_old != homework[0]['status']:
        homework_status_new = homework[0]['status']
        homework_status_old = homework_status_new
        verdict = HOMEWORK_STATUSES.get(homework_status_new)
        message = (f'Изменился статус проверки работы'
                   f' "{homework_status_new}". {verdict}'
                   )
    else:
        message = ''
    return(message)


def check_tokens() -> bool:
    """Проверить наличие токенов."""
    return all((PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID))


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
            parse_status(homework_list)
            logging.info('Статус работы получен')
            message = parse_status(homework_list)
            if len(message) != 0:
                logging.info('Статус работы изменился')
                send_message(bot, message)
                logging.info('Сообщение отправлено')
            else:
                logging.info('Статус работы не изменился')
            time.sleep(RETRY_TIME)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()

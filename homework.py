import logging
import os
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv
from requests import exceptions
from telegram.ext import Updater

load_dotenv()

PRACTICUM_TOKEN = os.getenv("my_practicum_token")
TELEGRAM_TOKEN = os.getenv("my_telegram_token")
TELEGRAM_CHAT_ID = os.getenv("my_telegram_chat")

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

logging.basicConfig(
    format='%(asctime)s %(levelname)s %(name)s %(message)s',
    level=logging.INFO)

updater = Updater(token=TELEGRAM_TOKEN)
HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Функция отправки сообщения ботом в указанный чат."""
    bot.send_message(TELEGRAM_CHAT_ID, message)


def get_api_answer(current_timestamp):
    """Функция запроса к API сервиса."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    if response.status_code != HTTPStatus.OK:
        error = f'ошибочный статус ответа по API: {response.status_code}'
        logging.error(error)
        raise exceptions.HTTPError(error)
    return response.json()


def check_response(response):
    """Функция проверки ответа API на корректность."""
    if response is None or not isinstance(response, dict):
        raise TypeError('В ответе нет списка homeworks')
    homeworks = response.get('homeworks')
    if homeworks is None or not isinstance(homeworks, list):
        raise ValueError('Список homeworks пуст')
    logging.info('Обновлен статус домашней работы')
    return homeworks


def parse_status(homework):
    """Проверка статуса домашней работы."""
    if not isinstance(homework, dict):
        message = 'Неверный тип данных'
        raise TypeError(message)
    if ('status' or 'homework_name') not in homework:
        message = 'Ключи отсутствуют'
        raise KeyError(message)
    homework_name = homework['homework_name']
    homework_status = homework['status']
    if homework_status not in HOMEWORK_STATUSES:
        message = 'Неизвестный статус работы'
        raise TypeError(message)
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверка токенов."""
    print(PRACTICUM_TOKEN)
    print(TELEGRAM_TOKEN)
    print(TELEGRAM_CHAT_ID)
    if PRACTICUM_TOKEN and TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        return True


def main():
    """Основная логика работы бота."""
    print(check_tokens())
    if not check_tokens():
        error = 'Токены отсутствуют'
        logging.error(error, exc_info=True)
        raise SystemExit
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    status = ''
    while True:
        try:
            response = get_api_answer(current_timestamp)

        except Exception as error:
            logging.error(f'Ошибка при запросе к основному API. {error}')
            time.sleep(RETRY_TIME)
            continue
        try:
            if check_response(response):
                homeworks = check_response(response)
                homework = homeworks[0]
                message = parse_status(homework)
                if message != status:
                    send_message(bot, status)
                    status = message
            current_timestamp = current_timestamp
            time.sleep(RETRY_TIME)
        except Exception as error:
            message = f'Сбой в работе программы {error}'
            if message != status:
                send_message(bot, message)
                status = message
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()

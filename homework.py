import logging
import sys
import time
from http import HTTPStatus

import requests
import telegram

from ProjectConfig import PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

logging.basicConfig(
    format='%(asctime)s %(levelname)s %(name)s %(message)s',
    level=logging.INFO)

HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Функция отправки сообщения ботом в указанный чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except telegram.TelegramError as error:
        logging.error(f'Телеграм недоступен. {error}')


def get_api_answer(current_timestamp):
    """Функция запроса к API сервиса."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    except Exception as error:
        logging.error(f'Ошибка при запросе к основному API: {error}')
        raise Exception(f'Ошибка при запросе к основному API: {error}')
    if response.status_code != HTTPStatus.OK:
        logging.error(f'Ошибка {response.status_code}')
        raise Exception(f'Ошибка {response.status_code}')
    try:
        return response.json()
    except ValueError:
        logging.error('Ошибка формата json')
        raise ValueError('Ошибка формата json')


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
        raise Exception(message)
    homework_name = homework['homework_name']
    homework_status = homework['status']
    if homework_status not in HOMEWORK_STATUSES:
        message = 'Неизвестный статус работы'
        raise TypeError(message)
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверка токенов."""
    return bool(PRACTICUM_TOKEN and TELEGRAM_TOKEN and TELEGRAM_CHAT_ID)


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        error = 'Токены отсутствуют'
        logging.error(error, exc_info=True)
        raise sys.exit()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    status = ''
    while True:
        try:
            response = get_api_answer(current_timestamp)
        except Exception as error:
            logging.error(f'Ошибка при запросе к основному API. {error}')
            continue
        try:
            if check_response(response):
                homeworks = check_response(response)
                homework = homeworks[0]
                message = parse_status(homework)
                if message != status:
                    send_message(bot, status)
                    status = message
            current_timestamp = response.get('current_date')
        except Exception as error:
            message = f'Сбой в работе программы {error}'
            if message != status:
                send_message(bot, message)
                status = message
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    sys.exit(main())

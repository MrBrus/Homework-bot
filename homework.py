import logging
import sys
import time
from http import HTTPStatus

import requests
import telegram

import exceptions as exc
import project_config as pc
from project_config import PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID

logging.basicConfig(
    format='%(asctime)s %(levelname)s %(name)s %(message)s',
    level=logging.INFO)


def send_message(bot, message):
    """Функция отправки сообщения ботом в указанный чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except exc.TelegramException as error:
        logging.error(f'Телеграм недоступен. {error}')


def get_api_answer(current_timestamp):
    """Функция запроса к API сервиса."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(pc.ENDPOINT, headers=pc.HEADERS, params=params)
    except Exception as error:
        logging.error(f'Ошибка при запросе к основному API: {error}')
        raise exc.GetAPIException(f'Ошибка при запросе к'
                                  f'основному API: {error}')
    if response.status_code != HTTPStatus.OK:
        logging.error(f'Ошибка {response.status_code}')
        raise exc.GetAPIException(f'Ошибка при запросе'
                                  f'к основному API: {response.status_code}')
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
        raise exc.StatusException(message)
    homework_name = homework['homework_name']
    homework_status = homework['status']
    if homework_status not in pc.HOMEWORK_STATUSES:
        message = 'Неизвестный статус работы'
        raise TypeError(message)
    verdict = pc.HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверка токенов."""
    return bool(PRACTICUM_TOKEN and TELEGRAM_TOKEN and TELEGRAM_CHAT_ID)


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        error = 'Токены отсутствуют'
        logging.error(error, exc_info=True)
        sys.exit()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    status = ''
    while True:
        try:
            response = get_api_answer(current_timestamp)
            if check_response(response):
                homeworks = check_response(response)
                homework = homeworks[0]
                message = parse_status(homework)
                if message != status:
                    send_message(bot, status)
                    status = message
            current_timestamp = response.get('current_date', current_timestamp)
        except KeyboardInterrupt:
            hotkey = input(
                'Хотите остановить бота? Y/N: '
            )
            if hotkey in ('Y', 'y'):
                print('Спасибо, что были с нами!')
                break
            elif hotkey in ('N', 'n'):
                print('Продолжаем!')
        except Exception as error:
            message = f'Сбой в работе программы {error}'
            if message != status:
                send_message(bot, message)
                status = message
        finally:
            time.sleep(pc.RETRY_TIME)


if __name__ == '__main__':
    main()

import requests
import time
import random
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import boto3
from typing import List


bucket_name = "name"  # Название бакета
file_name = "name.txt"  # Название файла с куки в бакете
AWS_ACCESS_KEY_ID = "key-id"  # key id для доступа в бакет
AWS_SECRET_ACCESS_KEY = "key"  # key для доступа в бакет
region = "region"  # регион, обычно "ru-central1"
company_id = "123456"  # id компании, можно посмотреть на странице компании (например https://www.ozon.ru/seller/ooo-mebelnaya-fabrika-volzhanka-1234/products/?miniapp=seller_1234 - id компании 1234)
fromaddr = "example1@mail.ru"  # почта, с которой будет уходить письмо
mypass = "password"  # пароль от почты для внешних приложений
toaddr = "example2@mail.ru"  # почта, на которую отправлять письмо
questions_sum = (
    10  # количество кейсов, которые необходимо отправить (1 кейс = 10 вопросов)
)
cookie = "cookie"  # куки


# Обновляет куки в бакете Yandex Cloud
def change_cookie_bucket(cookie: str) -> None:
    max_attempts = 3  # Максимальное количество попыток загрузки
    delay = 1  # Задержка между попытками в секундах

    for attempt in range(max_attempts):
        try:
            # Создаем клиент для работы с S3
            s3 = boto3.client(
                "s3",
                endpoint_url="https://storage.yandexcloud.net",
                aws_access_key_id=AWS_ACCESS_KEY_ID,
                aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
                region_name=region,
            )

            # Загружаем новое содержимое файла
            response = s3.put_object(
                Bucket=bucket_name,
                Key=file_name,
                Body=cookie.encode("utf-8"),
                ContentType="text/plain",  # Content-Type файла
            )

            # Проверяем успешность операции
            if response["ResponseMetadata"]["HTTPStatusCode"] == 200:
                print(
                    f"File '{file_name}' successfully updated in Yandex Object Storage."
                )
                return  # Выходим из функции, если файл успешно загружен
            else:
                print(
                    f"Failed to update file. Status code: {response['ResponseMetadata']['HTTPStatusCode']}"
                )
                print(response)
        except Exception as e:
            print(f"Error updating file: {e}")

        # Если это не последняя попытка, ждем перед следующей попыткой
        if attempt < max_attempts - 1:
            print(
                f"Попытка {attempt + 1} не удалась. Ждем {delay} секунд перед следующей попыткой..."
            )
            time.sleep(delay)
    print(f"Все {max_attempts} попытки загрузки файла не удалась.")


# Получает список вопросов с сервера OZON
def get_answers(value_cases: int, cookie: str) -> List[dict]:
    global start_time
    start_time = time.time()  # начало таймера
    print(f'cookie: "{cookie}"')
    print(f'cases: "{value_cases}"')
    url = "https://seller.ozon.ru/api/v1/question-list"
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "ru",
        "Content-Type": "application/json",
        "Priority": "u=1, i",
        "Sec-CH-UA": '"Not)A;Brand";v="99", "Google Chrome";v="127", "Chromium";v="127"',
        "Sec-CH-UA-Mobile": "?0",
        "Sec-CH-UA-Platform": '"Windows"',
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "X-O3-App-Name": "seller-ui",
        "X-O3-Company-Id": company_id,
        "X-O3-Language": "ru",
        "X-O3-Page-Type": "questions",
        "Cookie": cookie,
        "Referer": "https://seller.ozon.ru/app/reviews/questions",
        "Referrer-Policy": "strict-origin-when-cross-origin",
    }

    last_id = "0"
    last_published = None
    body = {
        "sc_company_id": company_id,
        "with_brands": False,
        "with_counters": False,
        "company_type": "seller",
        "filter": {"status": "NEW"},
        "last_published_at": last_published,
        "pagination_last_id": last_id,
    }
    all_cases = []
    max_retries = 11  # Количество повторных запросов

    success = False  # Флаг успешности запросов для сохранения новых куки

    for cases in range(value_cases):
        retries = 0  # Счетчик повторных запросов
        while retries <= max_retries:
            try:
                print(
                    f"Отправляю запрос на сервер OZON для получения вопросов. Запрос {cases+1} из {value_cases}."
                )
                response = requests.post(url, headers=headers, json=body)
                response.raise_for_status()  # Вызвать исключение, если статус не 200
                if response.status_code == 401:
                    print("Ошибка 401: Не авторизован")
                    return []  # Прервать выполнение функции
                data = response.json()
                for case in data["result"]:
                    all_cases.append(case)
                last_id = data["pagination_last_id"]
                last_published = data["last_published_at"]
                body["pagination_last_id"] = last_id
                body["last_published_at"] = last_published
                time.sleep(random.uniform(2, 4))

                success = True  # т.к. запрос успешно прошел - меняю флаг, чтобы сохранить эти куки

                end_time = time.time()
                execution_time = end_time - start_time
                execution_time_formatted = time.strftime(
                    "%H:%M:%S", time.gmtime(execution_time)
                )

                print(f"Время выполнения программы: {execution_time_formatted}")
                break  # Выход из цикла, если запрос успешный

            except requests.exceptions.RequestException as err:
                print(f"Ошибка запроса: {err}")
                retries += 1  # Увеличение счетчика повторных запросов
                if retries <= max_retries:
                    print(f"Повторный запрос через 6 секунд...")
                    time.sleep(6)
                else:
                    print(f"Все повторные запросы исчерпаны. Пропускаю...")
                    end_time = time.time()
                    execution_time = end_time - start_time
                    execution_time_formatted = time.strftime(
                        "%H:%M:%S", time.gmtime(execution_time)
                    )

                    print(f"Время выполнения программы: {execution_time_formatted}")
                    break
            except Exception as err:
                print(f"Неизвестная ошибка: {err}")
                break
    if success:
        change_cookie_bucket(
            cookie
        )  # сохраняю новые куки, т.к. успешно прошел хотя бы один запрос
    return all_cases


# Отправляет вопросы на указанный email
def send_mail_ozon(value: int, cookie: str) -> str:
    cases = get_answers(value, cookie)
    if not cases:
        print("Нет вопросов для отправки")
        return "Нет вопросов для отправки.\nОшибка 401: Не авторизован.\nПроверь корректность cookie."
    sent_cases = 0  # переменная для хранения количества отправленных кейсов
    for case in cases:
        tema = case["id"]
        body = f"""<p><b>Текст вопроса:</b> {case['text']}</p>
<br>
<p><b>Ссылка на товар OZON:</b> <a href="firefox:{case['product']['url']}">{case['product']['url']}</a></p>
<br>
<p>Название бренда: {case['brand_info']['name']}</p>
<p>ID вопроса: {case['id']}</p>
<p>Дата поступления вопроса: {case['published_at']}</p>
<p>Артикул на OZON: {case['product']['sku']}</p>
<p>Артикул наш сайт: {case['product']['offer_id']}</p>
<p>Название товара: {case['product']['title']}</p>
"""
        print(f"Начинаю отправку сообщения(кейса) на email {toaddr}.")

        msg = MIMEMultipart()
        msg["From"] = fromaddr
        msg["To"] = toaddr
        msg["Subject"] = tema
        msg.attach(MIMEText(body, "html"))

        max_retries = 10  # количество попыток отправки email
        retry_delay = 6  # задержка между попытками в секундах
        case_sent = False  # флаг, указывающий, был ли кейс отправлен

        for i in range(max_retries):
            try:
                server = smtplib.SMTP_SSL("smtp.mail.ru", 465)
                server.login(fromaddr, mypass)
                text = msg.as_string()
                server.sendmail(fromaddr, toaddr, text)
                server.quit()
                case_sent = True
                current_index = cases.index(case)
                print(
                    f"Сообщение отправлено. Осталось отправить сообщений(кейсов): {len(cases[current_index:])-1}шт."
                )
                end_time = time.time()
                execution_time = end_time - start_time
                execution_time_formatted = time.strftime(
                    "%H:%M:%S", time.gmtime(execution_time)
                )
                print(f"Время выполнения программы: {execution_time_formatted}")
                break
            except smtplib.SMTPException as e:
                print(f"Ошибка при отправке письма: {e}. Повторяю отправку...")
                time.sleep(retry_delay)
        else:
            print(f"Все попытки отправки письма не увенчались успехом. Ошибка.")
        if case_sent:
            sent_cases += 1
        time.sleep(1)
    print("Все сообщения(кейсы) отправлены.")
    end_time = time.time()
    execution_time = end_time - start_time
    execution_time_formatted = time.strftime("%H:%M:%S", time.gmtime(execution_time))
    print(f"Время выполнения программы: {execution_time_formatted}")
    return f"Отправлено {sent_cases} кейсов из {len(cases)}."


if __name__ == "__main__":
    send_mail_ozon(questions_sum, cookie)

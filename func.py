import time
import requests
import json
import gspread
from gspread.utils import rowcol_to_a1
from datetime import date, timedelta

# Загрузка конфигурации
with open('config.json', 'r') as file:
    config = json.load(file)
    GOOGLE_SHEET_KEY = config.get('google_sheet_key')
    SERVICE_ACCOUNT_FILE = config.get('service_account_file')
    projects = config.get('projects')

def gsheet_output(date_of_request, customer='project1', type_of_request='stock'):
    gc = gspread.service_account(filename=SERVICE_ACCOUNT_FILE)
    sh = gc.open_by_key(GOOGLE_SHEET_KEY)  # открывает таблицу по ключу
    worksheet = sh.worksheet("Выкупы")  # выбираем текущий лист в таблице

    cell_data = worksheet.findall(date_of_request)  # создаем массив всех ячеек с выбранной датой
    start_index = rowcol_to_a1(cell_data[0].row, cell_data[0].col)
    end_index = rowcol_to_a1(cell_data[-1].row, cell_data[-1].col)

    ranges = [f'G{start_index[1:]}:G{end_index[1:]}', f'L{start_index[1:]}:L{end_index[1:]}']
    data = worksheet.batch_get(ranges)

    shop = projects[customer]['shop']
    fbs = projects[customer]['fbs']

    filtered_rows = [i for i, row in enumerate(data[0]) if row and row[0] == shop]
    articles = [data[1][i][0] for i in filtered_rows if data[1][i][0] != ""]
    unic_articles = list(set(articles))
    counts = [articles.count(i) for i in unic_articles]

    if type_of_request == 'stock':
        lst = [{"offer_id": article, "stock": count, "warehouse_id": fbs}
               for article, count in zip(unic_articles, counts)]
        return lst

    elif type_of_request == 'delete':
        lst = [{"offer_id": article, "stock": 0, "warehouse_id": fbs} for article in unic_articles]
        return lst

    elif type_of_request == 'remains':
        return unic_articles
    

def get_product_remains(head: dict, items_list: list) -> list:
    method = "https://api-seller.ozon.ru/v3/product/info/stocks"
    body = {
        "filter": {
            "offer_id": items_list,
            "visibility": "ALL"
        },
        "last_id": "",
        "limit": 1000
    }
    body = json.dumps(body)  # конвертация тела запроса в json
    response = requests.post(method, headers=head, data=body).json()
    dict_output = {i.get('offer_id'): i.get('stocks')[0].get('present') for i in response.get('result').get('items')}
    list_output = [dict(list(dict_output.items())[i:i + 10]) for i in range(0, len(list(dict_output.items())), 10)]
    return list_output


def split_list(big_lst, chunk_size=100):
    for i in range(0, len(big_lst), chunk_size):
        yield big_lst[i:i + chunk_size]


def get_fbo_stock(head: dict, items_list: list):
    # Если список меньше или равен 100, обрабатываем сразу
    if len(items_list) <= 100:
        return update_stock_chunk(head, items_list)

    # Если список больше 100, делим на части
    chunks = list(split_list(items_list))

    for chunk in chunks:
        result = update_stock_chunk(head, chunk)
#        print(result)  # Выводим результат для каждой части

    return "Обновление стока завершено для всех частей."


# Функция для обновления стока по одному фрагменту с обработкой ошибок
def update_stock_chunk(head: dict, chunk: list):
    method = "https://api-seller.ozon.ru/v2/products/stocks"
    body = {"stocks": chunk}
    body = json.dumps(body)  # конвертация тела запроса в json

    try:
        # Выполнение POST-запроса
        response = requests.post(method, headers=head, data=body)
        response.raise_for_status()  # Проверяем наличие HTTP-ошибок
        response_json = response.json()  # Парсим JSON-ответ
        for i in response_json['result']:
            print(i)

        # Проверка на наличие ключей и данных в ответе
        if not response_json.get('result'):
            raise KeyError('Отсутствует ключ "result" в ответе от API.')

        # Обработка ответа
        # if all(item.get('updated') for item in response_json['result']):
        #     return f"Сток товаров успешно обновлен на складе {chunk[0].get('warehouse_id')}"
        
        if any(item.get('updated') is True or 'errors' in item and any(err.get('code') == 'NOT_FOUND_ERROR' for err in item['errors']) for item in response_json['result']):
            return f"Сток товаров успешно обновлен на складе {chunk[0].get('warehouse_id')}"
        
        else:
            print('Слишком частое обновление, ждем 15 секунд')
            time.sleep(15)
            return update_stock_chunk(head, chunk)  # Повторяем запрос для текущего куска

    except requests.exceptions.Timeout:
        print("Превышено время ожидания запроса, повтор через 15 секунд")
        time.sleep(15)
        return update_stock_chunk(head, chunk)

    except requests.exceptions.RequestException as e:
        # Обработка всех ошибок, связанных с сетью и запросами
        print(f"Ошибка сети или запроса: {e}")
        return "Произошла ошибка сети"

    except json.JSONDecodeError:
        print("Ошибка при декодировании JSON-ответа")
        return "Ошибка в данных от сервера"

    except KeyError as e:
        print(f"Ошибка доступа к данным: {e}")
        return "Некорректный ответ от сервера"

    except Exception as e:
        # Общая обработка для других непредвиденных ошибок
        print(f"Непредвиденная ошибка: {e}")
        return "Произошла непредвиденная ошибка"
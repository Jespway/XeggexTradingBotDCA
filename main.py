import websocket
import json
import time
import os
from dotenv import load_dotenv
load_dotenv()
# Учетные данные для доступа к API биржи


# Настройки торгового символа и стратегии
symbol = "GPN/USDT"
amount = 100
spread = 0.02
max_open_orders = 6
last_price = None
orders_opened = 0
top_of_range = 0.00145
bottom_of_range = 0.00135
spread_list = []
active_order_list = []

def on_message(ws, message):
    """
    Обработчик входящих сообщений WebSocket.

    Args:
        ws (websocket.WebSocketApp): Экземпляр WebSocket.
        message (str): Входящее сообщение.

    Returns:
        None
    """
    global last_price, max_open_orders, active_order_list
    response = json.loads(message)
    
    if 'id' in response:
        request_id = response['id']
        if request_id == 2:
            # Обработка данных тикера и создание сетки спреда
            last_price = float(response['params']['lastPrice'])
            s = 0
            spread_list.append(top_of_range)
            while spread_list[len(spread_list) - 1] > bottom_of_range:
                spread_list.append(round(top_of_range * (1 - (spread * s)), 7))
                s += 1
            print(f"Сетка спреда: {spread_list}")
        elif request_id == 3:
            print(f"Получено сообщение id3: {message}")
        elif request_id == 5:
            # Обработка открытых ордеров
            print(f"Получено сообщение id5: {message}")
            open_orders = response.get("result", [])
            buy_orders = [order for order in open_orders if order.get("side") == "buy"]
            active_order_list = [float(order.get("price")) for order in buy_orders]
    
    elif 'method' in response and response['method'] == 'ticker':
        # Обработка изменений тикера
        last_price = float(response['params']['lastPrice'])
        closest_number = find_closest_number(spread_list, last_price)
        if closest_number is not None:
            if closest_number not in active_order_list:
                open_buy_order(ws, closest_number)
                active_order_list.append(closest_number)
        else:
            print(f"В списке нет чисел, меньших {last_price}")
    
    elif 'method' in response and response['method'] == "report":
        # Обработка отчетов об исполненных ордерах
        params = response.get('params', {})
        side = params.get('side')
        reportType = params.get('reportType')
        repotprice = float(params.get('price'))
        status = params.get('status')
        if side == 'buy' and reportType == 'trade' and status == 'Filled':
            print(f"Куплено по цене: {repotprice}")
            sell_price = repotprice * (1 + spread)
            open_sell_order(ws, sell_price)

def find_closest_number(lst, target):
    """
    Найти ближайшее число к целевому числу в списке.

    Args:
        lst (list): Список чисел.
        target (float): Целевое число.

    Returns:
        float: Ближайшее число в списке к целевому числу.
    """
    filtered_list = [x for x in lst if x < target]
    if filtered_list:
        return max(filtered_list)
    else:
        return None

def open_buy_order(ws, buy_price):
    """
    Открыть ордер на покупку.

    Args:
        ws (websocket.WebSocketApp): Экземпляр WebSocket.
        buy_price (float): Цена покупки.

    Returns:
        None
    """
    buy_order = {
        "method": "newOrder",
        "params": {
            "symbol": symbol,
            "userProvidedId": str(time.time()),
            "side": "buy",
            "type": "limit",
            "quantity": str(amount),
            "price": buy_price
        },
        "id": 4
    }
    ws.send(json.dumps(buy_order))
    print(f"Выставлено на покупку по цене {buy_price}")

def open_sell_order(ws, sell_price):
    """
    Открыть ордер на продажу.

    Args:
        ws (websocket.WebSocketApp): Экземпляр WebSocket.
        sell_price (float): Цена продажи.

    Returns:
        None
    """
    sell_order = {
        "method": "newOrder",
        "params": {
            "symbol": symbol,
            "userProvidedId": str(time.time()),
            "side": "sell",
            "type": "limit",
            "quantity": str(amount),
            "price": sell_price
        },
        "id": 4
    }
    ws.send(json.dumps(sell_order))
    print(f"Выставлено на продажу по цене {sell_price}")

def get_open_orders(ws):
    """
    Получить список открытых ордеров.

    Args:
        ws (websocket.WebSocketApp): Экземпляр WebSocket.

    Returns:
        None
    """
    get_orders_message = {
        "method": "getOrders",
        "params": {
            "symbol": symbol
        },
        "id": 5
    }
    ws.send(json.dumps(get_orders_message))

def get_order_reports(ws):
    """
    Подписаться на отчеты об исполненных ордерах.

    Args:
        ws (websocket.WebSocketApp): Экземпляр WebSocket.

    Returns:
        None
    """
    get_report_message = {
        "method": "subscribeReports",
        "params": {},
        "id": 4
    }
    ws.send(json.dumps(get_report_message))

def get_balance(ws):
    """
    Получить баланс.

    Args:
        ws (websocket.WebSocketApp): Экземпляр WebSocket.

    Returns:
        None
    """
    get_balance_message = {
        "method": "getTradingBalance",
        "params": {},
        "id": 3
    }
    ws.send(json.dumps(get_balance_message))

def on_close(ws, close_status_code, close_msg):
    """
    Обработчик закрытия WebSocket соединения.

    Args:
        ws (websocket.WebSocketApp): Экземпляр WebSocket.
        close_status_code (int): Код статуса закрытия.
        close_msg (str): Сообщение о закрытии.

    Returns:
        None
    """
    print("WebSocket соединение закрыто")

def on_open(ws):
    """
    Обработчик открытия WebSocket соединения.

    Args:
        ws (websocket.WebSocketApp): Экземпляр WebSocket.

    Returns:
        None
    """
    global orders_opened
    print("WebSocket соединение открыто.")
    auth_message = {
        "method": "login",
        "params": {
            "algo": "BASIC",
            "pKey": os.getenv("API_KEY"),
            "sKey": os.getenv("API_SECRET"),
            "nonce": "любая_случайная_строка"
        },
        "id": 1
    }
    ws.send(json.dumps(auth_message))

    subscribe_message = {
        "method": "subscribeTicker",
        "params": {
            "symbol": symbol
        },
        "id": 2
    }
    ws.send(json.dumps(subscribe_message))

    get_open_orders(ws)
    get_balance(ws)
    get_order_reports(ws)

def on_error(ws, error):
    """
    Обработчик ошибок WebSocket.

    Args:
        ws (websocket.WebSocketApp): Экземпляр WebSocket.
        error (str): Сообщение об ошибке.

    Returns:
        None
    """
    print(f"Произошла ошибка: {error}")
    if "10054" in str(error):
        print("Соединение разорвано, переподключение...")
        ws.close()
        time.sleep(30)
        ws.run_forever()

if __name__ == "__main__":
    ws_url = "wss://api.xeggex.com"
    ws = websocket.WebSocketApp(ws_url, on_message=on_message, on_error=on_error, on_close=on_close)
    ws.on_open = on_open
    ws.run_forever()

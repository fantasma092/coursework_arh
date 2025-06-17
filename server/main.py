from fastapi import FastAPI, HTTPException
import redis
import pika
import json
import time
import psycopg2
from psycopg2.extras import RealDictCursor

app = FastAPI()

# Подключение к Redis (исправлены кавычки)
redis_client = redis.Redis(host="redis", port=6379, decode_responses=True)

# Подключение к PostgreSQL
def get_postgres_connection():
    while True:
        try:
            connection = psycopg2.connect(
                host="postgres",
                database="default",
                user="postgres",
                password="postgres",
                cursor_factory=RealDictCursor
            )
            return connection
        except Exception as e:
            print("Не удалось подключиться к PostgreSQL. Повтор через 5 секунд...")
            time.sleep(5)

# Инициализация подключения к PostgreSQL
try:
    postgres_conn = get_postgres_connection()
    
    # Инициализация таблицы
    with postgres_conn.cursor() as cursor:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id VARCHAR(255) PRIMARY KEY,
                data JSONB NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        postgres_conn.commit()
except Exception as e:
    print(f"Ошибка при инициализации PostgreSQL: {e}")
    postgres_conn = None

# Ваш исходный код подключения к RabbitMQ (исправлены кавычки)
def get_rabbitmq_connection():
    while True:
        try:
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host="rabbitmq",
                    heartbeat=600,
                    blocked_connection_timeout=300
                )
            )
            return connection
        except pika.exceptions.AMQPConnectionError:
            print("Не удалось подключиться к RabbitMQ. Повтор через 5 секунд...")
            time.sleep(5)

# Инициализация RabbitMQ (исправлены кавычки)
try:
    connection = get_rabbitmq_connection()
    channel = connection.channel()
    channel.queue_declare(queue="orders", durable=True)
except Exception as e:
    print(f"Ошибка инициализации RabbitMQ: {e}")
    connection = None
    channel = None

@app.post("/order")
def create_order(order_data: dict):
    global connection, channel, postgres_conn
    
    order_id = order_data.get("id")
    if not order_id:
        raise HTTPException(status_code=400, detail="Order ID is required")

    # Сохраняем в PostgreSQL
    if postgres_conn:
        try:
            with postgres_conn.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO orders (id, data) VALUES (%s, %s)",
                    (order_id, json.dumps(order_data))
                )
                postgres_conn.commit()
        except Exception as e:
            print(f"Ошибка при сохранении в PostgreSQL: {e}")
            try:
                postgres_conn = get_postgres_connection()
            except Exception:
                pass

    # Сохраняем в Redis и отправляем в RabbitMQ
    try:
        redis_client.set(f"order:{order_id}", json.dumps(order_data))
        
        if channel:
            channel.basic_publish(
                exchange="",
                routing_key="orders",
                body=json.dumps({"event": "order_created", "order_id": order_id})
            )
    except Exception as e:
        print(f"Ошибка при работе с Redis/RabbitMQ: {e}")

    return {"status": "Order created", "order_id": order_id}

@app.get("/order/{order_id}")
def get_order(order_id: str):
    # Сначала проверяем кеш
    try:
        cached_order = redis_client.get(f"order:{order_id}")
        if cached_order:
            return json.loads(cached_order)
    except Exception as e:
        print(f"Ошибка при работе с Redis: {e}")

    # Если нет в кеше, проверяем PostgreSQL
    if postgres_conn:
        try:
            with postgres_conn.cursor() as cursor:
                cursor.execute("SELECT data FROM orders WHERE id = %s", (order_id,))
                result = cursor.fetchone()
                
                if not result:
                    raise HTTPException(status_code=404, detail="Order not found")
                
                # Сохраняем в кеш
                try:
                    redis_client.set(f"order:{order_id}", json.dumps(result['data']))
                except Exception:
                    pass
                
                return result['data']
        except Exception as e:
            print(f"Ошибка при работе с PostgreSQL: {e}")

    raise HTTPException(status_code=404, detail="Order not found")

@app.patch("/order/{order_id}")
def update_order(order_id: str, update_data: dict):
    # Получаем текущий заказ
    current_order = get_order(order_id)
    current_order.update(update_data)

    # Обновляем в PostgreSQL
    if postgres_conn:
        try:
            with postgres_conn.cursor() as cursor:
                cursor.execute(
                    "UPDATE orders SET data = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s",
                    (json.dumps(current_order), order_id)
                )
                postgres_conn.commit()
        except Exception as e:
            print(f"Ошибка при обновлении в PostgreSQL: {e}")

    # Обновляем кеш и отправляем событие
    try:
        redis_client.set(f"order:{order_id}", json.dumps(current_order))
        
        if channel:
            channel.basic_publish(
                exchange="",
                routing_key="orders",
                body=json.dumps({"event": "order_updated", "order_id": order_id})
            )
    except Exception as e:
        print(f"Ошибка при работе с Redis/RabbitMQ: {e}")

    return {"status": "Order updated", "order_id": order_id}

@app.delete("/order/{order_id}")
def delete_order(order_id: str):
    # Проверяем существование заказа
    get_order(order_id)

    # Удаляем из PostgreSQL
    if postgres_conn:
        try:
            with postgres_conn.cursor() as cursor:
                cursor.execute("DELETE FROM orders WHERE id = %s", (order_id,))
                postgres_conn.commit()
        except Exception as e:
            print(f"Ошибка при удалении из PostgreSQL: {e}")

    # Удаляем из кеша и отправляем событие
    try:
        redis_client.delete(f"order:{order_id}")
        
        if channel:
            channel.basic_publish(
                exchange="",
                routing_key="orders",
                body=json.dumps({"event": "order_deleted", "order_id": order_id})
            )
    except Exception as e:
        print(f"Ошибка при работе с Redis/RabbitMQ: {e}")

    return {"status": "Order deleted", "order_id": order_id}

# Тестовый endpoint для RabbitMQ
@app.get("/test-rabbit")
def test_rabbit():
    try:
        if channel:
            channel.basic_publish(
                exchange="",
                routing_key="orders",
                body="TEST_MESSAGE"
            )
            return {"status": "Сообщение отправлено в RabbitMQ"}
        return {"error": "RabbitMQ channel не инициализирован"}
    except Exception as e:
        return {"error": str(e)}
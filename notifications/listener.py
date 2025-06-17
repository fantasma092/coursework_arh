import pika
import json
import time

def connect_to_rabbitmq():
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
            print("Ожидание RabbitMQ...")
            time.sleep(5)

def on_message(ch, method, properties, body):
    try:
        event = json.loads(body)
        print(f" [x] Received: {event}")
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        print(f"Ошибка обработки: {e}")

def start_consumer():
    connection = connect_to_rabbitmq()
    channel = connection.channel()
    
    channel.queue_declare(queue="orders", durable=True)
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(
        queue="orders",
        on_message_callback=on_message
    )
    
    print(" [*] Waiting for messages. To exit press CTRL+C")
    try:
        channel.start_consuming()
    except pika.exceptions.ConnectionClosed:
        print("Соединение потеряно. Переподключение...")
        start_consumer()  # Рекурсивный перезапуск

if __name__ == "__main__":
    start_consumer()
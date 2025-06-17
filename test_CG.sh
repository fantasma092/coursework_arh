#!/bin/bash

API_URL="http://localhost:8000/order"

create_order() {
  local order_id="$1"
  local product="$2"
  
  echo "Создаем заказ $order_id..."
  response=$(curl -s -X POST -H "Content-Type: application/json" -d "{\"id\":\"$order_id\", \"product\":\"$product\"}" "$API_URL")
  echo "Ответ сервера: $response"
}

get_order() {
  local order_id="$1"
  
  echo "Проверяем заказ $order_id..."
  curl -s "$API_URL/$order_id" | jq .  
}

#Тестируем
create_order "1" "Телефон"
create_order "2" "Фитнес-браслет"
create_order "3" "Кофемолка"

get_order "1"
get_order "2"
get_order "3"
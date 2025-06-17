#!/bin/bash

API_URL="http://localhost:8000/order"

# Создание заказа
create_order() {
  local order_id="$1"
  local product="$2"
  
  echo "🛒 Создаем заказ $order_id..."
  response=$(curl -s -X POST -H "Content-Type: application/json" -d "{\"id\":\"$order_id\", \"product\":\"$product\"}" "$API_URL")
  echo "   Ответ сервера: $response"
}

# Получение заказа
get_order() {
  local order_id="$1"
  
  echo "🔍 Проверяем заказ $order_id..."
  curl -s "$API_URL/$order_id" | jq .
}

# Обновление заказа
update_order() {
  local order_id="$1"
  local new_product="$2"
  
  echo "🔄 Обновляем заказ $order_id..."
  response=$(curl -s -X PATCH -H "Content-Type: application/json" -d "{\"product\":\"$new_product\"}" "$API_URL/$order_id")
  echo "   Ответ сервера: $response"
}

# Удаление заказа
delete_order() {
  local order_id="$1"
  
  echo "❌ Удаляем заказ $order_id..."
  response=$(curl -s -X DELETE "$API_URL/$order_id")
  echo "   Ответ сервера: $response"
}

# Тест CRUD
echo "=== Тест обновление, удаление) ==="
create_order "999" "Nintendo Switch"
get_order "999"

echo ""
update_order "999" "Nintendo Switch OLED"
get_order "999"

echo ""
delete_order "999"
echo "Проверяем, что заказ удалён..."
get_order "999"  # Должен вернуть 404
## Описание проекта

**Foodgram** — это сервис обмена рецептами - https://foodgramonfire.ddns.net/
Пользователи могут размещать свои рецепты, подписываться на авторов, добавлять рецепты в избранное и в список покупок, скачивать список ингредиентов любимых рецептов.

**Основные возможности:**
- Регистрация и аутентификация пользователей
- Создание, редактирование и просмотр рецептов
- Подписки на авторов
- Избранное и корзина покупок
- Скачивание списка покупок

---

## Стек технологий

Проект реализован на Django REST Framework и полностью разворачивается в Docker.

- Python 3.12
- Django
- Django REST Framework
- PostgreSQL
- Docker
- Docker Compose
- Nginx
- Gunicorn
- Djoser

---

## Как развернуть проект в Docker

### 1. Клонировать репозиторий

```bash
git clone https://github.com/ElizavetaUdodenko/foodgram.git
cd foodgram
````

---

### 2. Создать файл `.env`

В корне проекта создать файл `.env` и заполнить его переменными:

```env
DEBUG
SECRET_KEY
ALLOWED_HOSTS
CSRF_TRUSTED_ORIGINS
POSTGRES_DB
POSTGRES_USER
POSTGRES_PASSWORD
DB_HOST
DB_PORT
```

---

### 3. Собрать и запустить контейнеры

```bash
docker-compose up -d --build
```

---

### 4. Применить миграции и собрать статику

```bash
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py collectstatic
docker compose exec backend cp -r /app/collected_static/. /backend_static/static/
```

---

### 5. Создать суперпользователя

```bash
docker compose exec backend python manage.py createsuperuser
```

---

## Как наполнить базу данных

Для загрузки тестовых данных (ингредиенты и теги) выполнить команду:

```bash
docker compose exec backend python manage.py loaddata ../data/tags_ingredients.json
```

---

## Документация API

После запуска проекта документация доступна по адресу:

  ```
  http://localhost:8080/api/docs/
  ```

---

## Примеры запросов и ответов

### 1. Добавить рецепт в избранное

**POST**

```
http://localhost:8080/api/recipes/{id}/favorite/
```

**Ответ — 201 CREATED**

```json
{
  "id": 0,
  "name": "string",
  "image": "http://foodgram.example.org/media/recipes/images/image.png",
  "cooking_time": 1
}
```

---

### 2. Удалить рецепт из избранного

**DELETE**

```
http://localhost:8080/api/recipes/{id}/favorite/
```

**Ответ — 204 NO CONTENT**

---

### 3. Подписаться на автора

**POST**

```
http://localhost:8080/api/users/{id}/subscribe/
```

**Ответ — 201 CREATED**

```json
{
  "email": "user@example.com",
  "id": 0,
  "username": "string",
  "first_name": "Вася",
  "last_name": "Иванов",
  "is_subscribed": true,
  "recipes": [
    {
      "id": 0,
      "name": "string",
      "image": "http://foodgram.example.org/media/recipes/images/image.png",
      "cooking_time": 1
    }
  ],
  "recipes_count": 0,
  "avatar": "http://foodgram.example.org/media/users/image.png"
}
```

---

### 4. Скачать список покупок

**GET**

```
http://localhost:8080/api/recipes/download_shopping_cart/
```

**Ответ:**
Текстовый файл `.txt` со списком ингредиентов и их количеством.

---

## Автор

Елизавета Удоденко



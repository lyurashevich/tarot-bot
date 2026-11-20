# Tarot bot

Telegram-бот для раскладов на таро. План разработки: [PLAN.md](PLAN.md).

## Запуск для разработки

1. Установить зависимости: `uv sync`
2. Скопировать `.env.example` в `.env` и вписать `BOT_TOKEN` от @BotFather.
3. Поднять базу: `docker compose up -d`
4. Применить миграции: `uv run alembic upgrade head`
5. Запустить бота: `uv run python -m bot`

## Структура

```
bot/
  __main__.py     точка входа: настройки, база, запуск polling
  config.py       настройки из переменных окружения / .env
  db/             базовый класс моделей и фабрика сессий
  handlers/       обработчики команд и сообщений
migrations/       миграции Alembic
```

## Проверки

- Линтер: `uv run ruff check .`
- Тесты: `uv run pytest`

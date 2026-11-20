# Tarot bot

Telegram-бот для раскладов на таро. План разработки: [PLAN.md](PLAN.md).

## Запуск для разработки

1. Установить зависимости: `uv sync`
2. Скопировать `.env.example` в `.env` и вписать `BOT_TOKEN` от @BotFather.
3. Поднять базу: `docker compose up -d`
4. Применить миграции (они же добавляют в базу 78 карт): `uv run alembic upgrade head`
5. Один раз загрузить картинки колоды (см. ниже).
6. Запустить бота: `uv run python -m bot`

## Картинки колоды

Картинки хранятся на серверах Telegram, в базе только их `file_id`.
Скрипт уменьшает картинки до 1280 px по высоте, делает перевёрнутые копии,
публикует всё в закрытый канал-хранилище и сохраняет `file_id` в базу.

Нужно: закрытый канал, бот в нём администратор с правом публикации,
ID канала в `.env` как `STORAGE_CHAT_ID`. Файлы называются
`major_arcana_fool.png`, `minor_arcana_cups_queen.png` и т. п.

```bash
# проверить имена файлов и обработку, без Telegram и базы
uv run python -m scripts.import_deck --source ~/Downloads/tarot --dry-run
# загрузить (около 8 минут: Telegram ограничивает частоту сообщений в канале)
uv run python -m scripts.import_deck --source ~/Downloads/tarot
```

После смены бота (токена) `file_id` перестают работать — запустите скрипт заново.

## Структура

```
bot/
  __main__.py     точка входа: настройки, база, запуск polling
  config.py       настройки из переменных окружения / .env
  db/             базовый класс моделей и фабрика сессий
  handlers/       обработчики команд и сообщений
scripts/          разовые скрипты (импорт колоды)
migrations/       миграции Alembic
```

## Проверки

- Линтер: `uv run ruff check .`
- Тесты: `uv run pytest`

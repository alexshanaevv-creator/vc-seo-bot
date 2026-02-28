# VC SEO Bot — Контекст проекта

## Что это
Бот автоматически генерирует SEO-статьи через Claude API
и публикует их на vc.ru (Osnova API).

## Почему перенесли с Railway
Railway имеет нерусский IP — vc.ru блокировал публикации.
Перенесли на VPS с русским IP.

## Хостинг
- VPS: reg.cloud, Ubuntu 24.04
- Путь: /home/user/vc-seo-bot

## GitHub
https://github.com/alexshanaevv-creator/vc-seo-bot

## Структура проекта
- `main.py` — точка входа
- `app.py` — основная логика / Flask
- `generator.py` — генерация статей через Claude API
- `publisher.py` — публикация на vc.ru (Osnova API)
- `parser.py` — парсинг тем/данных
- `photos.py` — работа с фото
- `config.py` — конфигурация

## Как начать новую сессию
Скажи: "Читай CLAUDE.md и продолжаем работу над проектом"

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

## Агенты (Oh-My-ClaudeCode стиль)
Специализированные субагенты в `.claude/agents/`:

| Агент | Когда использовать |
|---|---|
| `@topic-finder` | Найти актуальные темы для статей |
| `@article-writer` | Написать SEO-статью по теме |
| `@vc-publisher` | Опубликовать/сохранить черновик на vc.ru |
| `@seo-orchestrator` | Полный цикл: темы → статья → публикация |

### Примеры команд
- "найди темы для статей" → запускает `topic-finder`
- "напиши статью про массажные кресла до 100к" → запускает `article-writer`
- "опубликуй последнюю статью как черновик" → запускает `vc-publisher`
- "полный цикл, автопилот" → запускает `seo-orchestrator`

## Как начать новую сессию
Скажи: "Читай CLAUDE.md и продолжаем работу над проектом"

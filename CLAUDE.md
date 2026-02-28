# VC SEO Bot — Контекст проекта

## Что это
Бот автоматически генерирует SEO-лонгриды через Claude / Gemini API
и публикует их на vc.ru (Osnova API). Управляется через веб-интерфейс (Flask PWA).

## Почему перенесли с Railway
Railway имеет нерусский IP — vc.ru блокировал публикации.
Перенесли на VPS с русским IP.

## Хостинг
- VPS: reg.cloud, Ubuntu 24.04
- Рабочая директория: `/home/user/vc_seo_bot/` (с подчёркиванием — актуальная)
- `/home/user/vc-seo-bot/` (с дефисом) — старый дубль, не использовать

## GitHub
https://github.com/alexshanaevv-creator/vc-seo-bot
Ветка с последними изменениями: `claude/refactor-01BvSYfTp7bVATRKbHtUH2ad`

## Структура проекта (`/home/user/vc_seo_bot/`)
- `app.py` — Flask веб-интерфейс + все API эндпоинты
- `generator.py` — генерация статей (Claude + Gemini)
- `publisher.py` — публикация на vc.ru (Osnova API, EditorJS-блоки)
- `photos.py` — работа с фото (локально / Яндекс.Диск / Pexels) + RuTube
- `config.py` — конфигурация (все ключи и настройки)
- `parser.py` — парсинг тем/данных конкурентов
- `main.py` — точка входа для gunicorn

## Текущий статус (обновлено 2026-02-28)

### Реализовано ✅
- Два типа статей: **Экспертная** (Claude Opus, только позитив) / **Общетематическая** (Gemini Flash, бесплатно)
- `GeneratedArticle` — 18 полей: title, meta_description, keywords, breadcrumbs, brief (AI GEO),
  intro, about_text, sections, specs_table, faq, comparison, for_whom, expert_comment,
  reviews, videos, conclusion, image_alts
- Источники фото: локальная папка (ротация) / Яндекс.Диск / Pexels
- RuTube: вставка по ссылке + поиск из интерфейса → iframe embed
- Веб-поиск (DuckDuckGo) + редактор одобренных данных → передаётся в промпт
- Поле характеристик товара/услуги → используется для точных цифр в статье
- publisher.py собирает все 18 секций в EditorJS-блоки для VC.RU
- PWA: устанавливается как приложение на телефон/ПК
- 4 новых API: `/api/search-web`, `/api/search-images`, `/api/yandex-disk`, `/api/search-rutube`
- Код проверен (`python -c "import app, generator, photos, publisher, config"` → OK)

### Что нужно для запуска
Заполнить в `config.py` или задать env-переменные:

| Переменная | Где взять | Обязательна |
|---|---|---|
| `ANTHROPIC_API_KEY` | console.anthropic.com | Для Expert-статей |
| `GEMINI_API_KEY` | aistudio.google.com | Для General-статей (бесплатно) |
| `VC_TOKEN` | DevTools на vc.ru → X-Device-Token | Для публикации |
| `PEXELS_API_KEY` | pexels.com/api | Для поиска фото (бесплатно) |

### Известные проблемы
- Anthropic API кредиты закончились → нужно пополнить на console.anthropic.com → Billing
- Коммит-подпись через `/tmp/code-sign` возвращает 400 при определённых условиях среды
  (workaround: создавать ветку `claude/...` и пушить туда)

## Следующие задачи
- [ ] Пополнить Anthropic API кредиты
- [ ] Протестировать полный цикл: генерация → превью → публикация черновика на VC.RU
- [ ] Получить GEMINI_API_KEY и проверить General-тип
- [ ] Получить PEXELS_API_KEY и проверить поиск фото
- [ ] Проверить Яндекс.Диск с реальной ссылкой
- [ ] Настроить gunicorn / systemd на VPS для автозапуска

## Как начать новую сессию
Скажи: "Читай CLAUDE.md и продолжаем работу"

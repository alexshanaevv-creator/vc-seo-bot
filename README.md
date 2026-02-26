# VC.RU SEO Bot

Автоматическая генерация и публикация SEO-лонгридов на VC.RU.

## Быстрый старт

### 1. Установка зависимостей
```bash
cd vc_seo_bot
pip install -r requirements.txt
```

### 2. Настройка `config.py`

| Параметр | Как получить |
|---|---|
| `ANTHROPIC_API_KEY` | [console.anthropic.com](https://console.anthropic.com) → API Keys |
| `VC_TOKEN` | Войдите на vc.ru → DevTools → Network → любой запрос к api.vc.ru → заголовок `X-Device-Token` |
| `COMPETITOR_URLS` | URL страниц блогов конкурентов |
| `NICHE_KEYWORDS` | Ключевые слова вашей ниши |
| `YOUR_SITE_URL` | Ссылка на ваш сайт |
| `PHOTOS_DIR` | Папка с вашими фото |

### 3. Запуск

```bash
# Показать найденные темы (без генерации)
python main.py --list-topics

# Сгенерировать 1 статью (черновик)
python main.py

# Сгенерировать 3 статьи (черновики)
python main.py --count 3

# Написать статью на конкретную тему
python main.py --topic "Как увеличить конверсию сайта в 2025"

# Генерировать и сразу публиковать
python main.py --count 2 --publish
```

## Структура проекта

```
vc_seo_bot/
├── config.py        # Все настройки (заполнить!)
├── main.py          # Главный скрипт / CLI
├── parser.py        # Парсер трендов и конкурентов
├── generator.py     # Генератор статей через Claude API
├── publisher.py     # Публикация на VC.RU через Osnova API
├── photos.py        # Менеджер фотографий с ротацией
├── photos/          # Папка с вашими фото (создайте сами)
├── requirements.txt
├── bot.log          # Лог работы
└── processed_topics.json  # Уже обработанные темы (не дублировать)
```

## Как получить X-Device-Token для VC.RU

1. Откройте [vc.ru](https://vc.ru) и войдите в аккаунт
2. Нажмите F12 → вкладка **Network**
3. Обновите страницу или нажмите любую кнопку
4. Найдите любой запрос к `api.vc.ru`
5. Перейдите в **Headers** → **Request Headers**
6. Скопируйте значение `X-Device-Token`

## Настройка публикации в компанию/сообщество

Если хотите публиковать от имени компании на VC.RU:
1. Откройте страницу компании на VC.RU
2. В URL найдите числовой ID: `vc.ru/company/XXXXX`
3. Укажите `VC_SUBSITE_ID = XXXXX` в `config.py`

## Автозапуск по расписанию (cron)

```bash
# Публиковать 1 статью каждый день в 10:00
0 10 * * * cd /path/to/vc_seo_bot && python main.py --publish >> cron.log 2>&1
```

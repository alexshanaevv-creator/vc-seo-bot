"""
Конфигурация бота для автопубликации на VC.RU
Заполните все значения перед запуском.
"""

# ─── Claude / Anthropic API ───────────────────────────────────────────────────
ANTHROPIC_API_KEY = "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"

# ─── VC.RU (Osnova) ───────────────────────────────────────────────────────────
# Как получить токен:
#  1. Войдите на vc.ru в браузере
#  2. Откройте DevTools → Network → любой запрос к api.vc.ru
#  3. Скопируйте значение заголовка X-Device-Token
VC_TOKEN = "SliUKGUm9TIMLtZm8v4ZxXbFG-qyJGv1jjtARLAo"
VC_BASE_URL = "https://api.vc.ru/v2.8"
VC_SUBSITE_ID = None   # None = личный блог. Для компании — ID субсайта (число)

# ─── Фото ────────────────────────────────────────────────────────────────────
PHOTOS_DIR = "./photos"                   # Папка с вашими фото (jpg/png/webp)
PHOTOS_PER_ARTICLE = 3                   # Сколько фото вставлять в статью

# ─── Парсинг конкурентов / трендов ───────────────────────────────────────────
# URL сайтов конкурентов для парсинга свежих статей
COMPETITOR_URLS = [
    # "https://example.com/blog",
]
# Ключевые слова ниши для поиска трендов в Google News
NICHE_KEYWORDS = [
    "массажные кресла",
    "массажное кресло для дома",
    "лучшие массажные кресла",
    "купить массажное кресло",
    "массажное кресло Россия",
]
# Ссылка на ваш сайт для вставки в статьи
YOUR_SITE_URL = "https://osari.ru/massagnie-kresla"
YOUR_SITE_ANCHOR = "массажные кресла"

# ─── Параметры генерации статей ──────────────────────────────────────────────
ARTICLE_MIN_WORDS = 2000
ARTICLE_LANGUAGE = "Russian"
ARTICLE_TONE = "экспертный, информативный, с практическими советами"
ARTICLE_LINKS_COUNT = 2                  # Сколько ссылок на сайт вставить
PUBLISH_AS_DRAFT = True                  # True = сохранять как черновик, False = сразу публиковать

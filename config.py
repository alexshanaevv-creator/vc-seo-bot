"""
Конфигурация бота для автопубликации на VC.RU
Заполните все значения перед запуском.
"""
import os
from dotenv import load_dotenv
load_dotenv()

# ─── Claude / Anthropic API ───────────────────────────────────────────────────
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# ─── VC.RU (Osnova) ───────────────────────────────────────────────────────────
# Как получить токен:
#  1. Войдите на vc.ru в браузере
#  2. Откройте DevTools → Network → любой запрос к api.vc.ru
#  3. Скопируйте значение заголовка X-Device-Token
VC_TOKEN = os.environ.get("VC_TOKEN", "")
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

# ─── Gemini API ───────────────────────────────────────────────────────────────
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = "gemini-2.0-flash"

# ─── LLM Provider ────────────────────────────────────────────────────────────
# "auto" = expert→Claude, general→Gemini | "claude" | "gemini"
LLM_PROVIDER = "auto"
CLAUDE_MODEL = "claude-opus-4-6"

# ─── Pexels API ──────────────────────────────────────────────────────────────
PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY", "")

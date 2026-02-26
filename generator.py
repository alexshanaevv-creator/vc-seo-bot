"""
Генератор SEO-лонгридов через Claude API.
Создаёт структурированные статьи с заголовками, подзаголовками, списками,
вставками ссылок на ваш сайт и плейсхолдерами для фото.
"""

import re
import logging
from dataclasses import dataclass, field

import anthropic

logger = logging.getLogger(__name__)


@dataclass
class GeneratedArticle:
    title: str
    intro: str          # Первый абзац — SEO-лид
    sections: list[dict] = field(default_factory=list)
    # section = {
    #   "heading": str,
    #   "paragraphs": [str, ...],
    #   "has_image_placeholder": bool,   # здесь вставим фото
    #   "list_items": [str, ...],        # если есть маркированный список
    # }
    conclusion: str = ""
    meta_description: str = ""          # ~160 символов для SEO
    keywords: list[str] = field(default_factory=list)


SYSTEM_PROMPT = """Ты — опытный SEO-копирайтер, специализирующийся на экспертных лонгридах
для российской бизнес-аудитории. Пишешь глубоко, структурированно, с конкретными примерами
и цифрами. Стиль — экспертный, но живой, без канцелярщины."""


def _build_prompt(
    topic_title: str,
    topic_description: str,
    niche_keywords: list[str],
    site_url: str,
    site_anchor: str,
    min_words: int,
    links_count: int,
    tone: str,
    image_count: int,
) -> str:
    kw_str = ", ".join(niche_keywords) if niche_keywords else topic_title
    anchor_variants = ", ".join([f'"{site_anchor}"', f'"подробнее на {site_anchor}"', f'"читайте на {site_anchor}"'])

    return f"""Напиши SEO-лонгрид на тему: «{topic_title}»

Контекст темы: {topic_description or "нет дополнительного контекста"}

ОБЯЗАТЕЛЬНЫЕ ТРЕБОВАНИЯ:
1. Объём: не менее {min_words} слов
2. Тон: {tone}
3. Ключевые слова для органичного вхождения: {kw_str}
4. Вставь ровно {links_count} ссылки на {site_url} — используй естественные анкоры ({anchor_variants})
5. Структура должна включать:
   - Цепляющий заголовок (H1)
   - Введение (2-3 абзаца, обозначь проблему/ценность)
   - 5-7 разделов с подзаголовками (H2)
   - Внутри разделов: абзацы + минимум 2 маркированных или нумерованных списка
   - Заключение с призывом к действию
6. Отметь места для вставки фото маркером [ФОТО] — ровно {image_count} штуки,
   размести их равномерно (не в начале и не в конце)

ФОРМАТ ОТВЕТА — строго JSON без лишнего текста:
{{
  "title": "заголовок статьи",
  "meta_description": "описание для SEO, 150-160 символов",
  "keywords": ["кл.слово1", "кл.слово2", "кл.слово3", "кл.слово4", "кл.слово5"],
  "intro": "вводные абзацы через \\n\\n",
  "sections": [
    {{
      "heading": "Подзаголовок раздела",
      "paragraphs": ["абзац 1", "абзац 2"],
      "list_items": ["пункт 1", "пункт 2", "пункт 3"],
      "has_image_placeholder": false
    }}
  ],
  "conclusion": "заключительный текст"
}}

Для разделов, где стоит [ФОТО], выставляй "has_image_placeholder": true.
Ссылки вставляй прямо в текст абзацев в формате HTML: <a href="{site_url}">{site_anchor}</a>"""


def generate_article(
    topic_title: str,
    topic_description: str,
    niche_keywords: list[str],
    site_url: str,
    site_anchor: str,
    api_key: str,
    min_words: int = 2000,
    links_count: int = 2,
    tone: str = "экспертный, информативный",
    image_count: int = 3,
    model: str = "claude-opus-4-6",
) -> GeneratedArticle:
    """Генерирует статью через Claude API и возвращает структурированный объект."""

    client = anthropic.Anthropic(api_key=api_key)

    prompt = _build_prompt(
        topic_title=topic_title,
        topic_description=topic_description,
        niche_keywords=niche_keywords,
        site_url=site_url,
        site_anchor=site_anchor,
        min_words=min_words,
        links_count=links_count,
        tone=tone,
        image_count=image_count,
    )

    logger.info(f"Generating article: «{topic_title}»")

    message = client.messages.create(
        model=model,
        max_tokens=16000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
        extra_headers={"anthropic-beta": "output-128k-2025-02-19"},
    )

    import json

    raw = message.content[0].text.strip()
    logger.debug(f"Raw Claude response (first 500 chars): {raw[:500]}")

    if not raw:
        raise ValueError("Claude returned empty response")

    # Пробуем извлечь JSON разными способами
    json_str = None

    # 1. Ищем ```json ... ``` или ``` ... ```
    json_match = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", raw)
    if json_match:
        candidate = json_match.group(1).strip()
        if candidate:
            json_str = candidate

    # 2. Если не нашли — берём от первой { до последней }
    if not json_str:
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1 and end > start:
            json_str = raw[start:end + 1]

    # 3. Пробуем весь текст как есть
    if not json_str:
        json_str = raw

    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        logger.error(f"JSON parse error: {e}\nRaw response:\n{raw[:2000]}")
        raise

    article = GeneratedArticle(
        title=data.get("title", topic_title),
        intro=data.get("intro", ""),
        sections=data.get("sections", []),
        conclusion=data.get("conclusion", ""),
        meta_description=data.get("meta_description", ""),
        keywords=data.get("keywords", []),
    )

    word_count = _count_words(article)
    logger.info(f"Article generated: «{article.title}» | ~{word_count} words")
    return article


def _count_words(article: GeneratedArticle) -> int:
    parts = [article.intro, article.conclusion]
    for s in article.sections:
        parts.extend(s.get("paragraphs", []))
        parts.extend(s.get("list_items", []))
    return sum(len(p.split()) for p in parts)

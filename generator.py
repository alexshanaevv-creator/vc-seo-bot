"""
Генератор SEO-лонгридов.
Поддерживает два типа статей и две модели:
  - Экспертная статья  → Claude claude-opus-4-6  (платно, высокое качество)
  - Общетематическая   → Gemini 2.0 Flash  (бесплатно, 1500 req/day)
"""

import json
import logging
import re
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class GeneratedArticle:
    title: str
    meta_description: str
    keywords: list = field(default_factory=list)
    breadcrumbs: list = field(default_factory=list)
    brief: str = ""
    intro: str = ""
    about_text: str = ""
    sections: list = field(default_factory=list)
    specs_table: list = field(default_factory=list)
    faq: list = field(default_factory=list)
    comparison: list = field(default_factory=list)
    for_whom: list = field(default_factory=list)
    expert_comment: str = ""
    reviews: list = field(default_factory=list)
    videos: list = field(default_factory=list)
    conclusion: str = ""
    image_alts: list = field(default_factory=list)


SYSTEM_EXPERT = """Ты — старший SEO-копирайтер и контент-стратег с 10-летним опытом.
Специализируешься на экспертных имиджевых статьях для российского бизнеса.
Пишешь убедительно, с конкретными цифрами и фактами. Стиль — авторитетный, живой, без канцелярщины.
ВАЖНО: только позитив и превосходство. Никакого негатива, скепсиса, слабых сторон или оговорок."""

SYSTEM_GENERAL = """Ты — опытный SEO-копирайтер, специализирующийся на информационных лонгридах
для российской аудитории. Пишешь нейтрально, структурированно, с конкретными примерами и цифрами.
Стиль — экспертный, информативный, без канцелярщины."""


def _build_prompt(
    article_type: str,
    topic_title: str,
    topic_description: str,
    product_specs: str,
    research_data: str,
    niche_keywords: list,
    site_url: str,
    site_anchor: str,
    min_words: int,
    links_count: int,
    tone: str,
    image_count: int,
    video_embeds: list,
) -> str:
    kw_str = ", ".join(niche_keywords) if niche_keywords else topic_title
    anchor_variants = f'"{site_anchor}", "подробнее на {site_anchor}", "читайте на {site_anchor}"'

    specs_block = f"\nХАРАКТЕРИСТИКИ (использовать для точных утверждений):\n{product_specs}\n" if product_specs.strip() else ""
    research_block = f"\nОДОБРЕННЫЕ ДАННЫЕ (обязательно включить):\n{research_data}\n" if research_data.strip() else ""

    if article_type == "expert":
        tone_instruction = "ТОН: только позитив, превосходство, выгоды. Никакого негатива."
    else:
        tone_instruction = f"ТОН: {tone}, нейтрально-информационный."

    videos_instruction = f"\nВИДЕО: отметь {len(video_embeds)} места маркерами [ВИДЕО_1]...[ВИДЕО_{len(video_embeds)}] равномерно.\n" if video_embeds else ""

    return f"""Напиши SEO-лонгрид: «{topic_title}»

Контекст: {topic_description or "нет"}
{specs_block}{research_block}
{tone_instruction}
{videos_instruction}
ТРЕБОВАНИЯ:
1. Объём: не менее {min_words} слов
2. Ключевые слова (органично): {kw_str}
3. Вставь {links_count} ссылки: <a href="{site_url}">{site_anchor}</a> (анкоры: {anchor_variants})
4. Отметь {image_count} мест для фото маркером [ФОТО] — равномерно

СТРУКТУРА: введение → 5-7 разделов H2 с абзацами и списками → заключение

ВЕРНИ СТРОГО JSON без markdown-обёртки:
{{
  "title": "H1 до 65 символов",
  "meta_description": "SEO описание 150-160 символов",
  "keywords": ["ключ1","ключ2","ключ3","ключ4","ключ5"],
  "breadcrumbs": ["Главная","Категория","Страница"],
  "brief": "3-5 предложений энциклопедического стиля с точными цифрами.",
  "intro": "вводный текст через \\n\\n",
  "about_text": "связный текст 500-800 слов с ключевыми словами о товаре/теме",
  "sections": [
    {{"heading":"Подзаголовок","paragraphs":["абзац1","абзац2"],"list_items":["пункт1","пункт2"],"has_image_placeholder":false,"has_video_placeholder":false,"video_index":null}}
  ],
  "specs_table": [{{"prop":"Характеристика","value":"Значение"}}],
  "faq": [{{"q":"Вопрос как ищут?","a":"Ответ 2-3 предложения."}}],
  "comparison": [{{"model":"Название","price":"цена","advantage":"преимущество","rating":"4.8/5"}}],
  "for_whom": ["Аудитория 1","Аудитория 2"],
  "expert_comment": "2-3 абзаца от имени эксперта.",
  "reviews": [{{"name":"Имя","date":"15 января 2025","rating":5,"text":"Текст отзыва."}}],
  "conclusion": "заключение с CTA",
  "image_alts": ["alt для фото 1","alt для фото 2"]
}}

Минимум: specs_table 6-8 строк, faq 5-6 вопросов, reviews 3-4 шт., for_whom 4-5 пунктов, image_alts {image_count} штук."""


def _parse_json(raw: str) -> dict:
    raw = raw.strip()
    if not raw:
        raise ValueError("Пустой ответ модели")
    m = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", raw)
    if m:
        try:
            return json.loads(m.group(1).strip())
        except json.JSONDecodeError:
            pass
    start, end = raw.find("{"), raw.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(raw[start:end + 1])
        except json.JSONDecodeError:
            pass
    return json.loads(raw)


def _build_article(data: dict, topic_title: str, video_embeds: list) -> GeneratedArticle:
    sections = data.get("sections", [])
    if video_embeds:
        for sec in sections:
            idx = sec.get("video_index")
            if idx is not None and isinstance(idx, int) and 0 < idx <= len(video_embeds):
                sec["video_html"] = video_embeds[idx - 1]
                sec["has_video_placeholder"] = True
    return GeneratedArticle(
        title=data.get("title", topic_title),
        meta_description=data.get("meta_description", ""),
        keywords=data.get("keywords", []),
        breadcrumbs=data.get("breadcrumbs", []),
        brief=data.get("brief", ""),
        intro=data.get("intro", ""),
        about_text=data.get("about_text", ""),
        sections=sections,
        specs_table=data.get("specs_table", []),
        faq=data.get("faq", []),
        comparison=data.get("comparison", []),
        for_whom=data.get("for_whom", []),
        expert_comment=data.get("expert_comment", ""),
        reviews=data.get("reviews", []),
        videos=video_embeds,
        conclusion=data.get("conclusion", ""),
        image_alts=data.get("image_alts", []),
    )


def _generate_claude(prompt: str, system: str, api_key: str, model: str) -> str:
    import anthropic
    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model=model,
        max_tokens=16000,
        system=system,
        messages=[{"role": "user", "content": prompt}],
        extra_headers={"anthropic-beta": "output-128k-2025-02-19"},
    )
    return message.content[0].text


def _generate_gemini(prompt: str, system: str, api_key: str, model: str) -> str:
    import google.generativeai as genai
    genai.configure(api_key=api_key)
    gmodel = genai.GenerativeModel(
        model_name=model,
        system_instruction=system,
        generation_config={"temperature": 0.7, "max_output_tokens": 8192},
    )
    return gmodel.generate_content(prompt).text


def generate_article(
    topic_title: str,
    topic_description: str = "",
    product_specs: str = "",
    research_data: str = "",
    article_type: str = "general",
    niche_keywords: list = None,
    site_url: str = "",
    site_anchor: str = "",
    min_words: int = 2000,
    links_count: int = 2,
    tone: str = "экспертный, информативный",
    image_count: int = 3,
    video_embeds: list = None,
    llm_provider: str = "auto",
    claude_api_key: str = "",
    gemini_api_key: str = "",
    claude_model: str = "claude-opus-4-6",
    gemini_model: str = "gemini-2.0-flash",
) -> GeneratedArticle:
    """
    Генерирует статью. llm_provider='auto': expert→Claude, general→Gemini Flash.
    """
    if niche_keywords is None:
        niche_keywords = []
    if video_embeds is None:
        video_embeds = []

    provider = llm_provider
    if provider == "auto":
        provider = "claude" if article_type == "expert" else "gemini"

    if provider == "gemini" and not gemini_api_key:
        if claude_api_key:
            logger.warning("Gemini key not set, falling back to Claude")
            provider = "claude"
        else:
            raise ValueError("Не указан GEMINI_API_KEY")
    if provider == "claude" and not claude_api_key:
        if gemini_api_key:
            logger.warning("Claude key not set, falling back to Gemini")
            provider = "gemini"
        else:
            raise ValueError("Не указан ANTHROPIC_API_KEY")

    system = SYSTEM_EXPERT if article_type == "expert" else SYSTEM_GENERAL
    prompt = _build_prompt(
        article_type=article_type,
        topic_title=topic_title,
        topic_description=topic_description,
        product_specs=product_specs,
        research_data=research_data,
        niche_keywords=niche_keywords,
        site_url=site_url,
        site_anchor=site_anchor,
        min_words=min_words,
        links_count=links_count,
        tone=tone,
        image_count=image_count,
        video_embeds=video_embeds,
    )

    logger.info(f"Generating [{article_type}] via [{provider}]: «{topic_title}»")

    if provider == "claude":
        raw = _generate_claude(prompt, system, claude_api_key, claude_model)
    else:
        raw = _generate_gemini(prompt, system, gemini_api_key, gemini_model)

    logger.debug(f"Raw response (first 500): {raw[:500]}")
    data = _parse_json(raw)
    article = _build_article(data, topic_title, video_embeds)
    logger.info(f"Done: «{article.title}» | ~{_count_words(article)} words | {provider}")
    return article


def _count_words(article: GeneratedArticle) -> int:
    parts = [article.intro, article.conclusion, article.about_text,
             article.brief, article.expert_comment]
    for s in article.sections:
        parts.extend(s.get("paragraphs", []))
        parts.extend(s.get("list_items", []))
    for r in article.reviews:
        parts.append(r.get("text", ""))
    for f in article.faq:
        parts.append(f.get("a", ""))
    return sum(len(p.split()) for p in parts if p)

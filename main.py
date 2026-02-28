"""
Главный оркестратор.

Использование:
  # Собрать темы из конкурентов/трендов и сгенерировать N статей:
  python main.py --count 3

  # Написать статью по конкретной теме:
  python main.py --topic "Как выбрать подрядчика по SEO в 2025 году"

  # Генерировать и сразу публиковать (не черновик):
  python main.py --count 2 --publish

  # Только показать найденные темы, без генерации:
  python main.py --list-topics

  # Сбросить историю использования фото:
  python main.py --reset-photos
"""

import argparse
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

import config
from generator import generate_article
from parser import collect_topics, Topic
from photos import pick_photos, reset_usage
from publisher import VcPublisher

# ─── Логирование ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("bot.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("main")

# ─── Журнал обработанных тем ─────────────────────────────────────────────────
PROCESSED_LOG = Path("processed_topics.json")


def load_processed() -> set[str]:
    if PROCESSED_LOG.exists():
        try:
            return set(json.loads(PROCESSED_LOG.read_text(encoding="utf-8")))
        except Exception:
            return set()
    return set()


def save_processed(processed: set[str]) -> None:
    PROCESSED_LOG.write_text(
        json.dumps(sorted(processed), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


# ─── Основная логика ─────────────────────────────────────────────────────────

def process_topic(
    topic: Topic,
    publisher: VcPublisher,
    publish: bool,
) -> bool:
    """Генерирует статью по теме и публикует/сохраняет черновик. Возвращает True при успехе."""
    logger.info(f"▶ Topic: «{topic.title}»")

    # 1. Генерируем статью
    try:
        article = generate_article(
            topic_title=topic.title,
            topic_description=topic.description,
            niche_keywords=config.NICHE_KEYWORDS,
            site_url=config.YOUR_SITE_URL,
            site_anchor=config.YOUR_SITE_ANCHOR,
            api_key=config.ANTHROPIC_API_KEY,
            min_words=config.ARTICLE_MIN_WORDS,
            links_count=config.ARTICLE_LINKS_COUNT,
            tone=config.ARTICLE_TONE,
            image_count=config.PHOTOS_PER_ARTICLE,
        )
    except Exception as e:
        logger.error(f"Generation failed for «{topic.title}»: {e}")
        return False

    # 2. Выбираем фото
    photos = pick_photos(config.PHOTOS_DIR, count=config.PHOTOS_PER_ARTICLE)
    if not photos:
        logger.warning("No photos available — article will be published without images")

    # 3. Сохраняем статью локально (всегда, независимо от публикации)
    _save_article_locally(article)

    # 4. Публикуем
    result = publisher.publish_article(
        article=article,
        image_paths=photos,
        subsite_id=config.VC_SUBSITE_ID,
        publish=publish,
    )

    if result:
        entry_url = result.get("url") or f"https://vc.ru/id/{result.get('id', '?')}"
        status = "PUBLISHED" if publish else "DRAFT"
        logger.info(f"✓ [{status}] «{article.title}» → {entry_url}")
        return True
    else:
        logger.error(f"✗ Failed to create entry for «{topic.title}» (article saved locally)")
        return False


def _save_article_locally(article) -> None:
    """Сохраняет статью в HTML-файл для просмотра/копипасты."""
    output_dir = Path("articles")
    output_dir.mkdir(exist_ok=True)

    safe_name = "".join(c if c.isalnum() or c in " _-" else "_" for c in article.title)[:60]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = output_dir / f"{timestamp}_{safe_name}.html"

    sections_html = ""
    for section in article.sections:
        sections_html += f'<h2>{section.get("heading", "")}</h2>\n'
        for para in section.get("paragraphs", []):
            sections_html += f"<p>{para}</p>\n"
        items = section.get("list_items", [])
        if items:
            sections_html += "<ul>\n" + "".join(f"  <li>{it}</li>\n" for it in items) + "</ul>\n"
        if section.get("has_image_placeholder"):
            sections_html += "<p><em>[ФОТО]</em></p>\n"

    html = f"""<!DOCTYPE html>
<html lang="ru"><head><meta charset="utf-8">
<title>{article.title}</title>
<style>body{{max-width:860px;margin:40px auto;font-family:Georgia,serif;line-height:1.7;padding:0 20px}}
h1{{font-size:2em;margin-bottom:.3em}}h2{{margin-top:1.8em;color:#222}}
p{{margin:.8em 0}}ul{{margin:.5em 0 1em 1.5em}}
.meta{{color:#888;font-size:.9em;margin-bottom:2em}}</style>
</head><body>
<h1>{article.title}</h1>
<p class="meta">{article.meta_description}</p>
{article.intro.replace(chr(10)*2, "</p><p>")}
{sections_html}
<h2>Заключение</h2>
<p>{article.conclusion.replace(chr(10)*2, "</p><p>")}</p>
</body></html>"""

    filepath.write_text(html, encoding="utf-8")
    logger.info(f"Article saved locally: {filepath}")


def run(
    count: int = 1,
    forced_topic: str | None = None,
    publish: bool = False,
    list_only: bool = False,
) -> None:
    publisher = VcPublisher(token=config.VC_TOKEN, base_url=config.VC_BASE_URL)
    processed = load_processed()

    if forced_topic:
        # Режим одной конкретной темы
        topic = Topic(
            title=forced_topic,
            description="",
            source_url="",
            source="manual",
        )
        process_topic(topic, publisher, publish=publish)
        processed.add(forced_topic)
        save_processed(processed)
        return

    # Собираем темы
    logger.info("Collecting topics from competitors and trends…")
    all_topics = collect_topics(
        competitor_urls=config.COMPETITOR_URLS,
        niche_keywords=config.NICHE_KEYWORDS,
        limit=50,
    )

    if list_only:
        print(f"\n{'─'*60}")
        print(f"Found {len(all_topics)} topics:")
        for i, t in enumerate(all_topics, 1):
            print(f"  {i:2}. [{t.source}] {t.title}")
        print(f"{'─'*60}\n")
        return

    # Фильтруем уже обработанные
    new_topics = [t for t in all_topics if t.title not in processed]
    if not new_topics:
        logger.info("No new topics found. All available topics already processed.")
        return

    logger.info(f"New topics available: {len(new_topics)}, will process: {min(count, len(new_topics))}")

    success_count = 0
    for topic in new_topics[:count]:
        ok = process_topic(topic, publisher, publish=publish)
        if ok:
            processed.add(topic.title)
            save_processed(processed)
            success_count += 1
        # Пауза между статьями чтобы не нагружать API
        if success_count < min(count, len(new_topics)):
            time.sleep(5)

    logger.info(f"Done. {success_count}/{min(count, len(new_topics))} articles processed.")


# ─── CLI ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="SEO-бот для автогенерации и публикации статей на VC.RU"
    )
    parser.add_argument(
        "--count", "-n",
        type=int,
        default=1,
        help="Сколько статей сгенерировать (по умолчанию: 1)",
    )
    parser.add_argument(
        "--topic", "-t",
        type=str,
        default=None,
        help="Написать статью на конкретную тему",
    )
    parser.add_argument(
        "--publish",
        action="store_true",
        default=not config.PUBLISH_AS_DRAFT,
        help="Опубликовать сразу (по умолчанию: черновик)",
    )
    parser.add_argument(
        "--list-topics",
        action="store_true",
        help="Только показать найденные темы, без генерации",
    )
    parser.add_argument(
        "--reset-photos",
        action="store_true",
        help="Сбросить историю использования фотографий",
    )

    args = parser.parse_args()

    if args.reset_photos:
        reset_usage()
        print("Photo usage history reset.")
        return

    # Проверка обязательных настроек
    if config.ANTHROPIC_API_KEY.startswith("sk-ant-..."):
        print("ERROR: Укажите ANTHROPIC_API_KEY в config.py")
        sys.exit(1)
    if config.VC_TOKEN == "YOUR_VC_DEVICE_TOKEN":
        print("ERROR: Укажите VC_TOKEN в config.py")
        sys.exit(1)

    publish_mode = args.publish
    mode_label = "PUBLISH" if publish_mode else "DRAFT"
    print(f"\n{'='*60}")
    print(f"  VC.RU SEO Bot  |  {datetime.now():%Y-%m-%d %H:%M}  |  mode={mode_label}")
    print(f"{'='*60}\n")

    run(
        count=args.count,
        forced_topic=args.topic,
        publish=publish_mode,
        list_only=args.list_topics,
    )


if __name__ == "__main__":
    main()

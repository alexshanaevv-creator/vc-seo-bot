"""
Публикатор на VC.RU через Osnova API.

Документация API: https://osnova.io/api/
Формат контента: EditorJS-совместимые блоки.
"""

import json
import logging
import mimetypes
from pathlib import Path
from typing import Optional

import requests

from generator import GeneratedArticle

logger = logging.getLogger(__name__)


class VcPublisher:
    """Клиент для публикации статей на VC.RU через Osnova API."""

    def __init__(self, token: str, base_url: str = "https://api.vc.ru/v2.8"):
        self.token = token
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({
            "X-Device-Token": token,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
        })
        self.session.proxies = {"http": None, "https": None}
        self.session.trust_env = False

    # ─── Загрузка фото ───────────────────────────────────────────────────────

    def upload_image(self, image_path: str | Path) -> Optional[dict]:
        """Загружает изображение на VC.RU. Возвращает dict с uuid/width/height/url."""
        image_path = Path(image_path)
        mime, _ = mimetypes.guess_type(str(image_path))
        mime = mime or "image/jpeg"
        try:
            with open(image_path, "rb") as f:
                resp = self.session.post(
                    f"{self.base_url}/uploader/upload",
                    files={"file": (image_path.name, f, mime)},
                    timeout=60,
                )
            resp.raise_for_status()
            data = resp.json()
            img_data = (
                data.get("result", {}).get("data")
                or data.get("data")
                or data
            )
            logger.info(f"Image uploaded: {image_path.name} → {img_data.get('url', '?')}")
            return img_data
        except Exception as e:
            logger.error(f"Upload failed for {image_path.name}: {e}")
            return None

    # ─── EditorJS блоки ──────────────────────────────────────────────────────

    @staticmethod
    def _paragraph(html: str) -> dict:
        return {"type": "paragraph", "data": {"text": html}}

    @staticmethod
    def _header(text: str, level: int = 2) -> dict:
        return {"type": "header", "data": {"text": text, "level": level}}

    @staticmethod
    def _list_block(items: list, style: str = "unordered") -> dict:
        return {"type": "list", "data": {"style": style, "items": items}}

    @staticmethod
    def _image_block(img_data: dict, caption: str = "") -> dict:
        return {
            "type": "image",
            "data": {
                "file": {
                    "url": img_data.get("url", ""),
                    "uuid": img_data.get("uuid", ""),
                    "width": img_data.get("width", 1200),
                    "height": img_data.get("height", 630),
                },
                "caption": caption,
                "withBorder": False,
                "stretched": True,
                "withBackground": False,
            },
        }

    @staticmethod
    def _table_block(rows: list[list[str]], with_heading: bool = False) -> dict:
        return {
            "type": "table",
            "data": {"withHeadings": with_heading, "content": rows},
        }

    @staticmethod
    def _delimiter() -> dict:
        return {"type": "delimiter", "data": {}}

    @staticmethod
    def _embed_block(embed_html: str) -> dict:
        """Вставляет iframe как raw HTML (для видео RuTube)."""
        return {"type": "paragraph", "data": {"text": embed_html}}

    # ─── Сборка блоков ────────────────────────────────────────────────────────

    def build_blocks(
        self,
        article: GeneratedArticle,
        uploaded_images: list[dict],
    ) -> list[dict]:
        """
        Собирает полный список EditorJS-блоков из статьи со всеми SEO/AI GEO секциями.
        """
        blocks: list[dict] = []
        img_queue = list(uploaded_images)

        # ── AI GEO: краткое энциклопедическое описание
        if article.brief:
            blocks.append(self._header("Кратко о теме", level=3))
            blocks.append(self._paragraph(f"<i>{article.brief}</i>"))
            blocks.append(self._delimiter())

        # ── Введение
        for para in article.intro.split("\n\n"):
            if para.strip():
                blocks.append(self._paragraph(para.strip()))

        # Первое фото после введения
        if img_queue:
            blocks.append(self._image_block(img_queue.pop(0)))

        # ── Основные разделы
        video_index = 0
        for section in article.sections:
            heading = section.get("heading", "")
            paragraphs = section.get("paragraphs", [])
            list_items = section.get("list_items", [])
            has_photo = section.get("has_image_placeholder", False)
            has_video = section.get("has_video_placeholder", False)
            video_html = section.get("video_html", "")

            if heading:
                blocks.append(self._header(heading, level=2))

            for para in paragraphs:
                if para.strip():
                    blocks.append(self._paragraph(para.strip()))

            if list_items:
                blocks.append(self._list_block(list_items))

            if has_photo and img_queue:
                alt = ""
                if video_index < len(article.image_alts):
                    alt = article.image_alts[video_index]
                blocks.append(self._image_block(img_queue.pop(0), caption=alt))
                video_index += 1

            if has_video and video_html:
                blocks.append(self._embed_block(video_html))

        # ── Таблица характеристик
        if article.specs_table:
            blocks.append(self._delimiter())
            blocks.append(self._header("Технические характеристики", level=2))
            rows = [[row["prop"], row["value"]] for row in article.specs_table]
            blocks.append(self._table_block(rows, with_heading=False))

        # ── О товаре (about_text) — SEO-текст 500-800 слов
        if article.about_text:
            blocks.append(self._delimiter())
            blocks.append(self._header("Подробнее о продукте", level=2))
            for para in article.about_text.split("\n\n"):
                if para.strip():
                    blocks.append(self._paragraph(para.strip()))

        # ── Сравнительная таблица
        if article.comparison:
            blocks.append(self._delimiter())
            blocks.append(self._header("Сравнение моделей", level=2))
            rows = [["Модель", "Цена", "Преимущество", "Рейтинг"]]
            for row in article.comparison:
                rows.append([row.get("model",""), row.get("price",""),
                              row.get("advantage",""), row.get("rating","")])
            blocks.append(self._table_block(rows, with_heading=True))

        # Остаток фото
        if img_queue:
            blocks.append(self._image_block(img_queue.pop(0)))

        # ── Для кого
        if article.for_whom:
            blocks.append(self._delimiter())
            blocks.append(self._header("Кому подойдёт", level=2))
            blocks.append(self._list_block(article.for_whom))

        # ── Экспертный комментарий
        if article.expert_comment:
            blocks.append(self._delimiter())
            blocks.append(self._header("Комментарий эксперта", level=2))
            for para in article.expert_comment.split("\n\n"):
                if para.strip():
                    blocks.append(self._paragraph(f"<i>{para.strip()}</i>"))

        # ── FAQ
        if article.faq:
            blocks.append(self._delimiter())
            blocks.append(self._header("Часто задаваемые вопросы", level=2))
            for item in article.faq:
                if item.get("q"):
                    blocks.append(self._header(item["q"], level=3))
                if item.get("a"):
                    blocks.append(self._paragraph(item["a"]))

        # ── Отзывы
        if article.reviews:
            blocks.append(self._delimiter())
            blocks.append(self._header("Отзывы покупателей", level=2))
            for r in article.reviews:
                stars = "★" * (r.get("rating") or 5) + "☆" * (5 - (r.get("rating") or 5))
                name_line = f"<b>{r.get('name', '')}</b> — {r.get('date', '')} {stars}"
                blocks.append(self._paragraph(name_line))
                if r.get("text"):
                    blocks.append(self._paragraph(r["text"]))

        # ── Заключение
        if article.conclusion:
            blocks.append(self._delimiter())
            blocks.append(self._header("Заключение", level=2))
            for para in article.conclusion.split("\n\n"):
                if para.strip():
                    blocks.append(self._paragraph(para.strip()))

        # Последнее фото (если осталось)
        for img_data in img_queue:
            blocks.insert(-1 if len(blocks) > 1 else len(blocks), self._image_block(img_data))

        return blocks

    # ─── Публикация ──────────────────────────────────────────────────────────

    def create_entry(
        self,
        article: GeneratedArticle,
        blocks: list[dict],
        subsite_id: Optional[int] = None,
        publish: bool = False,
    ) -> Optional[dict]:
        """Создаёт запись на VC.RU. publish=False → черновик."""
        payload = {
            "title": article.title,
            "text": json.dumps({"blocks": blocks, "version": "2.14"}),
        }
        if subsite_id:
            payload["subsite_id"] = str(subsite_id)
        if not publish:
            payload["is_published"] = "0"

        try:
            resp = self.session.post(
                f"{self.base_url}/entry/create",
                data=payload,
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            entry = data.get("result", {}).get("entry") or data.get("entry") or data
            entry_id = entry.get("id") or entry.get("entryId")
            entry_url = entry.get("url") or f"https://vc.ru/u/me/{entry_id}"
            logger.info(f"{'Published' if publish else 'Draft'}: «{article.title}» → {entry_url}")
            return entry
        except Exception as e:
            logger.error(f"create_entry failed: {e}")
            if hasattr(e, "response") and e.response is not None:
                logger.error(f"Response: {e.response.text[:500]}")
            return None

    def publish_article(
        self,
        article: GeneratedArticle,
        image_paths: list[str | Path],
        subsite_id: Optional[int] = None,
        publish: bool = False,
    ) -> Optional[dict]:
        """Полный цикл: загрузить фото → собрать блоки → создать запись."""
        uploaded = []
        for path in image_paths:
            img = self.upload_image(path)
            if img:
                uploaded.append(img)

        blocks = self.build_blocks(article, uploaded)
        return self.create_entry(
            article=article,
            blocks=blocks,
            subsite_id=subsite_id,
            publish=publish,
        )

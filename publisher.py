"""
Публикатор на VC.RU через Osnova API.

Документация API: https://osnova.io/api/
Формат контента: EditorJS-совместимые блоки.
"""

import logging
import mimetypes
import os
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
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "application/json",
            "Content-Type": "application/json",
        })
        # Обходим системный прокси для прямого подключения к VC.RU
        self.session.proxies = {"http": None, "https": None}
        self.session.trust_env = False

    # ─── Загрузка фото ───────────────────────────────────────────────────────

    def upload_image(self, image_path: str | Path) -> Optional[dict]:
        """
        Загружает изображение на VC.RU.
        Возвращает dict с uuid, width, height, url — или None при ошибке.
        """
        image_path = Path(image_path)
        mime, _ = mimetypes.guess_type(str(image_path))
        mime = mime or "image/jpeg"

        url = f"{self.base_url}/uploader/upload"
        try:
            with open(image_path, "rb") as f:
                resp = self.session.post(
                    url,
                    files={"file": (image_path.name, f, mime)},
                    timeout=60,
                )
            resp.raise_for_status()
            data = resp.json()
            # Ответ: {"result": {"data": {"uuid": "...", "url": "...", ...}}}
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

    # ─── Сборка блоков контента (EditorJS) ───────────────────────────────────

    @staticmethod
    def _paragraph_block(html_text: str) -> dict:
        return {"type": "paragraph", "data": {"text": html_text}}

    @staticmethod
    def _header_block(text: str, level: int = 2) -> dict:
        return {"type": "header", "data": {"text": text, "level": level}}

    @staticmethod
    def _list_block(items: list[str], style: str = "unordered") -> dict:
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

    def build_blocks(
        self,
        article: GeneratedArticle,
        uploaded_images: list[dict],
    ) -> list[dict]:
        """
        Собирает список EditorJS-блоков из статьи.
        uploaded_images — список результатов upload_image(), по порядку.
        """
        blocks: list[dict] = []
        img_queue = list(uploaded_images)  # копия, будем pop

        # Вводный текст
        for para in article.intro.split("\n\n"):
            if para.strip():
                blocks.append(self._paragraph_block(para.strip()))

        # Разделы
        for section in article.sections:
            heading = section.get("heading", "")
            paragraphs = section.get("paragraphs", [])
            list_items = section.get("list_items", [])
            has_photo = section.get("has_image_placeholder", False)

            if heading:
                blocks.append(self._header_block(heading, level=2))

            for para in paragraphs:
                if para.strip():
                    blocks.append(self._paragraph_block(para.strip()))

            if list_items:
                blocks.append(self._list_block(list_items))

            # Вставляем фото если нужно и есть в очереди
            if has_photo and img_queue:
                img_data = img_queue.pop(0)
                blocks.append(self._image_block(img_data))

        # Заключение
        if article.conclusion:
            blocks.append(self._header_block("Заключение", level=2))
            for para in article.conclusion.split("\n\n"):
                if para.strip():
                    blocks.append(self._paragraph_block(para.strip()))

        # Если остались незадействованные фото — добавляем перед заключением
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
        """
        Создаёт запись на VC.RU.
        publish=False → сохраняет как черновик.
        publish=True  → публикует немедленно.
        """
        payload = {
            "title": article.title,
            "entry": {
                "blocks": blocks,
                "version": "2.14",
            },
        }
        if subsite_id:
            payload["subsite_id"] = subsite_id

        if not publish:
            payload["is_published"] = 0
        url = f"{self.base_url}/entry/create"

        try:
            resp = self.session.post(url, json=payload, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            entry = data.get("result", {}).get("entry") or data.get("entry") or data
            entry_id = entry.get("id") or entry.get("entryId")
            entry_url = entry.get("url") or f"https://vc.ru/u/me/{entry_id}"
            logger.info(
                f"{'Published' if publish else 'Draft saved'}: «{article.title}» → {entry_url}"
            )
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
        """
        Полный цикл: загрузить фото → собрать блоки → создать запись.
        Возвращает dict записи или None при ошибке.
        """
        # 1. Загружаем фотографии
        uploaded = []
        for path in image_paths:
            img = self.upload_image(path)
            if img:
                uploaded.append(img)

        # 2. Собираем EditorJS-блоки
        blocks = self.build_blocks(article, uploaded)

        # 3. Создаём запись
        return self.create_entry(
            article=article,
            blocks=blocks,
            subsite_id=subsite_id,
            publish=publish,
        )

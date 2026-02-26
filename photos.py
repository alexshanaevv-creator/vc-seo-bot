"""
Менеджер фотографий.
Сканирует папку с вашими фото и выбирает изображения для статьи.
Поддерживает ротацию — не повторяет одно фото в разных статьях подряд.
"""

import json
import logging
import random
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
USAGE_LOG = Path(".photo_usage.json")  # Хранит историю использования


def _load_usage() -> dict[str, int]:
    """Загружает счётчик использования фото."""
    if USAGE_LOG.exists():
        try:
            return json.loads(USAGE_LOG.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save_usage(usage: dict[str, int]) -> None:
    USAGE_LOG.write_text(json.dumps(usage, ensure_ascii=False, indent=2), encoding="utf-8")


def scan_photos(photos_dir: str | Path) -> list[Path]:
    """Возвращает список всех поддерживаемых изображений в папке."""
    photos_dir = Path(photos_dir)
    if not photos_dir.exists():
        logger.warning(f"Photos directory not found: {photos_dir}")
        return []

    photos = [
        p for p in photos_dir.iterdir()
        if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS
    ]
    photos.sort(key=lambda p: p.name)
    logger.info(f"Found {len(photos)} photos in {photos_dir}")
    return photos


def pick_photos(
    photos_dir: str | Path,
    count: int = 3,
    seed: Optional[int] = None,
) -> list[Path]:
    """
    Выбирает `count` фото с ротацией (наименее использованные идут первыми).
    Позволяет избежать постоянного повторения одних и тех же снимков.
    """
    all_photos = scan_photos(photos_dir)
    if not all_photos:
        return []

    usage = _load_usage()

    # Сортируем по частоте использования (редко используемые — первые)
    sorted_photos = sorted(all_photos, key=lambda p: usage.get(p.name, 0))

    if seed is not None:
        random.seed(seed)

    # Берём пул из наименее использованных (2×count), затем рандомно выбираем
    pool = sorted_photos[:max(count * 2, len(sorted_photos) // 2 + 1)]
    selected = random.sample(pool, min(count, len(pool)))

    # Обновляем счётчик
    for photo in selected:
        usage[photo.name] = usage.get(photo.name, 0) + 1
    _save_usage(usage)

    logger.info(f"Selected photos: {[p.name for p in selected]}")
    return selected


def reset_usage() -> None:
    """Сбрасывает историю использования фотографий."""
    if USAGE_LOG.exists():
        USAGE_LOG.unlink()
    logger.info("Photo usage history reset")

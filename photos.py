"""
Менеджер фотографий.
Источники:
  1. Локальная папка ./photos/  (ротация — нет повторов)
  2. Яндекс.Диск — публичная папка по URL
  3. Pexels API  — поиск по запросу (бесплатный ключ)
"""

import json
import logging
import random
import re
import shutil
from pathlib import Path
from typing import Optional

import requests

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
USAGE_LOG = Path(".photo_usage.json")
DOWNLOAD_DIR = Path(".photo_cache")


# ─── Локальные фото ───────────────────────────────────────────────────────────

def _load_usage() -> dict:
    if USAGE_LOG.exists():
        try:
            return json.loads(USAGE_LOG.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save_usage(usage: dict) -> None:
    USAGE_LOG.write_text(json.dumps(usage, ensure_ascii=False, indent=2), encoding="utf-8")


def scan_photos(photos_dir: str | Path) -> list:
    photos_dir = Path(photos_dir)
    if not photos_dir.exists():
        logger.warning(f"Photos directory not found: {photos_dir}")
        return []
    photos = [p for p in photos_dir.iterdir()
              if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS]
    photos.sort(key=lambda p: p.name)
    return photos


def pick_photos(photos_dir: str | Path, count: int = 3, seed: Optional[int] = None) -> list:
    """Выбирает фото из локальной папки с ротацией."""
    all_photos = scan_photos(photos_dir)
    if not all_photos:
        return []
    usage = _load_usage()
    sorted_photos = sorted(all_photos, key=lambda p: usage.get(p.name, 0))
    if seed is not None:
        random.seed(seed)
    pool = sorted_photos[:max(count * 2, len(sorted_photos) // 2 + 1)]
    selected = random.sample(pool, min(count, len(pool)))
    for photo in selected:
        usage[photo.name] = usage.get(photo.name, 0) + 1
    _save_usage(usage)
    logger.info(f"Local photos: {[p.name for p in selected]}")
    return selected


def reset_usage() -> None:
    if USAGE_LOG.exists():
        USAGE_LOG.unlink()
    logger.info("Photo usage history reset")


# ─── Яндекс.Диск ─────────────────────────────────────────────────────────────

def list_yandex_disk_images(public_url: str) -> list:
    """Список изображений из публичной папки Яндекс.Диска."""
    try:
        resp = requests.get(
            "https://cloud-api.yandex.net/v1/disk/public/resources",
            params={"public_key": public_url, "limit": 50, "preview_size": "M"},
            timeout=15,
        )
        resp.raise_for_status()
        items = resp.json().get("_embedded", {}).get("items", [])
    except Exception as e:
        logger.error(f"Yandex.Disk list error: {e}")
        return []
    result = []
    for item in items:
        name = item.get("name", "")
        if not any(name.lower().endswith(ext) for ext in SUPPORTED_EXTENSIONS):
            if item.get("media_type") != "image":
                continue
        result.append({
            "name": name,
            "preview": item.get("preview", ""),
            "size": item.get("size", 0),
            "path": item.get("path", ""),
        })
    return result


def download_yandex_disk_file(public_url: str, file_path: str, local_name: str) -> Optional[Path]:
    """Скачивает файл из публичной папки Яндекс.Диска."""
    DOWNLOAD_DIR.mkdir(exist_ok=True)
    try:
        resp = requests.get(
            "https://cloud-api.yandex.net/v1/disk/public/resources/download",
            params={"public_key": public_url, "path": file_path},
            timeout=10,
        )
        resp.raise_for_status()
        file_url = resp.json().get("href")
        if not file_url:
            return None
        local_path = DOWNLOAD_DIR / local_name
        img_resp = requests.get(file_url, timeout=30, stream=True)
        img_resp.raise_for_status()
        with open(local_path, "wb") as f:
            shutil.copyfileobj(img_resp.raw, f)
        logger.info(f"Downloaded from Yandex.Disk: {local_name}")
        return local_path
    except Exception as e:
        logger.error(f"Yandex.Disk download error: {e}")
        return None


def fetch_yandex_disk_images(public_url: str, count: int = 3) -> list:
    """Скачивает первые N изображений из публичной папки."""
    items = list_yandex_disk_images(public_url)
    downloaded = []
    for item in items[:count]:
        p = download_yandex_disk_file(public_url, item["path"], item["name"])
        if p:
            downloaded.append(p)
    return downloaded


# ─── Pexels API ───────────────────────────────────────────────────────────────

def search_pexels_images(query: str, api_key: str, count: int = 6) -> list:
    """Поиск фото на Pexels. Бесплатный ключ: pexels.com/api/"""
    if not api_key:
        logger.warning("PEXELS_API_KEY not set")
        return []
    try:
        resp = requests.get(
            "https://api.pexels.com/v1/search",
            headers={"Authorization": api_key},
            params={"query": query, "per_page": count, "locale": "ru-RU"},
            timeout=15,
        )
        resp.raise_for_status()
        photos = resp.json().get("photos", [])
    except Exception as e:
        logger.error(f"Pexels error: {e}")
        return []
    return [
        {"id": p["id"], "url_preview": p["src"]["medium"],
         "url_original": p["src"]["original"],
         "photographer": p.get("photographer", ""), "alt": p.get("alt", query)}
        for p in photos
    ]


def download_pexels_photo(photo_url: str, filename: str) -> Optional[Path]:
    """Скачивает фото с Pexels по прямой ссылке."""
    DOWNLOAD_DIR.mkdir(exist_ok=True)
    local_path = DOWNLOAD_DIR / filename
    try:
        resp = requests.get(photo_url, timeout=30, stream=True)
        resp.raise_for_status()
        with open(local_path, "wb") as f:
            shutil.copyfileobj(resp.raw, f)
        logger.info(f"Downloaded from Pexels: {filename}")
        return local_path
    except Exception as e:
        logger.error(f"Pexels download error: {e}")
        return None


# ─── RuTube ───────────────────────────────────────────────────────────────────

def rutube_url_to_embed(url: str) -> str:
    """Конвертирует URL RuTube видео в iframe embed HTML."""
    m = re.search(r"rutube\.ru/(?:video|play/embed)/([a-zA-Z0-9]+)", url)
    if not m:
        logger.warning(f"Cannot parse RuTube URL: {url}")
        return ""
    video_id = m.group(1)
    return (
        f'<iframe width="720" height="405" src="https://rutube.ru/play/embed/{video_id}/" '
        f'frameBorder="0" allow="clipboard-write; autoplay" webkitAllowFullScreen '
        f'mozallowfullscreen allowFullScreen></iframe>'
    )


def search_rutube_videos(query: str, count: int = 6) -> list:
    """Поиск видео на RuTube по запросу."""
    try:
        resp = requests.get(
            "https://rutube.ru/api/search/video/",
            params={"query": query, "page": 1, "format": "json"},
            timeout=15,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        resp.raise_for_status()
        results = resp.json().get("results", [])
    except Exception as e:
        logger.error(f"RuTube search error: {e}")
        return []
    videos = []
    for v in results[:count]:
        video_id = v.get("id", "")
        url = f"https://rutube.ru/video/{video_id}/"
        videos.append({
            "id": video_id,
            "title": v.get("title", ""),
            "thumbnail": v.get("thumbnail_url", ""),
            "url": url,
            "embed_html": rutube_url_to_embed(url),
        })
    return videos

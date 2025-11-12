import os
import json
import re

try:
    from .utils import create_slug_from_text
except Exception:
    from utils import create_slug_from_text

def _safe_filename(text: str) -> str:
    # Simple sanitizer for filenames
    text = text.strip()
    text = re.sub(r'[\\/:*?"<>|]+', '-', text)
    return text


def get_existing_chapter_max(novel_dir: str) -> int:
    """Return the max chapterNumber already saved in novel_dir (based on leading numeric filename), 0 if none."""
    if not os.path.isdir(novel_dir):
        return 0
    max_num = 0
    for name in os.listdir(novel_dir):
        m = re.match(r'^(\d+)', name)
        if m:
            try:
                num = int(m.group(1))
                if num > max_num:
                    max_num = num
            except Exception:
                continue
    return max_num

def save_novel(novel: dict, chapters: list, base_dir: str = 'data') -> str:
    """Save a single novel's metadata and chapters to disk.

    - novel: dict with novel metadata
    - chapters: list of chapter dicts (should include 'chapterNumber' and 'plainTextContent' or 'content')
    - base_dir: where to create the novel folder (default 'data')

    Returns the path to the novel folder.
    """
    title = novel.get('title') or novel.get('slug') or novel.get('novelId')
    folder_name = create_slug_from_text(title)
    novel_dir = os.path.join(base_dir, folder_name)
    os.makedirs(novel_dir, exist_ok=True)

    # Write metadata.json
    metadata_path = os.path.join(novel_dir, 'metadata.json')
    with open(metadata_path, 'w', encoding='utf-8') as mf:
        json.dump(novel, mf, ensure_ascii=False, indent=2)

    # Write chapters. Do not overwrite existing chapter files (append behavior):
    for ch in chapters:
        ch_number = ch.get('chapterNumber', 0)
        ch_id = ch.get('chapterId') or ''
        ch_title = ch.get('title') or f'chapter-{ch_number}'
        safe_title = _safe_filename(ch_title)
        # Include chapter id in filename if available
        id_segment = f" - {ch_id}" if ch_id else ""
        filename = f"{ch_number:03d}{id_segment} - {safe_title}.txt"
        path = os.path.join(novel_dir, filename)
        # If file already exists, skip writing to preserve previous content (append behavior)
        if os.path.exists(path):
            continue
        content_text = ch.get('plainTextContent') or ch.get('content') or ''
        if not ch.get('plainTextContent') and ch.get('content'):
            # naive strip HTML tags
            content_text = re.sub(r'<[^>]+>', '', content_text)
        with open(path, 'w', encoding='utf-8') as cf:
            cf.write(content_text)

    return novel_dir

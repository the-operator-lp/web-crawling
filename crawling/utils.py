import json
import random
import datetime
import re
import time
from urllib.parse import urljoin

try:
    from .config import DEFAULT_MISSING_INFO, REQUEST_DELAY
except Exception:
    # Fallback when modules are imported as top-level scripts
    from config import DEFAULT_MISSING_INFO, REQUEST_DELAY

def initialize_json_files():
    """Creates or ensures the `data/` directory exists and seeds `data/genres.json` and `data/state.json`.

    This avoids creating top-level JSON files and prepares the folder structure for
    per-novel storage (data/<novel-slug>/metadata.json and chapter text files).
    If files already exist we don't overwrite them so partial crawls are preserved.
    """
    import os
    os.makedirs('data', exist_ok=True)
    genres_path = os.path.join('data', 'genres.json')
    if not os.path.exists(genres_path):
        with open(genres_path, 'w', encoding='utf-8') as f:
            json.dump([], f, ensure_ascii=False, indent=2)

    # Initialize state file if missing
    state_path = os.path.join('data', 'state.json')
    if not os.path.exists(state_path):
        initial_state = {
            "current_page": 1,
            "stories_crawled_count": 0,
            "processed_novels": {}
        }
        with open(state_path, 'w', encoding='utf-8') as f:
            json.dump(initial_state, f, ensure_ascii=False, indent=2)

    # Use logging instead of print where possible (main config will set handlers)
    try:
        import logging
        logging.getLogger(__name__).info(f"Initialized data directory and ensured {genres_path} and state.json exist.")
    except Exception:
        print(f"Initialized data directory and ensured {genres_path} and state.json exist.")

def create_slug_from_text(text):
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r'[àáạảãâầấậẩẫăằắặẳẵ]', 'a', text)
    text = re.sub(r'[èéẹẻẽêềếệểễ]', 'e', text)
    text = re.sub(r'[ìíịỉĩ]', 'i', text)
    text = re.sub(r'[òóọỏõôồốộổỗơờớợởỡ]', 'o', text)
    text = re.sub(r'[ùúụủũưừứựửữ]', 'u', text)
    text = re.sub(r'[ỳýỵỷỹ]', 'y', text)
    text = re.sub(r'[đ]', 'd', text)
    text = re.sub(r'\W+', '-', text)  # Replace non-alphanumeric with -
    text = re.sub(r'^-+|-+$', '', text)  # Remove leading/trailing -
    if not text:  # Handle case where title was all special characters
        return f"slug-{random.randint(1000,9999)}"
    return text

def format_datetime_for_json(dt_object):
    return {"$date": dt_object.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"}

def generate_random_dates_sequential(start_year=2021):
    year = random.randint(start_year, datetime.datetime.now().year - 1 if datetime.datetime.now().year > start_year else start_year)
    month = random.randint(1, 12)
    day = random.randint(1, 28)  # Keep it simple
    hour = random.randint(0, 23)
    minute = random.randint(0, 59)
    second = random.randint(0, 59)
    microsecond = random.randint(0, 999999)

    publication_date = datetime.datetime(year, month, day, hour, minute, second, microsecond)

    created_date_offset_days = random.randint(0, 30)
    created_date = publication_date + datetime.timedelta(days=created_date_offset_days,
                                                       hours=random.randint(0,23),
                                                       minutes=random.randint(0,59))

    updated_date_offset_days = random.randint(0, 10)
    updated_date = created_date + datetime.timedelta(days=updated_date_offset_days,
                                                    hours=random.randint(0,23),
                                                    minutes=random.randint(0,59))

    now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    publication_date = min(publication_date, now)
    created_date = min(created_date, now)
    updated_date = min(updated_date, now)

    created_date = max(created_date, publication_date)
    updated_date = max(updated_date, created_date)

    return format_datetime_for_json(publication_date), format_datetime_for_json(created_date), format_datetime_for_json(updated_date)

def generate_random_novel_numeric_fields():
    rating_average = round(random.uniform(0.0, 10.0), 1)
    total_views = random.randint(1000, 1000000)

    total_rating = random.randint(int(total_views * 0.01), int(total_views * 0.2))
    total_likes = random.randint(0, total_views // 2)
    total_comments = random.randint(0, total_likes // 2)
    total_upvotes = random.randint(0, total_likes)
    total_follow = random.randint(0, int(total_views * 0.1))

    views_this_year = random.randint(0, total_views)
    views_this_month = random.randint(0, views_this_year)
    views_this_week = random.randint(0, views_this_month)
    views_today = random.randint(0, views_this_week)

    pub_date, created_date, updated_date = generate_random_dates_sequential()

    return {
        "ratingAverage": rating_average,
        "totalRating": total_rating,
        "totalLikes": total_likes,
        "totalViews": total_views,
        "totalComments": total_comments,
        "totalUpvotes": total_upvotes,
        "totalFollow": total_follow,
        "viewsToday": views_today,
        "viewsThisWeek": views_this_week,
        "viewsThisMonth": views_this_month,
        "viewsThisYear": views_this_year,
        "publicationDate": pub_date,
        "created": created_date,
        "updated": updated_date,
    }

def generate_random_chapter_fields():
    view_count = random.randint(0, 100000)
    start_year = 2021
    year = random.randint(start_year, datetime.datetime.now().year - 1 if datetime.datetime.now().year > start_year else start_year)
    month = random.randint(1,12)
    day = random.randint(1,28)
    chapter_created_dt = datetime.datetime(year, month, day, random.randint(0,23), random.randint(0,59))

    chapter_updated_dt = chapter_created_dt + datetime.timedelta(days=random.randint(0,30), hours=random.randint(0,23))

    now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    chapter_created_dt = min(chapter_created_dt, now)
    chapter_updated_dt = min(chapter_updated_dt, now)
    chapter_updated_dt = max(chapter_updated_dt, chapter_created_dt)

    return {
        "viewCount": view_count,
        "isPremium": random.choice([True, False]),
        "created": format_datetime_for_json(chapter_created_dt),
        "updated": format_datetime_for_json(chapter_updated_dt),
    }

def generate_random_genre_dates():
    start_year = 2021
    year = random.randint(start_year, datetime.datetime.now().year - 1 if datetime.datetime.now().year > start_year else start_year)
    month = random.randint(1,12)
    day = random.randint(1,28)
    created_dt = datetime.datetime(year, month, day, random.randint(0,23), random.randint(0,59))

    updated_dt = created_dt + datetime.timedelta(days=random.randint(0,365), hours=random.randint(0,23))

    now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    created_dt = min(created_dt, now)
    updated_dt = min(updated_dt, now)
    updated_dt = max(updated_dt, created_dt)

    return format_datetime_for_json(created_dt), format_datetime_for_json(updated_dt)


def load_state(state_path='data/state.json'):
    """Load crawling state from disk. Returns a dict with keys current_page, stories_crawled_count, processed_novels."""
    try:
        with open(state_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {"current_page": 1, "stories_crawled_count": 0, "processed_novels": {}}


def save_state(state, state_path='data/state.json'):
    """Persist crawling state to disk atomically."""
    import os, tempfile
    os.makedirs(os.path.dirname(state_path) or '.', exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(state_path) or '.')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as tf:
            json.dump(state, tf, ensure_ascii=False, indent=2)
        os.replace(tmp, state_path)
    except Exception:
        try:
            os.remove(tmp)
        except Exception:
            pass

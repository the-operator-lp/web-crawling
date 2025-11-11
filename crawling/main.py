"""
Tiny entry point that orchestrates crawling by using smaller modules.
This file intentionally keeps only the orchestration logic; implementation moved to modules:
 - config.py
 - ids.py
 - utils.py
 - fetcher.py
"""

import json
from urllib.parse import urljoin
from config import BASE_URL, HOT_NOVELS_PATH, MAX_STORIES_TO_CRAWL, MAX_CHAPTERS_TO_SCRAPE_PER_NOVEL
from utils import initialize_json_files, generate_random_genre_dates, create_slug_from_text
from ids import generate_genre_id
from fetcher import get_novel_urls_from_list_page, scrape_novel_details, scrape_chapter_details

# --- DATA STORAGE ---
novels_data = []
chapters_data = []
genres_data = []
existing_genre_names_to_id = {}

def main():
    global novels_data, chapters_data, genres_data, existing_genre_names_to_id

    initialize_json_files()

    stories_crawled_count = 0
    current_page_num = 1

    while stories_crawled_count < MAX_STORIES_TO_CRAWL:
        if current_page_num == 1:
            page_url = urljoin(BASE_URL, HOT_NOVELS_PATH)
        else:
            page_url = urljoin(BASE_URL, f"{HOT_NOVELS_PATH}trang-{current_page_num}/")
        
        print(f"\nFetching novel list from: {page_url}")
        novel_urls_on_page = get_novel_urls_from_list_page(page_url)

        if not novel_urls_on_page:
            print(f"No more novels found on page {current_page_num}. Stopping.")
            break

        for novel_base_url_from_list in novel_urls_on_page:
            if stories_crawled_count >= MAX_STORIES_TO_CRAWL:
                break

            # Ensure novel_base_url_from_list ends with a '/' for consistent urljoin
            novel_base_url = novel_base_url_from_list.rstrip('/') + '/'

            novel_detail = scrape_novel_details(novel_base_url)
            if not novel_detail:
                print(f"Failed to scrape details for novel: {novel_base_url}. Skipping.")
                continue
            
            # Handle Genres
            processed_genre_ids_for_novel = []
            for genre_name in novel_detail.pop('scraped_genre_names', []):
                if not genre_name: continue
                genre_name_clean = genre_name.strip()
                if genre_name_clean not in existing_genre_names_to_id:
                    genre_id_str = generate_genre_id()
                    genre_slug = create_slug_from_text(genre_name_clean)
                    genre_desc = f"{genre_name_clean} {genre_id_str}"
                    created_g, updated_g = generate_random_genre_dates()
                    
                    new_genre = {
                        "genreId": genre_id_str,
                        "name": genre_name_clean,
                        "description": genre_desc,
                        "slug": genre_slug,
                        "isActive": True,
                        "created": created_g,
                        "updated": updated_g,
                        "_class": "com.content.content_service.models.GenreEntity"
                    }
                    genres_data.append(new_genre)
                    existing_genre_names_to_id[genre_name_clean] = genre_id_str
                    processed_genre_ids_for_novel.append(genre_id_str)
                else:
                    processed_genre_ids_for_novel.append(existing_genre_names_to_id[genre_name_clean])
            novel_detail['genreList'] = list(set(processed_genre_ids_for_novel))

            # Scrape Chapters sequentially for this novel
            print(f"Starting sequential chapter scrape for novel '{novel_detail['title']}' up to {MAX_CHAPTERS_TO_SCRAPE_PER_NOVEL} chapters.")
            novel_total_word_count = 0
            chapter_ids_for_this_novel = []
            chapters_scraped_for_this_novel_count = 0

            for chapter_num_to_try in range(1, MAX_CHAPTERS_TO_SCRAPE_PER_NOVEL + 1):
                # Construct chapter URL: e.g., novel_base_url + "chuong-1/"
                # Ensure novel_base_url ends with a slash.
                chapter_url = urljoin(novel_base_url, f"chuong-{chapter_num_to_try}/")
                
                # Pass chapter_num_to_try as chapter_number_expected
                chapter_detail = scrape_chapter_details(chapter_url, novel_detail['novelId'], chapter_num_to_try)
                
                if chapter_detail:
                    chapters_data.append(chapter_detail)
                    chapter_ids_for_this_novel.append(chapter_detail['chapterId'])
                    novel_total_word_count += chapter_detail.get('wordCount', 0)
                    chapters_scraped_for_this_novel_count +=1
                else:
                    # scrape_chapter_details returned None, meaning chapter likely doesn't exist or major error
                    print(f"  Stopping chapter scrape for '{novel_detail['title']}' at chapter {chapter_num_to_try} (URL: {chapter_url}) due to error or chapter not found.")
                    break # Stop trying chapters for this novel
            
            novel_detail['chapterList'] = chapter_ids_for_this_novel
            novel_detail['chapterCount'] = len(chapter_ids_for_this_novel)
            novel_detail['wordCount'] = novel_total_word_count
            
            print(f"  Scraped {chapters_scraped_for_this_novel_count} chapters for novel '{novel_detail['title']}'.")
            
            novels_data.append(novel_detail)
            stories_crawled_count += 1
            print(f"Successfully processed novel {stories_crawled_count}/{MAX_STORIES_TO_CRAWL}: {novel_detail['title']}")

            if stories_crawled_count >= MAX_STORIES_TO_CRAWL:
                break
        
        current_page_num += 1

    with open('novels.json', 'w', encoding='utf-8') as f:
        json.dump(novels_data, f, ensure_ascii=False, indent=2)
    with open('chapters.json', 'w', encoding='utf-8') as f:
        json.dump(chapters_data, f, ensure_ascii=False, indent=2)
    with open('genres.json', 'w', encoding='utf-8') as f:
        json.dump(genres_data, f, ensure_ascii=False, indent=2)

    print(f"\nCrawling finished. Total novels: {len(novels_data)}, Total chapters: {len(chapters_data)}, Total genres: {len(genres_data)}")

if __name__ == '__main__':
    main()
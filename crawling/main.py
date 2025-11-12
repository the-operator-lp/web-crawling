import argparse
import json
import logging
import os
from urllib.parse import urljoin
from config import BASE_URL, HOT_NOVELS_PATH, MAX_STORIES_TO_CRAWL, MAX_CHAPTERS_TO_SCRAPE_PER_NOVEL
from utils import initialize_json_files, generate_random_genre_dates, create_slug_from_text, load_state, save_state
from ids import generate_genre_id
from fetcher import get_novel_urls_from_list_page, scrape_novel_details, scrape_chapter_details
from saver import save_novel, get_existing_chapter_max

# --- DATA STORAGE ---
novels_data = []
chapters_data = []
genres_data = []
existing_genre_names_to_id = {}

def main():
    global novels_data, chapters_data, genres_data, existing_genre_names_to_id

    parser = argparse.ArgumentParser(description='Crawl novels and save to data/ folder')
    parser.add_argument('--no-resume', dest='resume', action='store_false', help='Do not resume from previous run; start fresh')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s')

    initialize_json_files()

    # Load or reset state depending on --no-resume
    if not args.resume:
        state = {"current_page": 1, "stories_crawled_count": 0, "processed_novels": {}}
        save_state(state)
    state = load_state()
    current_page_num = state.get('current_page', 1)
    stories_crawled_count = state.get('stories_crawled_count', 0)
    processed_novels = state.get('processed_novels', {})

    while stories_crawled_count < MAX_STORIES_TO_CRAWL:
        if current_page_num == 1:
            page_url = urljoin(BASE_URL, HOT_NOVELS_PATH)
        else:
            page_url = urljoin(BASE_URL, f"{HOT_NOVELS_PATH}trang-{current_page_num}/")
        
        logging.getLogger(__name__).info("\nFetching novel list from: %s", page_url)
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
                logging.getLogger(__name__).warning("Failed to scrape details for novel: %s. Skipping.", novel_base_url)
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

            # decide folder name early so we can detect existing progress
            folder_name = create_slug_from_text(novel_detail.get('title') or novel_detail.get('slug') or novel_detail['novelId'])
            novel_dir = os.path.join('data', folder_name)

            # If already completed, skip
            processed_info = processed_novels.get(folder_name, {})
            if processed_info.get('completed'):
                logging.getLogger(__name__).info("Skipping already completed novel: %s (%s)", novel_detail.get('title'), folder_name)
                continue

            # Scrape Chapters sequentially for this novel (resume-aware)
            start_chapter = get_existing_chapter_max(novel_dir) + 1
            if start_chapter > MAX_CHAPTERS_TO_SCRAPE_PER_NOVEL:
                logging.getLogger(__name__).info("Novel folder already has max chapters (%d). Marking completed.", start_chapter-1)
                processed_novels[folder_name] = {"last_chapter": start_chapter-1, "completed": True}
                state['processed_novels'] = processed_novels
                save_state(state)
                continue

            logging.getLogger(__name__).info("Starting sequential chapter scrape for novel '%s' from chapter %d up to %d.", novel_detail['title'], start_chapter, MAX_CHAPTERS_TO_SCRAPE_PER_NOVEL)
            novel_total_word_count = 0
            chapter_ids_for_this_novel = []
            chapters_scraped_for_this_novel_count = 0
            chapters_for_this_novel = []
            for chapter_num_to_try in range(start_chapter, MAX_CHAPTERS_TO_SCRAPE_PER_NOVEL + 1):
                # Construct chapter URL: e.g., novel_base_url + "chuong-1/"
                # Ensure novel_base_url ends with a slash.
                chapter_url = urljoin(novel_base_url, f"chuong-{chapter_num_to_try}/")
                
                # Pass chapter_num_to_try as chapter_number_expected
                chapter_detail = scrape_chapter_details(chapter_url, novel_detail['novelId'], chapter_num_to_try)
                
                if chapter_detail:
                    chapters_data.append(chapter_detail)
                    chapters_for_this_novel.append(chapter_detail)
                    chapter_ids_for_this_novel.append(chapter_detail['chapterId'])
                    novel_total_word_count += chapter_detail.get('wordCount', 0)
                    chapters_scraped_for_this_novel_count +=1
                else:
                    # scrape_chapter_details returned None, meaning chapter likely doesn't exist or major error
                    logging.getLogger(__name__).info("  Stopping chapter scrape for '%s' at chapter %d (URL: %s) due to error or chapter not found.", novel_detail['title'], chapter_num_to_try, chapter_url)
                    break # Stop trying chapters for this novel

                # Persist partial progress: save novel (metadata + all chapters collected so far) and update state
                try:
                    save_novel(novel_detail, chapters_for_this_novel, base_dir='data')
                except Exception as e:
                    logging.getLogger(__name__).warning("Failed to save partial novel '%s': %s", novel_detail.get('title'), e)

                processed_novels[folder_name] = {"last_chapter": start_chapter + chapters_scraped_for_this_novel_count - 1, "completed": False}
                state['current_page'] = current_page_num
                state['stories_crawled_count'] = stories_crawled_count
                state['processed_novels'] = processed_novels
                save_state(state)
            
            novel_detail['chapterList'] = chapter_ids_for_this_novel
            novel_detail['chapterCount'] = len(chapter_ids_for_this_novel)
            novel_detail['wordCount'] = novel_total_word_count
            
            logging.getLogger(__name__).info("  Scraped %d chapters for novel '%s'.", chapters_scraped_for_this_novel_count, novel_detail['title'])
            
            # Save novel metadata and chapters to disk (data/<novel-slug>/)
            try:
                novel_dir = save_novel(novel_detail, chapters_for_this_novel, base_dir='data')
            except Exception as e:
                novel_dir = None
                logging.getLogger(__name__).warning("Failed to save novel '%s' to disk: %s", novel_detail.get('title'), e)

            novels_data.append(novel_detail)
            stories_crawled_count += 1
            logging.getLogger(__name__).info("Successfully processed novel %d/%d: %s", stories_crawled_count, MAX_STORIES_TO_CRAWL, novel_detail['title'])
            if novel_dir:
                logging.getLogger(__name__).info("  Saved to: %s", novel_dir)

            if stories_crawled_count >= MAX_STORIES_TO_CRAWL:
                break
        
        current_page_num += 1

    # Persist genres to data/genres.json (others are saved per-novel)
    genres_path = os.path.join('data', 'genres.json')
    with open(genres_path, 'w', encoding='utf-8') as f:
        json.dump(genres_data, f, ensure_ascii=False, indent=2)

    logging.getLogger(__name__).info("\nCrawling finished. Total novels: %d, Total chapters: %d, Total genres: %d", len(novels_data), len(chapters_data), len(genres_data))

if __name__ == '__main__':
    main()
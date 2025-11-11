import requests
from bs4 import BeautifulSoup
import time
import re
from urllib.parse import urljoin

try:
    # Prefer package import when used as module
    from .config import BASE_URL, REQUEST_DELAY, DEFAULT_MISSING_INFO
    from .ids import generate_novel_id, generate_chapter_id
    from .utils import create_slug_from_text, generate_random_novel_numeric_fields, generate_random_chapter_fields
except Exception:
    # Fallback if modules are imported as scripts
    from config import BASE_URL, REQUEST_DELAY, DEFAULT_MISSING_INFO
    from ids import generate_novel_id, generate_chapter_id
    from utils import create_slug_from_text, generate_random_novel_numeric_fields, generate_random_chapter_fields

def fetch_page(url):
    """Fetches and parses a web page."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        time.sleep(REQUEST_DELAY)
        return BeautifulSoup(response.content, 'html.parser')
    except requests.exceptions.RequestException as e:
        print(f"Error fetching {url}: {e}")
        return None

def get_novel_urls_from_list_page(page_url):
    """Extracts novel URLs from a listing page."""
    soup = fetch_page(page_url)
    if not soup:
        return []
    
    novel_links = []
    story_elements = soup.select('div.list-truyen .row div.col-xs-7 > h3.truyen-title > a')
    if not story_elements:
         story_elements = soup.select('h3.truyen-title > a')

    for link_tag in story_elements:
        href = link_tag.get('href')
        if href:
            novel_links.append(urljoin(BASE_URL, href))
    print(f"Found {len(novel_links)} novels on {page_url}")
    return novel_links

def scrape_novel_details(novel_url):
    print(f"Scraping novel details from: {novel_url}")
    soup = fetch_page(novel_url)
    if not soup:
        return None

    novel_data = {}
    title_tag = soup.select_one('h3.title')
    novel_data['title'] = title_tag.get_text(strip=True) if title_tag else DEFAULT_MISSING_INFO

    cover_art_tag = soup.select_one('div.book img[itemprop="image"]')
    novel_data['coverArt'] = urljoin(BASE_URL, cover_art_tag['src']) if cover_art_tag and cover_art_tag.get('src') else DEFAULT_MISSING_INFO
    
    author_tag = soup.select_one('div.info a[itemprop="author"]')
    novel_data['scraped_author_name'] = author_tag.get_text(strip=True) if author_tag else DEFAULT_MISSING_INFO

    genre_tags = soup.select('div.info a[itemprop="genre"]')
    novel_data['scraped_genre_names'] = [tag.get_text(strip=True) for tag in genre_tags] if genre_tags else []

    desc_tag = soup.select_one('div.desc-text[itemprop="description"]')
    if not desc_tag:
        desc_tag = soup.select_one('div.desc-text')
    novel_data['description'] = desc_tag.decode_contents() if desc_tag else f"<p>{DEFAULT_MISSING_INFO}</p>"

    source_element = soup.select_one('div.info span.source')
    if source_element:
         novel_data['source'] = source_element.get_text(strip=True)
    else:
        source_strong_tag = soup.find('strong', string=re.compile(r'Nguồn:'))
        if source_strong_tag and source_strong_tag.next_sibling:
            novel_data['source'] = source_strong_tag.next_sibling.strip() if isinstance(source_strong_tag.next_sibling, str) else source_strong_tag.find_next('span', class_='source').get_text(strip=True) if source_strong_tag.find_next('span', class_='source') else DEFAULT_MISSING_INFO
        else:
            novel_data['source'] = DEFAULT_MISSING_INFO
            
    status_text_tag = soup.select_one('div.info span.text-success')
    if status_text_tag :
        novel_data['scraped_status'] = status_text_tag.get_text(strip=True)
    else:
        status_strong_tag = soup.find('strong', string=re.compile(r'Trạng thái:'))
        if status_strong_tag and status_strong_tag.next_sibling:
            next_sib = status_strong_tag.next_sibling
            if isinstance(next_sib, str) and next_sib.strip():
                 novel_data['scraped_status'] = next_sib.strip()
            elif next_sib and hasattr(next_sib, 'name') and next_sib.name == 'span':
                 novel_data['scraped_status'] = next_sib.get_text(strip=True)
            else:
                 novel_data['scraped_status'] = DEFAULT_MISSING_INFO
        else:
            novel_data['scraped_status'] = DEFAULT_MISSING_INFO

    novel_data['novelId'] = generate_novel_id()
    novel_data['altTitle'] = create_slug_from_text(novel_data['title'])
    base_novel_slug_from_url = novel_url.rstrip('/').split('/')[-1]
    novel_data['slug'] = base_novel_slug_from_url
    
    novel_data['authorId'] = "ACC0000125"
    novel_data['language'] = "tiếng Việt"
    novel_data['status'] = "completed"
    novel_data['approved'] = True
    novel_data['targetAudience'] = "all"
    novel_data['_class'] = "com.content.content_service.models.NovelEntity"

    novel_data.update(generate_random_novel_numeric_fields())

    novel_data['genreList'] = []
    novel_data['chapterList'] = []
    novel_data['wordCount'] = 0
    novel_data['chapterCount'] = 0

    return novel_data

def scrape_chapter_details(chapter_url, novel_id_str, chapter_number_expected):
    print(f"  Attempting to scrape chapter: {chapter_url}")
    soup = fetch_page(chapter_url)
    if not soup:
        print(f"  Chapter not found or error fetching: {chapter_url}")
        return None

    chapter_data = {}
    chapter_data['novelId'] = novel_id_str
    chapter_data['chapterId'] = generate_chapter_id()

    title_tag = soup.select_one('a.chapter-title')
    raw_chapter_title_from_site = title_tag.get_text(strip=True) if title_tag else f"Chương {chapter_number_expected}"
    number_match = re.search(r'Chương\s*(\d+)', raw_chapter_title_from_site, re.IGNORECASE)
    if number_match:
        chapter_data['chapterNumber'] = int(number_match.group(1))
    else:
        chapter_data['chapterNumber'] = chapter_number_expected
    title_only_match = re.match(r'Chương\s*\d+\s*:\s*(.*)', raw_chapter_title_from_site, re.IGNORECASE)
    if title_only_match:
        final_chapter_title = title_only_match.group(1).strip()
    else:
        final_chapter_title = raw_chapter_title_from_site
    chapter_data['title'] = final_chapter_title

    content_div = soup.select_one('div.chapter-c')
    raw_content_text = ""
    if content_div:
        for unwanted_tag in content_div.find_all(['script', 'style', 'div', 'span'], class_=re.compile(r'(ads|google|display)', re.I)):
            unwanted_tag.decompose()
        
        paragraphs = content_div.find_all('p')
        if paragraphs:
            raw_content_text = "\n".join(p.get_text(separator=" ", strip=True) for p in paragraphs)
        else:
            raw_content_text = content_div.get_text(separator=" ", strip=True)
        
        chapter_data['content'] = content_div.decode_contents()
        if not raw_content_text.strip() and not chapter_data['content'].strip():
             print(f"  Chapter content is empty for: {chapter_url}")
    else:
        print(f"  Chapter content div not found for: {chapter_url}. Assuming chapter does not exist.")
        return None

    word_count = len(raw_content_text.split())

    chapter_data['status'] = "PUBLISHED"
    chapter_data['approved'] = True
    chapter_data['_class'] = "com.content.content_service.models.ChapterEntity"
    
    chapter_data.update(generate_random_chapter_fields())
    chapter_data['wordCount'] = word_count

    print(f"    Successfully scraped Chapter {chapter_data['chapterNumber']}: {chapter_data['title']}")
    return chapter_data

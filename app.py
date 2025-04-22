from flask import Flask, render_template, request
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import time
import re

app = Flask(__name__)

categories = {
    # BBC Sources
    "BBC Politics": "https://www.bbc.com/news/politics",
    "BBC Finance": "https://www.bbc.com/news/business", 
    "BBC Entertainment": "https://www.bbc.com/news/entertainment_and_arts",
    "BBC Sports": "https://www.bbc.com/sport",
    "BBC India": "https://www.bbc.com/news/world/asia/india",

    # The Hindu Sources
    "Hindu National": "https://www.thehindu.com/news/national/",
    "Hindu Business": "https://www.thehindu.com/business/",
    "Hindu Sport": "https://www.thehindu.com/sport/",
    "Hindu Entertainment": "https://www.thehindu.com/entertainment/",
    "Hindu Science": "https://www.thehindu.com/sci-tech/science/",

    # Al Jazeera Sources
    "AlJazeera Middle East": "https://www.aljazeera.com/middle-east/",
    "AlJazeera Asia": "https://www.aljazeera.com/asia/",
    "AlJazeera Economy": "https://www.aljazeera.com/economy/",
    "AlJazeera Sports": "https://www.aljazeera.com/sports/",
    "AlJazeera Features": "https://www.aljazeera.com/features/"
}

def get_source_type(category):
    if category.startswith("BBC"):
        return "bbc"
    elif category.startswith("Hindu"):
        return "hindu"
    elif category.startswith("AlJazeera"):
        return "aljazeera"
    return "unknown"

def get_articles(category_name, max_articles=10, start_date=None, end_date=None):
    if category_name not in categories:
        return f"No such category: {category_name}"

    url = categories[category_name]
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.75 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Referer': 'https://www.google.com/'
    }
    source_type = get_source_type(category_name)

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        time.sleep(1)
        soup = BeautifulSoup(response.text, 'html.parser')

        if source_type == "bbc":
            return scrape_bbc(soup, category_name, url, headers, max_articles, start_date, end_date)
        elif source_type == "hindu":
            return scrape_hindu(soup, url, headers, max_articles, start_date, end_date)
        elif source_type == "aljazeera":
            return scrape_aljazeera(soup, url, headers, max_articles, start_date, end_date)
        else:
            return []
    except Exception as e:
        print(f"Error fetching articles from {category_name}: {str(e)}")
        return []

def scrape_bbc(soup, category_name, base_url, headers, max_articles, start_date, end_date):
    news_list = []
    seen_urls = set()
    articles = soup.select('a[href^="/sport"]' if category_name == "BBC Sports" else 'a[href^="/news"]')

    for article in articles:
        if len(news_list) >= max_articles:
            break

        href = article.get('href')
        if not href or len(href.split('/')) < 3 or "live" in href or "#" in href:
            continue
        link = "https://www.bbc.com" + href
        if link in seen_urls:
            continue
        seen_urls.add(link)

        try:
            article_response = requests.get(link, headers=headers)
            time.sleep(1.5)
            article_soup = BeautifulSoup(article_response.text, 'html.parser')
            headline_tag = article_soup.find('h1') or article_soup.find('h2')
            summary_tag = article_soup.find('p')
            date_tag = article_soup.find('time')

            if date_tag and date_tag.has_attr('datetime'):
                published = date_tag['datetime'][:10]
                published_date = datetime.strptime(published, "%Y-%m-%d").date()
            else:
                continue

            if (start_date and published_date < start_date) or (end_date and published_date > end_date):
                continue

            if headline_tag and summary_tag:
                news_list.append({
                    'headline': headline_tag.get_text(strip=True),
                    'summary': summary_tag.get_text(strip=True),
                    'link': link,
                    'published_date': published,
                    'formatted_date': published_date.strftime("%B %d, %Y"),
                    'source': 'BBC News'
                })
        except Exception as e:
            print(f"Error processing BBC article {link}: {str(e)}")
            continue

    return news_list

def scrape_hindu(soup, base_url, headers, max_articles, start_date, end_date):
    news_list = []
    seen_urls = set()
    
    # Just get all links from the page first
    all_links = soup.find_all('a', href=True)
    article_links = []
    
    # Filter links that likely point to articles
    for link in all_links:
        href = link.get('href', '')
        # Look for article patterns in URLs
        if (href.startswith('https://www.thehindu.com/') or href.startswith('/')) and \
           any(pattern in href for pattern in ['/article', '/news/', '/business/', '/sport/', '/sci-tech/', '/entertainment/']):
            if href.startswith('/'):
                href = 'https://www.thehindu.com' + href
            article_links.append(href)
    
    # Remove duplicates
    article_links = list(set(article_links))
    print(f"Found {len(article_links)} potential Hindu article links")
    
    # Process each article link
    for href in article_links:
        if len(news_list) >= max_articles:
            break
            
        if href in seen_urls:
            continue
            
        seen_urls.add(href)
        
        try:
            print(f"Fetching The Hindu article: {href}")
            res = requests.get(href, headers=headers, timeout=15)
            time.sleep(2)  # Longer delay to avoid rate limiting
            
            if res.status_code != 200:
                print(f"Failed to fetch article, status code: {res.status_code}")
                continue
                
            article_soup = BeautifulSoup(res.text, 'html.parser')
            
            # Try different headline approaches
            headline = None
            # First try common classes
            headline_element = (
                article_soup.find('h1', class_='title') or 
                article_soup.find('h1', class_='article-title') or
                article_soup.find('h1', itemprop='headline') or
                article_soup.find('h1', class_='story-headline') or
                article_soup.find('h1')
            )
            if headline_element:
                headline = headline_element.get_text(strip=True)
            
            # If still no headline, check title tag
            if not headline or not headline.strip():
                title_tag = article_soup.find('title')
                if title_tag:
                    title_text = title_tag.get_text(strip=True)
                    if ' - The Hindu' in title_text:
                        headline = title_text.split(' - The Hindu')[0].strip()
            
            # Try to find summary
            summary = None
            
            # First check meta description
            meta_desc = article_soup.find('meta', attrs={'name': 'description'})
            if meta_desc and 'content' in meta_desc.attrs:
                summary = meta_desc['content']
            
            # If no meta description, try different paragraph selectors
            if not summary:
                for selector in ['.lead-text', '.article-text p', '.article p', 'article p', '.story-content p']:
                    paragraphs = article_soup.select(selector)
                    if paragraphs:
                        # Use the first paragraph that's not too short
                        for p in paragraphs:
                            text = p.get_text(strip=True)
                            if len(text) > 30:  # Skip very short paragraphs
                                summary = text
                                break
                        if summary:
                            break
            
            # If still no summary, use any paragraph
            if not summary:
                paragraphs = article_soup.find_all('p')
                for p in paragraphs:
                    if p.parent and not any(cls in str(p.parent.get('class', '')) for cls in ['footer', 'comment', 'author', 'social']):
                        text = p.get_text(strip=True)
                        if len(text) > 30:
                            summary = text
                            break
            
            # Look for date information
            published_date = None
            
            # Check for structured data first
            script_tags = article_soup.find_all('script', {'type': 'application/ld+json'})
            for script in script_tags:
                if script.string:
                    try:
                        import json
                        data = json.loads(script.string)
                        if isinstance(data, dict):
                            date_str = None
                            # Check for different date fields
                            for field in ['datePublished', 'dateModified', 'publishedDate']:
                                if field in data:
                                    date_str = data[field]
                                    break
                            if date_str:
                                # Handle different date formats
                                if 'T' in date_str:
                                    date_str = date_str.split('T')[0]
                                published_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                                break
                    except:
                        pass
            
            # If not found, try HTML elements
            if not published_date:
                date_patterns = [
                    r'(\w+ \d{1,2}, \d{4})',   # April 15, 2025
                    r'(\d{1,2} \w+ \d{4})',     # 15 April 2025
                    r'(\d{1,2}-\w+-\d{4})',     # 15-Apr-2025
                    r'(\d{2}/\d{2}/\d{4})',     # 15/04/2025
                    r'(\d{4}-\d{2}-\d{2})'      # 2025-04-15
                ]
                
                # Try specific date elements first
                for selector in [
                    '.dateline', '.date-line', '.publish-time', '.update-time', 
                    'time', '[itemprop="datePublished"]', '[itemprop="dateModified"]', 
                    '.article-date', '.storydate', '.story-date-time', '.meta-datetime', '.article__published'
                ]:
                    date_elements = article_soup.select(selector)
                    for element in date_elements:
                        # Check for datetime attribute
                        if element.has_attr('datetime'):
                            datetime_attr = element['datetime']
                            try:
                                if 'T' in datetime_attr:
                                    datetime_attr = datetime_attr.split('T')[0]
                                published_date = datetime.strptime(datetime_attr, "%Y-%m-%d").date()
                                break
                            except:
                                pass
                        
                        # Check text content
                        date_text = element.get_text(strip=True)
                        # Apply each regex pattern
                        for pattern in date_patterns:
                            match = re.search(pattern, date_text)
                            if match:
                                date_str = match.group(1)
                                try:
                                    if '-' in date_str and not date_str[0].isdigit():
                                        # Handle 15-Apr-2025 format
                                        published_date = datetime.strptime(date_str, "%d-%b-%Y").date()
                                    elif '-' in date_str and len(date_str.split('-')[0]) == 4:
                                        # Handle 2025-04-15 format
                                        published_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                                    elif '/' in date_str:
                                        # Handle 15/04/2025 format
                                        published_date = datetime.strptime(date_str, "%d/%m/%Y").date()
                                    elif ',' in date_str:
                                        # Handle April 15, 2025 format
                                        published_date = datetime.strptime(date_str, "%B %d, %Y").date()
                                    else:
                                        # Handle 15 April 2025 format
                                        published_date = datetime.strptime(date_str, "%d %B %Y").date()
                                    break
                                except ValueError:
                                    pass
                        
                        if published_date:
                            break
                    
                    if published_date:
                        break
            
            # If still no date, check the URL for a date pattern
            if not published_date:
                url_date_pattern = r'/(\d{4})/(\d{1,2})/(\d{1,2})/'
                url_match = re.search(url_date_pattern, href)
                if url_match:
                    year, month, day = url_match.groups()
                    try:
                        published_date = datetime(int(year), int(month), int(day)).date()
                    except ValueError:
                        pass
            
            # Use today's date as a last resort
            if not published_date:
                published_date = datetime.today().date()
                print(f"Using today's date for article: {href}")
                
            # Skip if outside date range
            if (start_date and published_date < start_date) or (end_date and published_date > end_date):
                continue

            # Only add the article if we have both headline and summary
            if headline and summary:
                news_list.append({
                    'headline': headline,
                    'summary': summary[:300] + '...' if len(summary) > 300 else summary,
                    'link': href,
                    'published_date': published_date.strftime("%Y-%m-%d"),
                    'formatted_date': published_date.strftime("%B %d, %Y"),
                    'source': 'The Hindu'
                })
        except Exception as e:
            print(f"Error processing The Hindu article {href}: {str(e)}")
            continue

    return news_list

def scrape_aljazeera(soup, base_url, headers, max_articles, start_date, end_date):
    news_list = []
    seen_urls = set()
    
    # Updated selectors for Al Jazeera
    article_containers = soup.select('.gc--type-post, .gc--type-custompost, article, .article-card')
    article_links = []
    
    # First try to find links within containers
    for container in article_containers:
        link_tag = container.find('a')
        if link_tag and link_tag.has_attr('href'):
            article_links.append(link_tag)
    
    # If that didn't work, try a more generic approach
    if not article_links:
        article_links = soup.select('a[href*="/20"], a[href*="/news/"]')
    
    print(f"Found {len(article_links)} Al Jazeera article links")
    
    for tag in article_links:
        if len(news_list) >= max_articles:
            break
            
        href = tag.get('href')
        if not href:
            continue
            
        # Skip non-article links
        if any(skip in href for skip in ['javascript:', '#', 'mailto:', '/tag/', '/author/']):
            continue
            
        # Ensure full URL
        if href.startswith('/'):
            href = 'https://www.aljazeera.com' + href
        elif not href.startswith('http'):
            continue
            
        if href in seen_urls:
            continue
            
        seen_urls.add(href)
        
        try:
            print(f"Fetching Al Jazeera article: {href}")
            res = requests.get(href, headers=headers, timeout=10)
            time.sleep(1.5)
            
            if res.status_code != 200:
                print(f"Failed to fetch article, status code: {res.status_code}")
                continue
                
            article_soup = BeautifulSoup(res.text, 'html.parser')
            
            # Try different headline selectors
            headline = (
                article_soup.find('h1', class_='article__title') or
                article_soup.find('h1', class_='post-title') or
                article_soup.find('h1')
            )
            
            # Try different summary extraction methods
            summary = None
            meta = article_soup.find('meta', attrs={'name': 'description'})
            if meta and 'content' in meta.attrs:
                summary = meta['content']
            else:
                # Try to get first paragraph
                first_para = article_soup.select_one('.article__content p, .article-p, .wysiwyg p')
                if first_para:
                    summary = first_para.get_text(strip=True)
            
            # Look for date in multiple places
            published_date = None
            
            # First try JSON-LD data
            script_tags = article_soup.find_all('script', {'type': 'application/ld+json'})
            for script in script_tags:
                if script.string:
                    try:
                        import json
                        data = json.loads(script.string)
                        if isinstance(data, dict) and 'datePublished' in data:
                            date_str = data['datePublished'].split('T')[0]
                            published_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                            break
                    except:
                        pass
            
            # If not found, try various HTML elements
            if not published_date:
                for date_selector in [
                    'time', '.article-dates', '.date-simple', '.article-date',
                    '[data-testid="article-date"]', '.published-date', '.post-date'
                ]:
                    date_element = article_soup.select_one(date_selector)
                    if date_element:
                        if date_element.has_attr('datetime'):
                            try:
                                date_str = date_element['datetime'].split('T')[0]
                                published_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                                break
                            except:
                                pass
                        
                        date_text = date_element.get_text(strip=True)
                        # Try to extract date with regex
                        date_patterns = [
                            r'(\d{1,2} \w+ \d{4})',  # 15 April 2025
                            r'(\w+ \d{1,2}, \d{4})',  # April 15, 2025
                            r'(\d{4}-\d{2}-\d{2})',   # 2025-04-15
                            r'(\d{2}/\d{2}/\d{4})'    # 15/04/2025
                        ]
                        
                        for pattern in date_patterns:
                            match = re.search(pattern, date_text)
                            if match:
                                date_str = match.group(1)
                                try:
                                    if '-' in date_str:
                                        published_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                                    elif '/' in date_str:
                                        published_date = datetime.strptime(date_str, "%d/%m/%Y").date()
                                    elif ',' in date_str:
                                        published_date = datetime.strptime(date_str, "%B %d, %Y").date()
                                    else:
                                        published_date = datetime.strptime(date_str, "%d %B %Y").date()
                                    break
                                except ValueError:
                                    pass
                        
                        if published_date:
                            break
            
            if not published_date:
                # If no date found, use current date
                published_date = datetime.today().date()
                
            if (start_date and published_date < start_date) or (end_date and published_date > end_date):
                continue

            if headline and summary:
                headline_text = headline.get_text(strip=True)
                if headline_text:  # Ensure headline is not empty
                    news_list.append({
                        'headline': headline_text,
                        'summary': summary[:300] + '...' if len(summary) > 300 else summary,
                        'link': href,
                        'published_date': published_date.strftime("%Y-%m-%d"),
                        'formatted_date': published_date.strftime("%B %d, %Y"),
                        'source': 'Al Jazeera'
                    })
        except Exception as e:
            print(f"Error processing Al Jazeera article {href}: {str(e)}")
            continue

    return news_list

@app.route('/', methods=['GET', 'POST'])
def index():
    articles = None
    category = None
    start_date = None
    end_date = None
    search_performed = False

    current_utc = "2025-04-22 12:34:01"
    user_login = "Lokesh-172"

    if request.method == 'POST':
        category = request.form.get('category')
        start_date_input = request.form.get('start_date')
        end_date_input = request.form.get('end_date')
        search_performed = True

        try:
            start_date = datetime.strptime(start_date_input, "%Y-%m-%d").date() if start_date_input else None
            end_date = datetime.strptime(end_date_input, "%Y-%m-%d").date() if end_date_input else datetime.today().date()
        except:
            start_date = None
            end_date = datetime.today().date()

        articles = get_articles(category, start_date=start_date, end_date=end_date)

    return render_template('index.html', 
                           articles=articles, 
                           category=category,
                           categories=categories,
                           start_date=start_date, 
                           end_date=end_date,
                           search_performed=search_performed,
                           current_utc=current_utc,
                           user_login=user_login)

if __name__ == '__main__':
    app.run(debug=True)
# # gdelt_search.py
# import requests
# from datetime import datetime, timedelta
# from newspaper import Article
# from sklearn.feature_extraction.text import TfidfVectorizer

# def extract_article_publish_date(url):
#     """Extracts the publish date of an article using newspaper3k"""
#     article = Article(url)
#     article.download()
#     article.parse()
#     return article.publish_date

# def extract_keywords(text, n=5):
#     """Extracts the top n keywords using TF-IDF from the given text"""
#     tfidf = TfidfVectorizer(stop_words="english", max_features=n)
#     tfidf_matrix = tfidf.fit_transform([text])
#     feature_names = tfidf.get_feature_names_out()
#     return feature_names

# def build_gdelt_query(keywords, start_datetime, end_datetime):
#     """Builds the query string for the GDELT API"""
#     query = ' '.join(keywords)
#     query = f"query={query}"
#     query += f"&startdatetime={start_datetime}&enddatetime={end_datetime}"
#     query += "&mode=artlist&maxrecords=25&format=json"
#     return query

# def search_gdelt(query):
#     """Performs a GDELT API search based on the constructed query"""
#     url = "https://api.gdeltproject.org/api/v2/context/context"
#     try:
#         response = requests.get(url, params=query)
#         data = response.json()
#         return data.get('articles', [])
#     except Exception as e:
#         print(f"[!] GDELT search failed: {e}")
#         return []

# def search_articles_with_gdelt(seed_url):
#     """Main function to search articles using GDELT"""
#     # Extract publish date and keywords from the seed article
#     publish_date = extract_article_publish_date(seed_url)
#     if not publish_date:
#         print("[!] Publish date not found for seed article.")
#         return []

#     # Apply 24-hour window
#     end_datetime = publish_date.strftime('%Y%m%d%H%M%S')
#     start_datetime = (publish_date - timedelta(days=1)).strftime('%Y%m%d%H%M%S')

#     # Extract keywords from the article
#     seed_text = extract_article_text(seed_url)
#     keywords = extract_keywords(seed_text, n=5)
#     print(f"[*] Keywords: {keywords}")

#     # Build the GDELT query
#     gdelt_query = build_gdelt_query(keywords, start_datetime, end_datetime)

#     print(f"[*] Searching with GDELT query: {gdelt_query}")
#     results = search_gdelt(gdelt_query)
#     print(f"[+] Found {len(results)} results")
#     return results

# gdelt_search.py
import requests
from datetime import datetime, timedelta
from newspaper import Article
from dateutil import parser
from sklearn.feature_extraction.text import TfidfVectorizer
from bs4 import BeautifulSoup

# Move extract_article_text() logic here
def extract_article_text(url):
    """Extract article text using newspaper3k"""
    try:
        article = Article(url)
        article.download()
        article.parse()
        return article.text
    except Exception as e:
        print(f"[!] Failed to extract from {url}: {e}")
        return None

def extract_article_publish_date(url):
    """Extract the publish date of an article using newspaper3k, BeautifulSoup, and dateutil.parser"""
    article = Article(url)
    article.download()
    article.parse()

    # Try to extract date using newspaper3k
    if article.publish_date:
        return article.publish_date

    # If newspaper3k fails, use BeautifulSoup to try extracting the date from the page
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.text, "html.parser")

        # Search for dates in the text using dateutil.parser and try different formats
        possible_dates = []
        for date_str in soup.find_all(text=True):
            # Remove unnecessary whitespaces and handle specific date format
            date_str = date_str.strip()
            print(f"[DEBUG] Trying to parse date: {date_str}")  # Log the date being processed

            # Try a specific format like 17 May, 2025 18:53
            try:
                parsed_date = datetime.strptime(date_str, "%d %b, %Y %H:%M")
                possible_dates.append(parsed_date)
            except ValueError:
                # Try other common formats
                try:
                    parsed_date = datetime.strptime(date_str, "%d %b, %Y")
                    possible_dates.append(parsed_date)
                except ValueError:
                    try:
                        parsed_date = datetime.strptime(date_str, "%Y-%m-%d")  # ISO format
                        possible_dates.append(parsed_date)
                    except ValueError:
                        try:
                            parsed_date = parser.parse(date_str, fuzzy=True)  # Fallback to fuzzy parser
                            possible_dates.append(parsed_date)
                        except (ValueError, TypeError):
                            continue

        # Return the first valid parsed date found
        if possible_dates:
            return min(possible_dates)  # Return the earliest date if there are multiple
    except Exception as e:
        print(f"[!] Error extracting publish date: {e}")

    return None

def extract_keywords(text, n=5):
    """Extracts the top n keywords using TF-IDF from the given text"""
    tfidf = TfidfVectorizer(stop_words="english", max_features=n)
    tfidf_matrix = tfidf.fit_transform([text])
    feature_names = tfidf.get_feature_names_out()
    return feature_names

def build_gdelt_query(keywords, start_datetime, end_datetime):
    """Builds the query string for the GDELT API"""
    query = ' '.join(keywords)
    query = f"query={query}"
    query += f"&startdatetime={start_datetime}&enddatetime={end_datetime}"
    query += "&mode=artlist&maxrecords=25&format=json"
    return query

def search_gdelt(query):
    """Performs a GDELT API search based on the constructed query"""
    url = "https://api.gdeltproject.org/api/v2/context/context"
    try:
        response = requests.get(url, params=query)
        data = response.json()
        return data.get('articles', [])
    except Exception as e:
        print(f"[!] GDELT search failed: {e}")
        return []

def search_articles_with_gdelt(seed_url):
    """Main function to search articles using GDELT"""
    # Extract publish date and keywords from the seed article
    publish_date = extract_article_publish_date(seed_url)
    if not publish_date:
        print("[!] Publish date not found for seed article.")
        return []

    # Apply 24-hour window
    end_datetime = publish_date.strftime('%Y%m%d%H%M%S')
    start_datetime = (publish_date - timedelta(days=1)).strftime('%Y%m%d%H%M%S')

    # Extract keywords from the article
    seed_text = extract_article_text(seed_url)
    keywords = extract_keywords(seed_text, n=5)
    print(f"[*] Keywords: {keywords}")

    # Build the GDELT query
    gdelt_query = build_gdelt_query(keywords, start_datetime, end_datetime)

    print(f"[*] Searching with GDELT query: {gdelt_query}")
    results = search_gdelt(gdelt_query)
    print(f"[+] Found {len(results)} results")
    return results

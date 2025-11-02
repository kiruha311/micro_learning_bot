import requests
from bs4 import BeautifulSoup

def get_random_wiki_article():
    url = 'https://ru.wikipedia.org/wiki/Special:Random'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        title = soup.find('h1', id='firstHeading').text.strip() if soup.find('h1', id='firstHeading') else 'Неизвестная статья'
        first_paragraph = soup.find('p')
        content = first_paragraph.text.strip()[:500] + '...' if first_paragraph else 'Нет описания.'
        article_url = response.url
        
        return {
            'title': title,
            'url': article_url,
            'summary': content
        }
    except Exception as e:
        return {
            'title': 'Ошибка загрузки статьи',
            'url': '',
            'summary': f'Не удалось получить статью: {str(e)}. Попробуй позже или проверь интернет.'
        }
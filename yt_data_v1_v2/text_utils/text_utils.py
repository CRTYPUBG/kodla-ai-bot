import re
from bs4 import BeautifulSoup
import requests

def clean_text(text: str) -> str:
    """HTML ve linkleri temizle"""
    text = re.sub(r'http\S+', '', text)
    return BeautifulSoup(text, "html.parser").get_text().strip()

def fetch_text_from_url(url: str) -> str:
    """URL’den sayfa metnini çek"""
    try:
        res = requests.get(url, timeout=5)
        return clean_text(res.text)
    except:
        return ""

def extract_text_from_message(content: str) -> str:
    """Mesaj içinde link varsa çek, yoksa direkt temizle"""
    urls = re.findall(r'http[s]?://\S+', content)
    full_text = content
    for url in urls:
        full_text += "\n" + fetch_text_from_url(url)
    return clean_text(full_text)

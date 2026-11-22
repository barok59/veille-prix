import feedparser
from urllib.parse import quote

def chercher(mot_cle: str):
    url = f"https://www.dealabs.com/rss/search?q={quote(mot_cle)}"
    flux = feedparser.parse(url)
    return [{"titre": e.title, "lien": e.link} for e in flux.entries[:10]]

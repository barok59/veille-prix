import requests
import feedparser

HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                         "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"}

def chercher(mot_cle: str):
    r = requests.get("https://www.dealabs.com/rss/search",
                     params={"q": mot_cle}, headers=HEADERS, timeout=20)
    print(f"[dealabs] '{mot_cle}' -> HTTP {r.status_code}, "
          f"{len(r.content)} octets, type={r.headers.get('content-type')}")
    flux = feedparser.parse(r.content)
    print(f"[dealabs]   {len(flux.entries)} résultat(s)")
    return [{"titre": e.title, "lien": e.link} for e in flux.entries[:10]]

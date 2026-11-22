import json
import re
import requests
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                         "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
           "Accept-Language": "fr-FR,fr;q=0.9"}

def _offres(data):
    if isinstance(data, list):
        for x in data:
            yield from _offres(x)
    elif isinstance(data, dict):
        if "offers" in data:
            o = data["offers"]
            yield from (o if isinstance(o, list) else [o])
        for v in data.values():
            if isinstance(v, (dict, list)):
                yield from _offres(v)

def lire_prix(url: str):
    r = requests.get(url, headers=HEADERS, timeout=25)
    print(f"[prix] {url[:70]}... -> HTTP {r.status_code}, {len(r.content)} octets")
    if r.status_code != 200:
        return None
    soup = BeautifulSoup(r.text, "html.parser")
    for s in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(s.string or "")
        except Exception:
            continue
        for o in _offres(data):
            if isinstance(o, dict) and o.get("price"):
                print(f"[prix]   JSON-LD : {o.get('price')} {o.get('priceCurrency')}")
                return float(str(o["price"]).replace(",", "."))
    m = soup.find("meta", property="product:price:amount")
    if m and m.get("content"):
        print(f"[prix]   meta : {m['content']}")
        return float(m["content"].replace(",", "."))
    print("[prix]   aucun prix trouvé dans la page")
    return None

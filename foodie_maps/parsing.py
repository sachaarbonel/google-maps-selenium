"""Parse rendered place panels. Keep unlabelled descriptions out of AI fields."""
import hashlib
import re
from urllib.parse import parse_qs, unquote, urlsplit, urlunsplit
from bs4 import BeautifulSoup

AI_LABEL = re.compile(
    r"AI[- ](?:generated|powered)|generated (?:by|with) (?:Google )?AI|"
    r"summari[sz]ed (?:by|with) (?:(?:Google )?AI|Gemini)|AI (?:overview|summary)|"
    r"(?:généré|générée|générés|générées|résumé|résumés|synthèse).{0,30}"
    r"(?:\bIA\b|intelligence artificielle)|résumé (?:des avis )?par (?:l[’']?)?IA",
    re.I,
)


def clean(text):
    return re.sub(r"\s+", " ", text or "").strip()


def canonical_url(url):
    parts = urlsplit(url)
    # Coordinates and place data in the path must be preserved.
    params = parse_qs(parts.query)
    identity = [(key, params[key][0]) for key in ("cid", "ftid", "query_place_id") if key in params]
    from urllib.parse import urlencode
    return urlunsplit((parts.scheme or "https", parts.netloc, parts.path, urlencode(identity), ""))


def place_key(url):
    decoded = unquote(url)
    match = re.search(r"!1s(0x[0-9a-f]+:0x[0-9a-f]+)", decoded, re.I)
    if match:
        return "cid:" + str(int(match.group(1).split(":")[1], 16))
    query = parse_qs(urlsplit(url).query)
    if query.get("cid"):
        return "cid:" + query["cid"][0]
    if query.get("query_place_id"):
        return "place:" + query["query_place_id"][0]
    match = re.search(r"!1s([^!/?]+)", decoded)
    if match:
        return "place:" + match.group(1)
    return "url:" + hashlib.sha256(canonical_url(url).encode()).hexdigest()[:24]


def number(text, decimal=False):
    text = clean(text).replace("\u202f", " ").replace("\xa0", " ")
    pattern = r"\d+(?:[.,]\d+)?" if decimal else r"\d[\d\s.,]*"
    match = re.search(pattern, text)
    if not match:
        return None
    raw = match.group().strip()
    return float(raw.replace(",", ".")) if decimal else int(re.sub(r"\D", "", raw))


def summaries(soup):
    found = []
    # Only locally bounded containers with an explicit AI disclosure qualify.
    # Generic 'Review summary' and editorial descriptions are deliberately excluded.
    for leaf in soup.find_all(["span", "div", "p", "h2", "h3", "button"]):
        if leaf.find_parent(attrs={"data-review-id": True}):
            continue
        label = clean(leaf.get_text(" ", strip=True))
        if len(label) > 180 or not AI_LABEL.search(label):
            continue
        if any(AI_LABEL.search(clean(child.get_text(" ", strip=True))) for child in leaf.find_all(recursive=False)):
            continue
        container = leaf
        for _ in range(4):
            if container.parent is None:
                break
            container = container.parent
            if container.name in ("body", "html") or container.get("role") == "main":
                break
            if container.select('h1, [data-item-id="address"], [data-review-id], [role="feed"]'):
                break
            text = clean(container.get_text(" ", strip=True))
            if 40 <= len(text) <= 2500 and len(text) > len(label) + 25:
                links = [{"text": clean(a.get_text(" ", strip=True)), "url": a["href"]}
                         for a in container.select('a[href^="https://"]')]
                found.append({"text": text, "disclosure": label, "links": links})
                break
    unique = {item["text"]: item for item in found}
    return list(unique.values())


def parse_place(html, url, language):
    soup = BeautifulSoup(html, "html.parser")
    for hidden in list(soup.select('[hidden], [aria-hidden="true"], script, style')):
        hidden.decompose()
    main = soup.select_one('[role="main"]') or soup
    title = main.select_one("h1.DUwDvf, h1")
    if not title or not clean(title.get_text()) or clean(title.get_text()).lower() in {"google maps", "results", "résultats"}:
        raise ValueError("No place title found; page may be blocked or Maps markup changed")

    def text(selector):
        node = main.select_one(selector)
        return clean(node.get_text(" ", strip=True)) if node else None

    def labelled(selector, prefixes):
        node = main.select_one(selector)
        if not node:
            return None
        raw = node.get("aria-label") or node.get_text(" ", strip=True)
        return clean(re.sub(prefixes, "", raw, flags=re.I)) or None

    address = labelled('[data-item-id="address"]', r"^(?:Address|Adresse)\s*:\s*")
    postal = re.search(r"\b(750(?:0[1-9]|1[0-9]|20)|75116)\b", address or "")
    rating = None
    for node in main.select('[role="img"][aria-label]'):
        label = node.get("aria-label", "")
        if re.search(r"stars?|étoiles?", label, re.I):
            rating = number(label, decimal=True)
            if rating is not None and 0 <= rating <= 5:
                break
            rating = None
    count = None
    for node in main.select('button[aria-label], button[jsaction*="reviewChart"]'):
        label = node.get("aria-label", "") or node.get_text()
        if re.search(r"[\d\s.,]+\s*(?:reviews?|avis)\b", label, re.I):
            count = number(label)
            break
    if count is None:
        count = number(text('.F7nice span[aria-label*="avis"], .F7nice span[aria-label*="reviews"]'))
    coords = re.search(r"!3d(-?[\d.]+)!4d(-?[\d.]+)", url)
    website = main.select_one('a[data-item-id="authority"]')
    ai = summaries(main)
    panel_text = clean(main.get_text(" ", strip=True)).lower()
    limited = any(label in panel_text for label in ("affichage limité de google", "limited view of google"))
    description = text('.PYvSYb, .WeS02d .fontBodyMedium')
    if description and AI_LABEL.search(description):
        description = None
    return {
        "place_id": place_key(url), "name": clean(title.get_text()),
        "maps_url": canonical_url(url), "address": address,
        "postal_code": postal.group(1) if postal else None,
        "arrondissement": (16 if postal.group(1) == "75116" else int(postal.group(1)[-2:])) if postal else None,
        "in_paris": bool(postal), "category": text('button[jsaction*="category"]'),
        "rating": rating, "review_count": count,
        "price_range": text('[aria-label*="Price"], [aria-label*="Prix"]'),
        "phone": labelled('[data-item-id^="phone:tel:"]', r"^(?:Phone(?: number)?|Téléphone|Numéro de téléphone)\s*:\s*"),
        "website": website.get("href") if website else None,
        "latitude": float(coords.group(1)) if coords else None,
        "longitude": float(coords.group(2)) if coords else None,
        "description": description, "ai_summaries": ai,
        "ai_summary_status": "found" if ai else ("unavailable_limited_view" if limited else "not_observed"),
        "page_status": "limited_view" if limited else "place_loaded",
        "language": language, "source": "google_maps",
    }

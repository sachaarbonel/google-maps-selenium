from pathlib import Path
import pytest
from foodie_maps.parsing import parse_place, place_key, number

HTML = (Path(__file__).parent / "fixtures/place_fr.html").read_text()
URL = "https://www.google.com/maps/place/Example/data=!4m2!3m1!1s0x123:0xabc!3d48.85!4d2.38?hl=fr"


def test_french_place_and_ai_provenance():
    place = parse_place(HTML, URL, "fr")
    assert place["rating"] == 4.7
    assert place["review_count"] == 1234
    assert place["arrondissement"] == 11
    assert place["in_paris"] is True
    assert place["latitude"] == 48.85
    assert place["phone"] == "+33 1 23 45 67 89"
    assert place["ai_summary_status"] == "found"
    summary, = place["ai_summaries"]
    assert "croissants au beurre" in summary["text"]
    assert summary["disclosure"] == "Résumé généré par l'IA"
    assert summary["links"][0]["url"] == "https://www.google.com/maps/reviews"
    assert "Boulangerie de quartier" not in summary["text"]


def test_unlabelled_review_and_editorial_summaries_are_not_ai():
    place = parse_place(HTML.replace("Résumé généré par l'IA", "Résumé des avis"), URL, "fr")
    assert place["ai_summaries"] == []
    assert place["ai_summary_status"] == "not_observed"
    assert place["description"].startswith("Boulangerie de quartier")


def test_global_ai_disclaimer_does_not_capture_place_panel():
    html = '<div role="main"><h1>Example</h1><p>AI-generated</p><p>About this place</p><button data-item-id="address">Address: 75011 Paris</button></div>'
    assert parse_place(html, URL, "en")["ai_summaries"] == []


def test_same_place_dedupes_locale_viewport_and_cid_links():
    assert place_key(URL) == place_key(URL.replace("hl=fr", "hl=en"))
    assert place_key(URL) == place_key("https://www.google.com/maps?cid=2748")
    assert place_key(URL) != place_key(URL.replace("0xabc", "0xabd"))


@pytest.mark.parametrize("address,expected", [("75116 Paris",16), ("75020 Paris",20), ("92100 Boulogne",None), ("",None)])
def test_postcode_scope(address, expected):
    html = f'<div role="main"><h1>Example</h1><button data-item-id="address">{address}</button></div>'
    place = parse_place(html, URL, "fr")
    assert place["arrondissement"] == expected
    assert place["in_paris"] == (expected is not None)


def test_missing_fields_are_null_and_invalid_pages_fail():
    place = parse_place('<h1>Unrated bakery</h1>', URL, "en")
    assert place["rating"] is None
    assert place["review_count"] is None
    with pytest.raises(ValueError):
        parse_place('<h1>Google Maps</h1>', URL, "en")


@pytest.mark.parametrize("text,expected", [("1,234 reviews",1234), ("1.234 avis",1234), ("1 234 avis",1234), ("0 avis",0)])
def test_review_counts(text, expected):
    assert number(text) == expected


def test_live_limited_view_is_distinguished_from_missing_summary():
    html = '<div role="main"><h1>Example</h1><button data-item-id="phone:tel:+33123456789" aria-label="Numéro de téléphone: +33 1 23 45 67 89"></button><p>Vous voyez un affichage limité de Google Maps.</p></div>'
    place = parse_place(html, URL, "fr")
    assert place["ai_summary_status"] == "unavailable_limited_view"
    assert place["page_status"] == "limited_view"
    assert place["review_count"] is None
    assert place["phone"] == "+33 1 23 45 67 89"


def test_english_ai_summary():
    html = '<div role="main"><h1>Example</h1><section><p>Summarized with Gemini</p><p>Reviewers enjoy fresh bread and flaky pastries with coffee every morning.</p></section></div>'
    assert parse_place(html, URL, "en")["ai_summary_status"] == "found"


def test_hidden_content_and_reviewer_ai_mentions_are_not_summaries():
    html = '''<div role="main"><h1>Example</h1>
    <section hidden><p>AI-generated</p><p>This should never be included as a visible summary.</p></section>
    <div data-review-id="123"><span>AI-generated decorations</span><p>I did not like the AI-generated decorations inside this bakery.</p></div>
    </div>'''
    assert parse_place(html, URL, "en")["ai_summaries"] == []

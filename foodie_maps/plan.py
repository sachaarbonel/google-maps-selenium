"""Explicit, inspectable search coverage; discovery does not imply a census."""
from dataclasses import asdict, dataclass
from urllib.parse import urlencode

CATEGORIES = {
    "restaurants": "restaurants", "bakeries": "boulangeries artisanales",
    "pastries": "pâtisseries", "cafes": "cafés coffee shops",
    "bistros": "bistrots", "brasseries": "brasseries restaurants",
    "fine-dining": "restaurants gastronomiques", "street-food": "street food",
    "brunch": "brunch", "vegetarian": "restaurants végétariens",
    "vegan": "restaurants vegan", "creperies": "crêperies",
    "pizzerias": "pizzerias", "ice-cream": "glaciers artisanaux",
    "chocolate": "chocolatiers", "cheese": "fromageries",
    "delis": "épiceries fines traiteurs", "markets": "marchés alimentaires",
    "wine-bars": "bars à vin avec restauration", "seafood": "restaurants fruits de mer",
    "butchers": "boucheries charcuteries", "fishmongers": "poissonneries",
    "tea": "salons de thé", "food-halls": "halles gourmandes food court",
}

@dataclass(frozen=True)
class Search:
    category: str
    arrondissement: int
    query: str
    url: str

    def to_dict(self):
        return asdict(self)


def make_plan(categories=None, arrondissements=None, language="fr"):
    for district in (arrondissements or range(1, 21)):
        if not 1 <= district <= 20:
            raise ValueError("Paris arrondissements must be between 1 and 20")
        for category in (categories or CATEGORIES):
            query = f"{CATEGORIES[category]} Paris {75000 + district} France"
            yield Search(category, district, query, "https://www.google.com/maps/search/?" +
                         urlencode({"api": "1", "query": query, "hl": language}))

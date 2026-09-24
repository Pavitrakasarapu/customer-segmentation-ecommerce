import urllib.request
import urllib.parse
import json
import time
import os
import concurrent.futures
from pathlib import Path

SCRATCH_DIR = Path(__file__).resolve().parent
OUTPUT_FILE = SCRATCH_DIR / "catalog_images.json"

SUBCATS_QUERIES = {
    # WOMEN (6 subcategories)
    ("WOMEN", "Dresses"): [
        "women dress", "evening gown", "cocktail dress", "summer dress women", "maxi dress",
        "floral dress women", "party dress women", "vintage dress women", "prom dress", "sundress",
        "red dress women", "white dress women", "black dress women", "silk dress women", "chiffon dress"
    ],
    ("WOMEN", "Tops"): [
        "women blouse", "women top", "crop top women", "tunic women", "ruffle top women",
        "sleeveless top women", "chiffon blouse women", "silk top women", "camisole women", "lace top women",
        "peplum top", "wrap top women", "off shoulder top", "button blouse women", "linen top women"
    ],
    ("WOMEN", "Kurtis"): [
        "kurti", "kurta women", "anarkali dress", "salwar suit", "chikankari kurti",
        "cotton kurti", "printed kurti", "embroidered kurti", "georgette kurti", "rayon kurti",
        "angrakha kurti", "straight kurti", "a-line kurti", "long kurti", "designer kurti"
    ],
    ("WOMEN", "Jeans"): [
        "women jeans", "skinny jeans women", "denim pants women", "high rise jeans",
        "blue jeans women", "bootcut jeans women", "flare jeans women", "distressed jeans women",
        "mom jeans women", "wide leg jeans women", "black jeans women", "cropped jeans women",
        "denim trousers women", "ripped jeans women"
    ],
    ("WOMEN", "Sarees"): [
        "saree", "sari", "silk saree", "banarasi saree", "kanjeevaram saree",
        "chanderi saree", "indian saree", "chiffon saree", "georgette saree", "linen saree",
        "printed saree", "embroidered saree", "organza saree", "wedding saree", "handloom saree",
        "mysore silk saree", "paithani saree", "tussar saree"
    ],
    ("WOMEN", "Ethnic Wear"): [
        "lehenga choli", "lehenga", "ghagra choli", "sherwani women", "salwar kameez wedding",
        "sharara suit", "gharara", "anarkali suit women", "palazzo suit ethnic", "designer lehenga",
        "bridal lehenga", "dupatta ethnic", "festive suit women", "ethnic jacket women", "indian wedding attire"
    ],

    # MEN (5 subcategories)
    ("MEN", "Shirts"): [
        "men dress shirt", "men casual shirt", "oxford shirt men", "button down shirt men",
        "men formal shirt", "flannel shirt men", "plaid shirt men", "linen shirt men",
        "white shirt men", "blue shirt men", "striped shirt men", "hawaiian shirt men",
        "chambray shirt men", "collar shirt men"
    ],
    ("MEN", "T-Shirts"): [
        "men t-shirt", "men tee shirt", "crewneck t-shirt men", "polo shirt men",
        "v-neck t-shirt men", "graphic tee men", "black t-shirt men", "white t-shirt men",
        "sports t-shirt men", "cotton t-shirt men", "striped t-shirt men", "henley shirt men",
        "round neck t-shirt"
    ],
    ("MEN", "Jeans"): [
        "men jeans", "men denim trousers", "blue jeans men", "slim fit jeans men",
        "straight leg jeans men", "black jeans men", "tapered jeans men", "ripped jeans men",
        "denim pants men", "dark wash jeans men", "stonewash jeans men", "regular fit jeans men"
    ],
    ("MEN", "Trousers"): [
        "men chinos", "men trousers", "khaki trousers men", "formal pants men",
        "suit trousers men", "dress pants men", "cargo pants men", "linen trousers men",
        "pleated trousers men", "slack pants men", "wool trousers men", "smart casual trousers men"
    ],
    ("MEN", "Jackets"): [
        "men jacket", "leather jacket men", "denim jacket men", "blazer men",
        "bomber jacket men", "winter jacket men", "suit jacket men", "windbreaker men",
        "parka men", "trench coat men", "sports jacket men", "wool coat men", "puffer jacket men"
    ],

    # CHILDREN (6 subcategories)
    ("CHILDREN", "Girls Dresses"): [
        "girl dress", "little girl frock", "girl party dress", "princess dress girl",
        "toddler dress", "flower girl dress", "summer dress girl", "pink dress girl",
        "tulle dress girl", "cotton frock girl", "birthday dress girl", "lace frock girl"
    ],
    ("CHILDREN", "Boys Dresses"): [
        "boy suit", "toddler suit", "boy formal wear", "boy tuxedo",
        "boy blazer outfit", "boy waistcoat", "little boy suit", "page boy suit",
        "boy party dress", "boy formal shirt trousers", "baby boy suit"
    ],
    ("CHILDREN", "Kids Shirts"): [
        "boy shirt", "kids shirt", "toddler shirt", "children shirt",
        "kid cotton shirt", "plaid shirt kid", "checkered shirt boy", "boy polo shirt",
        "summer shirt kid", "linen shirt boy", "striped shirt child"
    ],
    ("CHILDREN", "Kids Jeans"): [
        "kids jeans", "children jeans", "toddler denim", "kids denim pants",
        "boy jeans", "girl jeans", "elastic waist jeans kid", "blue jeans child",
        "denim trousers kid", "dungaree kid", "kids overalls denim"
    ],
    ("CHILDREN", "Footwear"): [
        "sneakers", "leather shoes", "running shoes", "sandals",
        "boots footwear", "athletic shoes", "kids shoes", "toddler shoes",
        "canvas shoes", "loafers footwear", "casual shoes", "dress shoes"
    ],
    ("CHILDREN", "Toys"): [
        "wooden toy", "teddy bear", "lego model", "diecast toy car",
        "building blocks toy", "puzzle board game", "doll toy", "plush toy",
        "rc car toy", "educational toy", "action figure toy", "musical toy", "toy robot"
    ],

    # BEAUTY (8 subcategories)
    ("BEAUTY", "Creams"): [
        "face cream cosmetic", "cold cream", "day cream cosmetic", "night cream jar",
        "skin cream jar", "anti aging cream", "moisturizing cream jar", "retinol cream",
        "eye cream tube", "whitening cream cosmetic", "herbal skin cream jar"
    ],
    ("BEAUTY", "Face Wash"): [
        "face wash bottle", "facial cleanser tube", "skin cleanser cosmetic", "foaming cleanser",
        "cleansing gel", "acne face wash", "tea tree face wash", "clay cleanser",
        "exfoliating face wash", "gentle cleanser", "facial wash pump"
    ],
    ("BEAUTY", "Moisturizer"): [
        "face moisturizer", "facial moisturizing lotion", "hydrating moisturizer", "skin moisturizer cream",
        "ceramide moisturizer", "hyaluronic moisturizer", "gel moisturizer", "daily moisturizer",
        "oil free moisturizer", "aloe moisturizer", "calming moisturizer"
    ],
    ("BEAUTY", "Sunscreen"): [
        "sunscreen bottle", "sunblock cream", "sun lotion tube", "spf sunscreen cosmetic",
        "sun protection lotion", "matte sunscreen", "mineral sunscreen", "gel sunscreen",
        "water resistant sunscreen", "uv sunscreen", "sun care tube"
    ],
    ("BEAUTY", "Serum"): [
        "face serum bottle", "cosmetic dropper serum", "hyaluronic serum", "skincare serum bottle",
        "facial oil dropper", "vitamin c serum", "niacinamide serum", "retinol serum",
        "peptide serum", "glow serum bottle", "skin essence dropper"
    ],
    ("BEAUTY", "Body Lotion"): [
        "body lotion bottle", "body milk lotion", "moisturizing body lotion", "body butter cosmetic",
        "shea butter lotion", "cocoa butter lotion", "aloe body lotion", "body moisturizing pump",
        "nourishing body lotion", "skin lotion bottle", "scented body lotion"
    ],
    ("BEAUTY", "Lip Care"): [
        "lipstick cosmetic", "lip balm tube", "lip gloss cosmetic", "lip balm stick",
        "matte lipstick tube", "tinted lip balm", "lip oil cosmetic", "liquid lipstick",
        "lip scrub cosmetic", "berry lipstick", "red lipstick tube"
    ],
    ("BEAUTY", "Skincare"): [
        "skincare product bottle", "facial toner bottle", "cosmetic mask", "exfoliating scrub tube",
        "micellar water bottle", "clay face mask", "rosewater toner", "face mist spray",
        "sheet mask cosmetic", "skincare cosmetic set", "botanical skincare bottle"
    ]
}

BAD_KEYWORDS = [
    "icon", "logo", "flag", "map", "diagram", "chart", "symbol", "sign",
    "stamp", "coin", "currency", "emblem", "coat_of_arms", "svg", "seal"
]


def fetch_query(query):
    url = f"https://commons.wikimedia.org/w/api.php?action=query&generator=search&gsrsearch={urllib.parse.quote(query)}&gsrnamespace=6&gsrlimit=50&prop=imageinfo&iiprop=url&iiurlwidth=500&format=json"
    req = urllib.request.Request(url, headers={"User-Agent": "CustomerCatalogBot/1.0 (contact@customersegment.local)"})
    results = []
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            pages = data.get("query", {}).get("pages", {})
            for p in pages.values():
                title = p.get("title", "").lower()
                if any(bad in title for bad in BAD_KEYWORDS):
                    continue
                if "imageinfo" in p and p["imageinfo"]:
                    thumb = p["imageinfo"][0].get("thumburl", "")
                    clean_thumb = thumb.split("?")[0] if thumb else ""
                    if any(clean_thumb.lower().endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".webp"]):
                        results.append(clean_thumb)
    except Exception:
        pass
    return results


def main():
    print("Collecting high-quality images across 25 subcategories (target >= 115 distinct per subcategory)...")
    category_images = {}

    for (cat, subcat), queries in SUBCATS_QUERIES.items():
        key = f"{cat}::{subcat}"
        all_candidates = []
        seen = set()

        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
            future_to_q = {executor.submit(fetch_query, q): q for q in queries}
            for fut in concurrent.futures.as_completed(future_to_q):
                urls = fut.result()
                for u in urls:
                    if u not in seen:
                        seen.add(u)
                        all_candidates.append(u)

        selected = all_candidates[:125]
        category_images[key] = selected
        print(f"[{cat} -> {subcat}]: Collected {len(selected)} distinct images (from {len(all_candidates)} candidates)")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(category_images, f, indent=2)

    print(f"\nALL 25 SUBCATEGORIES HARVESTED! Saved to {OUTPUT_FILE}")
    total = sum(len(v) for v in category_images.values())
    print(f"Total distinct images across catalog: {total}")


if __name__ == "__main__":
    main()

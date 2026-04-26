import os, json, re
from groq import Groq

# ─────────────────────────────────────────────────────────────────────────────
# DREAMSTIME CATEGORY MAP & CONSTANTS (Unchanged mappings)
# ─────────────────────────────────────────────────────────────────────────────
VALID_CATEGORIES = {
    112: "Abstract -> Backgrounds",       39: "Abstract -> Blurs",
    164: "Abstract -> Colors",            40: "Abstract -> Competition",
    42:  "Abstract -> Danger",            43: "Abstract -> Exploration",
    45:  "Abstract -> Luxury",           187: "Abstract -> Mobile",
    47:  "Abstract -> Power",             48: "Abstract -> Purity",
    49:  "Abstract -> Security",          51: "Abstract -> Stress",
    52:  "Abstract -> Success",           53: "Abstract -> Teamwork",
    141: "Abstract -> Textures",          54: "Abstract -> Unique",
    79:  "Business -> Communications",    78: "Business -> Computers",
    80:  "Business -> Finance",           77: "Business -> Industries",
    83:  "Business -> Metaphors",         84: "Business -> Objects",
    76:  "Business -> Teams",            210: "IT & C -> Artificial Intelligence",
    110: "IT & C -> Connectivity",       113: "IT & C -> Equipment",
    111: "IT & C -> Internet",           109: "IT & C -> Networking",
    105: "Technology -> Computers",      106: "Technology -> Connections",
    129: "Technology -> Electronics",    209: "Technology -> Science",
    104: "Technology -> Telecommunications",
    89:  "Industries -> Architecture",    87: "Industries -> Banking",
    94:  "Industries -> Communications",  91: "Industries -> Computers",
    90:  "Industries -> Construction",    99: "Industries -> Environment",
    92:  "Industries -> Healthcare & Medical",
    100: "Industries -> Manufacturing",   97: "Industries -> Power and energy",
    199: "Web Design Graphics -> Web Backgrounds & Textures",
}

STYLE_CATEGORY_MAP = {
    "tech_network":         (210, 110),
    "luxury_gold":          (45,  87),
    "finance_power":        (80,  52),
    "vibrant_gradient":     (164, 199),
    "healthcare_science":   (92,  209),
    "architecture_geo":     (89,  141),
    "energy_explosive":     (47,  97),
    "dark_neon":            (45,  112),
    "organic_texture":      (141, 164),
    "minimal_geometric":    (112, 54),
    "sustainability_green": (99,  97),
    "chrome_mechanical":    (100, 113),
    "royal_purple":         (45,  52),
    "warm_earth":           (141, 48),
    "ice_glass":            (39,  112),
}

STYLE_KEYWORD_SEEDS = {
    "tech_network":         ["glowing nodes", "fiber optic", "circuit board", "data stream", "blue glow"],
    "luxury_gold":          ["polished gold", "metallic sheen", "black marble", "gold texture", "reflective"],
    "finance_power":        ["brushed steel", "ascending bars", "navy blue", "chrome surface", "corporate form"],
    "vibrant_gradient":     ["fluid swirl", "color gradient", "vivid colors", "smooth transition", "iridescent"],
    "healthcare_science":   ["molecular structure", "crystalline lattice", "aqua teal", "frosted glass", "clean white"],
    "architecture_geo":     ["concrete texture", "angular shadow", "brutalist form", "raw concrete", "rust orange"],
    "energy_explosive":     ["radial burst", "plasma arc", "fiery orange", "motion trail", "electric discharge"],
    "dark_neon":            ["neon magenta", "matte black", "grid lines", "edge glow", "neon accent"],
    "organic_texture":      ["mineral banding", "terracotta", "stone texture", "slate gray", "oxidized copper"],
    "sustainability_green": ["clean energy", "lime green", "glass refraction", "forest green", "circular topology"],
    "chrome_mechanical":    ["mirror chrome", "gear teeth", "brushed steel", "precision machined", "industrial"],
    "royal_purple":         ["amethyst purple", "rose gold accent", "velvet texture", "violet hue", "iridescent foil"],
    "warm_earth":           ["terracotta layers", "blush pink", "burnt sienna", "ceramic glaze", "trowel marks"],
    "ice_glass":            ["shattered glass", "ice crystal", "refraction", "frosted sphere", "cold white"],
    "minimal_geometric":    ["negative space", "soft shadow", "Bauhaus", "geometric form", "muted palette"],
}

BANNED_KEYWORDS = {
    "boardroom", "meeting", "presentation", "office", "living", "vacation",
    "holiday", "travel", "lifestyle", "workspace", "workplace", "conference",
    "seminar", "webinar", "workshop", "training", "consulting", "strategy",
    "solution", "service", "platform", "product", "brand", "marketing",
    "advertising", "campaign", "startup", "entrepreneur", "ceo", "executive",
    "team", "staff", "employee", "manager", "director", "investor",
}

def clean_keywords(raw_keywords, style_key=None):
    seeds   = STYLE_KEYWORD_SEEDS.get(style_key, [])
    cleaned = set()
    for kw in raw_keywords:
        if not isinstance(kw, str):
            continue
        for sub in kw.split(","):
            k     = sub.strip().lower()
            words = k.split()
            if not words or len(words) > 3:
                continue
            if any(w in BANNED_KEYWORDS for w in words):
                continue
            if all(w.isdigit() for w in words):
                continue
            cleaned.add(k)

    for seed in seeds:
        cleaned.add(seed.lower())

    cleaned_list = list(cleaned)
    padding = [
        "abstract", "background", "design", "modern", "professional",
        "commercial", "artistic", "decorative", "pattern", "texture",
        "creative", "studio", "render", "digital art", "illustration"
    ]
    for p in padding:
        if len(cleaned_list) >= 48:
            break
        if p not in cleaned_list:
            cleaned_list.append(p)
            
    return cleaned_list[:50]

def score_metadata_revenue_potential(title, keywords, category_id):
    score = 0
    tlen = len(title)
    if 55 <= tlen <= 79:   score += 25
    elif 45 <= tlen < 55:  score += 15
    else:                  score += 5
    kcount = len(keywords)
    if kcount >= 47:   score += 25
    elif kcount >= 40: score += 18
    elif kcount >= 30: score += 10
    else:              score += 3

    longtail = sum(1 for k in keywords if len(k.split()) >= 2)
    score += min(20, longtail * 2)

    high_value = {210, 110, 106, 78, 80, 45, 92, 89, 164, 199, 100, 209}
    score += 20 if category_id in high_value else 8
    return min(100, score)

def generate_prompt_and_metadata(niche, style, palette, global_keywords, style_key=None):
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    cat1_default, cat2_default = STYLE_CATEGORY_MAP.get(style_key, (112, 210))
    seeds          = STYLE_KEYWORD_SEEDS.get(style_key, [])
    category_str   = "\n".join([f"{k}: {v}" for k, v in VALID_CATEGORIES.items()])

    prompt = f"""
You are a commercial stock photography director.
Your task: write the visual_prompt and metadata for one image.

IMAGE SPEC:
- Niche        : {niche}
- Visual style : {style}
- Color palette: {palette}

DREAMSTIME CATEGORIES:
{category_str}

Return ONLY a valid JSON object:
{{
    "visual_prompt": "Describe EXACTLY what you would see in the finished image. 3-5 sentences of pure visual description.",
    "metadata": {{
        "title": "Must be 55-79 characters total. Start with a strong VISUAL noun. NO commas.",
        "description": "3 sentences ONLY describing visuals and aesthetic. Total: 150-300 characters.",
        "keywords": [
            "1. ONLY include words that describe something VISUALLY PRESENT in the image.",
            "2. NO use-case words.",
            "3. Include all these visual seeds: {seeds}",
            "4. Provide EXACTLY 45 keywords as an array of strings."
        ],
        "category_id": {cat1_default},
        "category_id_2": {cat2_default}
    }}
}}
"""
    try:
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
        )
        data = json.loads(completion.choices[0].message.content)
    except Exception as e:
        print(f"  Metadata LLM failed: {e}. Using safe defaults.")
        data = {
            "visual_prompt": f"Abstract {style} composition featuring {palette} tones.",
            "metadata": {
                "title": f"Abstract {niche.title()} {style} Commercial Background",
                "description": f"Abstract geometric forms rendered in {palette} tones. Suitable for digital marketing.",
                "keywords": seeds + ["abstract", "background", "geometric", "render"],
                "category_id": cat1_default,
                "category_id_2": cat2_default,
            }
        }

    meta = data.get("metadata", {})

    raw_kws = meta.get("keywords", [])
    if isinstance(raw_kws, str):
        raw_kws = raw_kws.split(",")
    raw_kws = [k for k in raw_kws if isinstance(k, str) and len(k) < 60 and "RULE" not in k]
    meta["keywords"] = clean_keywords(raw_kws, style_key=style_key)

    title = meta.get("title", f"Abstract {style} Commercial Background Design").replace(",", "").strip()
    if len(title) > 79: title = title[:79].rsplit(" ", 1)[0]
    meta["title"] = title[:79]

    # Prepend AI description correctly
    desc = meta.get("description", "Premium abstract commercial background.")
    desc = desc.replace("(AI Generated)", "").strip()
    if not desc.lower().startswith("ai-generated"):
        # Make sure the first letter of original desc is lowercased if needed
        desc = "AI-generated abstract " + desc[0].lower() + desc[1:]
    meta["description"] = desc[:1500]

    for field, fallback in [("category_id", cat1_default), ("category_id_2", cat2_default)]:
        v = meta.get(field)
        if isinstance(v, list): v = v[0] if v else fallback
        try: v = int(v)
        except: v = fallback
        meta[field] = v if v in VALID_CATEGORIES else fallback

    meta["revenue_score"] = score_metadata_revenue_potential(meta["title"], meta["keywords"], meta["category_id"])
    return data.get("visual_prompt", "Abstract commercial background."), meta
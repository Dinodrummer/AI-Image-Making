import os, json, re
from groq import Groq

# ─────────────────────────────────────────────────────────────────────────────
# DREAMSTIME CATEGORY MAP
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

# ─────────────────────────────────────────────────────────────────────────────
# STYLE → CATEGORY MAPPING
# ─────────────────────────────────────────────────────────────────────────────
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

# ─────────────────────────────────────────────────────────────────────────────
# STYLE-SPECIFIC VISUAL KEYWORD SEEDS
# These are VISUAL descriptors — what a reviewer/buyer would actually see.
# ─────────────────────────────────────────────────────────────────────────────
STYLE_KEYWORD_SEEDS = {
    "tech_network":         ["glowing nodes", "fiber optic", "circuit board", "data stream",
                             "blue glow", "network mesh", "digital grid", "luminous strands",
                             "holographic", "dark background"],
    "luxury_gold":          ["polished gold", "gold surface", "metallic sheen", "black marble",
                             "spotlight", "gold texture", "reflective", "geometric form",
                             "macro detail", "champagne tone"],
    "finance_power":        ["brushed steel", "ascending bars", "navy blue", "chrome surface",
                             "upward composition", "hard shadow", "geometric structure",
                             "white background", "metallic bars", "corporate form"],
    "vibrant_gradient":     ["fluid swirl", "color gradient", "paint pour", "vivid colors",
                             "coral pink", "electric violet", "smooth transition",
                             "iridescent", "diagonal composition", "color field"],
    "healthcare_science":   ["molecular structure", "crystalline lattice", "aqua teal",
                             "white background", "clinical lighting", "transparent sphere",
                             "hexagonal pattern", "frosted glass", "helix form", "clean white"],
    "architecture_geo":     ["concrete texture", "angular shadow", "geometric void",
                             "brutalist form", "raking light", "raw concrete", "rectangular",
                             "warm gray", "sand beige", "rust orange"],
    "energy_explosive":     ["radial burst", "plasma arc", "fiery orange", "crimson glow",
                             "motion trail", "energy core", "white hot", "dark void",
                             "radial blur", "electric discharge"],
    "dark_neon":            ["neon magenta", "matte black", "grid lines", "vanishing point",
                             "edge glow", "indigo background", "geometric shard",
                             "atmospheric haze", "neon accent", "purple violet"],
    "organic_texture":      ["agate cross section", "mineral banding", "terracotta",
                             "stone texture", "geode interior", "terrazzo", "slate gray",
                             "oxidized copper", "teal mineral", "macro texture"],
    "sustainability_green": ["hexagonal array", "green glow", "clean energy", "lime green",
                             "glass refraction", "silver connector", "forest green",
                             "white background", "isometric view", "circular topology"],
    "chrome_mechanical":    ["mirror chrome", "gear teeth", "brushed steel", "platinum",
                             "precision machined", "reflective surface", "black background",
                             "turbine section", "industrial", "concentric rings"],
    "royal_purple":         ["amethyst purple", "rose gold accent", "velvet texture",
                             "crystal facet", "matte black", "gem surface", "violet hue",
                             "iridescent foil", "beauty lighting", "geometric line"],
    "warm_earth":           ["terracotta layers", "blush pink", "burnt sienna", "kraft texture",
                             "linen cream", "strata pattern", "ceramic glaze", "crackle texture",
                             "warm light", "trowel marks"],
    "ice_glass":            ["shattered glass", "ice crystal", "refraction", "clear prism",
                             "navy shadow", "backlit", "frosted sphere", "caustic light",
                             "crystalline", "cold white"],
    "minimal_geometric":    ["single shape", "negative space", "sage green circle",
                             "off white background", "soft shadow", "Bauhaus", "Swiss design",
                             "dusty rose", "geometric form", "muted palette"],
    "finance_power":        ["brushed steel", "ascending bars", "navy blue", "chrome",
                             "upward arrows", "hard shadow", "geometric structure",
                             "white background", "metallic", "corporate form"],
}

# Keywords that should NEVER appear — use-case words, not visual words
BANNED_KEYWORDS = {
    "boardroom", "meeting", "presentation", "office", "living", "vacation",
    "holiday", "travel", "lifestyle", "workspace", "workplace", "conference",
    "seminar", "webinar", "workshop", "training", "consulting", "strategy",
    "solution", "service", "platform", "product", "brand", "marketing",
    "advertising", "campaign", "startup", "entrepreneur", "ceo", "executive",
    "team", "staff", "employee", "manager", "director", "investor",
}


def clean_keywords(raw_keywords, style_key=None):
    """
    1. Split, strip, deduplicate
    2. Remove banned use-case words
    3. Enforce max 3 words per keyword
    4. Inject style-specific visual seeds
    5. Target 47–50 total
    """
    seeds   = STYLE_KEYWORD_SEEDS.get(style_key, [])
    cleaned = set()

    for kw in raw_keywords:
        if not isinstance(kw, str):
            continue
        for sub in kw.split(","):
            k     = sub.strip().lower()
            words = k.split()

            # Skip empty, too long (>3 words), or banned
            if not words or len(words) > 3:
                continue
            if any(w in BANNED_KEYWORDS for w in words):
                continue
            # Skip pure numbers
            if all(w.isdigit() for w in words):
                continue

            cleaned.add(k)

    # Always include visual seeds
    for seed in seeds:
        cleaned.add(seed.lower())

    # Also add the style label words as keywords
    cleaned_list = list(cleaned)

    # Pad if under 47 with generic visual/commercial terms
    padding = [
        "abstract", "background", "design", "modern", "professional",
        "commercial", "artistic", "decorative", "pattern", "texture",
        "creative", "studio", "render", "digital art", "illustration",
        "stock photo", "high resolution", "detailed", "vibrant", "elegant",
        "bold", "premium", "clean", "sharp", "macro photography",
    ]
    for p in padding:
        if len(cleaned_list) >= 50:
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

    # Visual specificity bonus — multi-word keywords are more precise
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
You are a commercial stock photography director and Dreamstime SEO expert.
Your task: write the visual_prompt and metadata for one image.

IMAGE SPEC:
- Niche        : {niche}
- Visual style : {style}
- Color palette: {palette}

DREAMSTIME CATEGORIES:
{category_str}

Return ONLY a valid JSON object — no markdown, no preamble:
{{
    "visual_prompt": "Describe EXACTLY what you would see in the finished image. "
                     "Use precise visual language: specific shapes (sphere, helix, arc), "
                     "materials (brushed steel, polished marble, frosted glass), "
                     "lighting (hard overhead spotlight, diffused studio fill, backlit), "
                     "and spatial arrangement (centered, radial, isometric). "
                     "Do NOT describe mood, use-case, or business context here. "
                     "3-5 sentences of pure visual description.",
    "metadata": {{
        "title": "RULE: Must be 55-79 characters total. Start with a strong VISUAL noun "
                 "(e.g. 'Glowing Cyan Data Node Network', 'Polished Gold Geometric Prism'). "
                 "Include the dominant color and main visual element. NO commas. "
                 "Do NOT reuse words from the description first sentence.",
        "description": "3 sentences ONLY. "
                       "Sentence 1: Describe the specific VISUAL ELEMENTS visible (shapes, colors, materials, lighting). "
                       "Sentence 2: Describe the AESTHETIC and MOOD (NOT a repeat of sentence 1 or the title). "
                       "Sentence 3: List 2-3 commercial USE CASES (e.g., presentations, branding, web design). "
                       "End with ' (AI Generated)'. Total: 150-300 characters.",
        "keywords": [
            "CRITICAL RULES FOR KEYWORDS:",
            "1. ONLY include words that describe something VISUALLY PRESENT in the image.",
            "2. NO use-case words: boardroom, meeting, office, vacation, lifestyle, etc.",
            "3. Include colors, shapes, materials, lighting terms, and composition words.",
            "4. Include all these visual seeds: {seeds}",
            "5. Include relevant terms from: {', '.join(global_keywords[:6])}",
            "6. Max 3 words per keyword phrase.",
            "7. Provide EXACTLY 45 keywords as an array of strings."
        ],
        "category_id": {cat1_default},
        "category_id_2": {cat2_default}
    }}
}}

IMPORTANT: category_id and category_id_2 must be raw integers from the list above.
Choose the two that best match the visual style: {style}.
The keywords array must contain EXACTLY 45 plain strings — no commentary, no rules text.
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
            "visual_prompt": (
                f"Abstract {style} composition featuring {palette} tones. "
                "Geometric forms with dramatic studio lighting, deep shadows, "
                "and crisp material surface detail."
            ),
            "metadata": {
                "title":        f"Abstract {niche.title()} {style} Commercial Background",
                "description":  (
                    f"Abstract geometric forms rendered in {palette} tones under dramatic studio lighting. "
                    f"The composition achieves a premium {style} aesthetic with precise visual balance. "
                    "Suitable for digital marketing, brand identity, and editorial design. (AI Generated)"
                ),
                "keywords":     seeds + ["abstract", "background", "geometric", "studio",
                                          "render", "commercial", "design", "modern",
                                          "premium", "professional"],
                "category_id":   cat1_default,
                "category_id_2": cat2_default,
            }
        }

    meta = data.get("metadata", {})

    # ── Keyword cleaning ──────────────────────────────────────────────────────
    raw_kws = meta.get("keywords", [])
    if isinstance(raw_kws, str):
        raw_kws = raw_kws.split(",")
    # Filter out any rule-text strings that sneak through
    raw_kws = [k for k in raw_kws if isinstance(k, str) and len(k) < 60
               and "RULE" not in k and "CRITICAL" not in k and "seed" not in k.lower()]
    meta["keywords"] = clean_keywords(raw_kws, style_key=style_key)

    # ── Title cleanup and length enforcement ──────────────────────────────────
    title = meta.get("title", f"Abstract {style} Commercial Background Design")
    title = title.replace(",", "").strip()
    # Trim to 79 chars at a word boundary
    if len(title) > 79:
        title = title[:79].rsplit(" ", 1)[0]
    # If too short, append style/palette descriptors
    if len(title) < 55:
        additions = [palette.split(",")[0].strip().title(),
                     style.split("/")[0].strip().title(),
                     "Background", "Abstract", "Design"]
        for word in additions:
            if len(title) >= 55:
                break
            if word.lower() not in title.lower():
                title = f"{title} {word}"
    meta["title"] = title[:79]

    # ── Description cleanup ───────────────────────────────────────────────────
    desc = meta.get("description", "Premium abstract commercial background. (AI Generated)")
    if "(AI Generated)" not in desc:
        desc += " (AI Generated)"
    desc = desc.replace(" (AI Generated) (AI Generated)", " (AI Generated)")
    meta["description"] = desc[:1500]

    # ── Category fail-safes ───────────────────────────────────────────────────
    for field, fallback in [("category_id", cat1_default), ("category_id_2", cat2_default)]:
        v = meta.get(field)
        if isinstance(v, list):
            v = v[0] if v else fallback
        try:
            v = int(v)
        except (TypeError, ValueError):
            v = fallback
        meta[field] = v if v in VALID_CATEGORIES else fallback

    # ── Revenue score ─────────────────────────────────────────────────────────
    meta["revenue_score"] = score_metadata_revenue_potential(
        meta["title"], meta["keywords"], meta["category_id"]
    )

    print(f"  Title    : {meta['title']} ({len(meta['title'])} chars)")
    print(f"  Keywords : {len(meta['keywords'])}/50")
    print(f"  Score    : {meta['revenue_score']}/100")

    return data.get("visual_prompt", "Abstract commercial background."), meta

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



BANNED_KEYWORDS = {
    "boardroom", "meeting", "presentation", "office", "living", "vacation",
    "holiday", "travel", "lifestyle", "workspace", "workplace", "conference",
    "seminar", "webinar", "workshop", "training", "consulting", "strategy",
    "solution", "service", "platform", "product", "brand", "marketing",
    "advertising", "campaign", "startup", "entrepreneur", "ceo", "executive",
    "team", "staff", "employee", "manager", "director", "investor",
}

def clean_keywords(raw_keywords):
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

    cleaned_list = list(cleaned)
            
    return cleaned_list[:40]

def score_metadata_revenue_potential(title, keywords, category_id):
    score = 0
    tlen = len(title)
    if 55 <= tlen <= 79:   score += 25
    elif 45 <= tlen < 55:  score += 15
    else:                  score += 5
    kcount = len(keywords)
    if 15 <= kcount <= 35: score += 25
    elif kcount > 35:      score += 15
    elif kcount >= 10:     score += 10
    else:                  score += 3

    longtail = sum(1 for k in keywords if len(k.split()) >= 2)
    score += min(20, longtail * 2)

    high_value = {210, 110, 106, 78, 80, 45, 92, 89, 164, 199, 100, 209}
    score += 20 if category_id in high_value else 8
    return min(100, score)

def generate_prompt_and_metadata(niche, aesthetic_style, palette, global_keywords, niche_type="evergreen", target_buyer="Corporate Designer", aspect_ratio="16:9"):
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    category_str   = "\n".join([f"{k}: {v}" for k, v in VALID_CATEGORIES.items()])

    seasonal_rule = ""
    if niche_type.lower() == "seasonal":
        seasonal_rule = "This is a SEASONAL niche. Include trending temporal keywords (e.g. quarterly, seasonal, holiday, trending)."

    prompt = f"""
You are a commercial stock photography director.
Your task: write the visual_prompt and metadata for one image.

IMAGE SPEC:
- Niche        : {niche}
- Aesthetic    : {aesthetic_style}
- Color palette: {palette}
- Aspect Ratio : {aspect_ratio}
- Target Buyer : {target_buyer}
- Context      : {seasonal_rule}

DREAMSTIME CATEGORIES:
{category_str}

Return ONLY a valid JSON object:
{{
    "visual_prompt": "Describe EXACTLY what you would see in the finished image. Build the prompt dynamically to perfectly embody the requested Aesthetic Style. Make it highly commercial and tailored to the Target Buyer.",
    "metadata": {{
        "title": "A highly specific 5-8 word product label (Title Case). NO commas, NO artistic names. Do not just describe the image, state what kind of background it is for.",
        "description": "3 distinct descriptive sentences (Sentence case). MUST NOT reuse vocabulary from the title. Describe the aesthetics, colors, and layout clearly. TOTAL: 150-300 chars.",
        "keywords": [
            "1. ONLY include real, correctly spelled dictionary words that describe something VISUALLY PRESENT in the image. NO made-up or hybrid words.",
            "2. NO use-case words. NO spammy or irrelevant words.",
            "3. Include global keywords: {', '.join(global_keywords)}",
            "4. Provide EXACTLY 25 keywords as an array of strings.",
            "5. CRITICAL SEO: The first 10 keywords MUST be the most descriptive, high-volume visual nouns in order of importance."
        ],
        "category_id": "Integer ID of the absolute best primary category from the DREAMSTIME list",
        "category_id_2": "Integer ID of the second best category from the DREAMSTIME list"
    }}
}}

STRICT IP AND LEGAL FENCE:
DO NOT include any brand names, trademarked products, real-world locations, recognizable buildings, or names of real artists in the visual_prompt, title, description, or keywords. Stick purely to generic, abstract, or non-trademarked physical descriptions.
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
            "visual_prompt": f"Hyper-realistic {aesthetic_style} commercial photography featuring {palette} tones.",
            "metadata": {
                "title": f"Realistic {niche.title()} Commercial Background",
                "description": f"Hyper-realistic tangible objects rendered in {palette} tones. Suitable for digital marketing.",
                "keywords": ["realistic", "background", "tangible", "commercial"] + global_keywords,
                "category_id": 112,
                "category_id_2": 210,
            }
        }

    meta = data.get("metadata", {})

    raw_kws = meta.get("keywords", [])
    if isinstance(raw_kws, str):
        raw_kws = raw_kws.split(",")
    raw_kws = [k for k in raw_kws if isinstance(k, str) and len(k) < 60 and "RULE" not in k]
    meta["keywords"] = clean_keywords(raw_kws)

    title = meta.get("title", f"Realistic Commercial Background Design").replace(",", "").strip()
    if len(title) > 79: title = title[:79].rsplit(" ", 1)[0]
    meta["title"] = title[:79]

    desc = meta.get("description", "Premium realistic commercial background.")
    meta["description"] = desc.strip()[:1500]

    for field, fallback in [("category_id", 112), ("category_id_2", 210)]:
        v = meta.get(field)
        if isinstance(v, list): v = v[0] if v else fallback
        try: v = int(v)
        except: v = fallback
        meta[field] = v if v in VALID_CATEGORIES else fallback

    meta["revenue_score"] = score_metadata_revenue_potential(meta["title"], meta["keywords"], meta["category_id"])
    return data.get("visual_prompt", "Hyper-realistic commercial background."), meta
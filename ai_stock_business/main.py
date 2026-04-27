import sys, time, random, os, json
from datetime import datetime, timedelta
from groq import Groq
from ddgs import DDGS
from dotenv import load_dotenv
import generator, metadata, uploader
from generator import STYLE_PROFILE_KEYS, STYLE_PROFILES

load_dotenv()

LEDGER_FILE             = "concept_ledger.json"
MAX_IMAGES_PER_CONCEPT  = 15
EXPIRY_DAYS             = 90

WARM_GOLD_FAMILY = {"luxury_gold", "finance_power", "warm_earth", "architecture_geo"}

# ─────────────────────────────────────────────────────────────────────────────
# LEDGER (With 90-day expiry & auto-migration)
# ─────────────────────────────────────────────────────────────────────────────
def load_ledger():
    if os.path.exists(LEDGER_FILE):
        try:
            with open(LEDGER_FILE, "r") as f:
                data = json.load(f)
                
                # Migrate old flat-dict format
                if data and "concepts" not in data:
                    data = {"concepts": data, "styles": {}}
                
                # Migrate old concept integer counts to dict format with timestamps
                current_time = time.time()
                for k, v in list(data.get("concepts", {}).items()):
                    if isinstance(v, int):
                        data["concepts"][k] = {"count": v, "last_used": current_time}
                
                # Expire old concepts
                expired_keys = []
                for k, v in data.get("concepts", {}).items():
                    if (current_time - v.get("last_used", current_time)) > (EXPIRY_DAYS * 86400):
                        expired_keys.append(k)
                for k in expired_keys:
                    del data["concepts"][k]

                return data
        except:
            pass
    return {"concepts": {}, "styles": {}}

def save_ledger(ledger):
    with open(LEDGER_FILE, "w") as f:
        json.dump(ledger, f, indent=4)

def update_ledger(concept, style_key):
    ledger = load_ledger()
    current_time = time.time()
    
    # Update Concept
    concept_data = ledger["concepts"].get(concept, {"count": 0, "last_used": current_time})
    concept_data["count"] += 1
    concept_data["last_used"] = current_time
    ledger["concepts"][concept] = concept_data
    
    # Update Style
    ledger["styles"][style_key] = ledger["styles"].get(style_key, 0) + 1
    
    save_ledger(ledger)

# ─────────────────────────────────────────────────────────────────────────────
# STYLE CYCLER
# ─────────────────────────────────────────────────────────────────────────────
class StyleCycler:
    def __init__(self, target_count: int):
        ledger       = load_ledger()
        style_counts = ledger.get("styles", {})
        sorted_styles = sorted(STYLE_PROFILE_KEYS, key=lambda k: style_counts.get(k, 0))
        self._queue = self._build_round_robin_queue(sorted_styles, target_count)
        self._last  = None
        self._warm_gold_used = 0

    def _build_round_robin_queue(self, sorted_styles, n):
        queue  = []
        styles = list(sorted_styles)
        while len(queue) < n:
            deck = list(styles)
            random.shuffle(deck)
            queue.extend(deck)
        return queue[:n]

    def next(self) -> str:
        MAX_ATTEMPTS = len(STYLE_PROFILE_KEYS) * 2
        for _ in range(MAX_ATTEMPTS):
            if not self._queue:
                deck = list(STYLE_PROFILE_KEYS)
                random.shuffle(deck)
                self._queue = deck
            candidate = self._queue.pop(0)
            if candidate == self._last:
                self._queue.append(candidate)
                continue
            if candidate in WARM_GOLD_FAMILY and self._warm_gold_used >= 1:
                self._queue.append(candidate)
                continue
            if candidate in WARM_GOLD_FAMILY:
                self._warm_gold_used += 1
            self._last = candidate
            return candidate
        fallback = random.choice([k for k in STYLE_PROFILE_KEYS if k != self._last])
        self._last = fallback
        return fallback

# ─────────────────────────────────────────────────────────────────────────────
# TIMING & SEASONAL INTEL
# ─────────────────────────────────────────────────────────────────────────────
def get_day_of_week_impact():
    return {
        0: {"name": "Monday",    "buyer_type": "corporate", "multiplier": 1.10},
        1: {"name": "Tuesday",   "buyer_type": "corporate", "multiplier": 1.15},
        2: {"name": "Wednesday", "buyer_type": "corporate", "multiplier": 1.12},
        3: {"name": "Thursday",  "buyer_type": "corporate", "multiplier": 1.08},
        4: {"name": "Friday",    "buyer_type": "mixed",     "multiplier": 1.00},
        5: {"name": "Saturday",  "buyer_type": "leisure",   "multiplier": 0.90},
        6: {"name": "Sunday",    "buyer_type": "leisure",   "multiplier": 0.85},
    }.get(datetime.now().weekday(), {"name": "Unknown", "buyer_type": "mixed", "multiplier": 1.0})

def get_optimal_upload_timing():
    day   = get_day_of_week_impact()
    week  = (datetime.now().day - 1) // 7 + 1
    score = 0
    if day["buyer_type"] == "corporate": score += 20
    if week <= 2:                         score += 15
    if 9 <= datetime.now().hour <= 11:    score += 10
    return {
        "day_info":       day,
        "week":           week,
        "timing_score":   score,
        "recommendation": "UPLOAD NOW" if score >= 35 else "WAIT for better timing",
    }

def get_seasonal_context():
    # Target themes 6 weeks out
    target_date = datetime.now() + timedelta(weeks=6)
    month = target_date.strftime("%B")
    return f"Designers are currently buying for {month} campaigns. Include relevant upcoming seasonal, holiday, or quarterly business transitions."

def get_dynamic_market_context():
    month = datetime.now().strftime("%B")
    year  = datetime.now().year
    queries = [
        f"best selling stock photography categories {year}",
        f"trending stock image buyer demand {month} {year}",
    ]
    results = []
    print("  Fetching live market data...")
    try:
        with DDGS() as ddgs:
            for q in queries:
                for r in ddgs.text(q, max_results=2):
                    results.append(r.get("body", ""))
                time.sleep(1)
    except Exception as e:
        print(f"  Search warning: {e}. Using general logic.")
        return f"General commercial photography demand for {month} {year}."
    return " ".join(results)[:2000]

# ─────────────────────────────────────────────────────────────────────────────
# MASTER STRATEGY 
# ─────────────────────────────────────────────────────────────────────────────
def get_global_intelligence(live_market_context, target_count, style_queue):
    client  = Groq(api_key=os.getenv("GROQ_API_KEY"))
    month   = datetime.now().strftime("%B")
    ledger  = load_ledger()
    seasonal = get_seasonal_context()

    saturated = [k for k, v in ledger.get("concepts", {}).items()
                 if isinstance(v, dict) and v.get("count", 0) >= MAX_IMAGES_PER_CONCEPT]
    saturated_text = ", ".join(saturated) or "None yet."

    historical = "No historical sales data yet."
    if os.path.exists("market_memory.json"):
        try:
            with open("market_memory.json") as f:
                mem    = json.load(f)
                top_3  = [f"{m['niche']} (${m['revenue']:.2f})" for m in mem[:3]]
                historical = f"BEST SELLERS: {', '.join(top_3)}."
        except:
            pass

    style_assignments = []
    for i, sk in enumerate(style_queue):
        label   = STYLE_PROFILES[sk]["label"]
        palette = STYLE_PROFILES[sk]["palette"].split("—")[0].strip()
        style_assignments.append(f'  Image {i+1}: style="{label}", palette="{palette}"')
    style_assignment_str = "\n".join(style_assignments)

    prompt = f"""
You are a commercial stock photography portfolio strategist.

LIVE MARKET: {live_market_context}
HISTORICAL:  {historical}
SEASONAL FORECAST (6-WEEKS OUT): {seasonal}
SATURATED (DO NOT USE): {saturated_text}

The next batch will contain {target_count} images with these PRE-ASSIGNED visual styles:
{style_assignment_str}

For EACH image slot, generate ONE niche concept that:
  - PERFECTLY MATCHES the assigned style and palette.
  - Is a SPECIFIC COMMERCIAL USE-CASE (e.g., 'Corporate sustainability presentation background', 'Healthcare data encryption layout').
  - Is NOT purely artistic, surreal, or chaotic "art for art's sake".
  - Has a clear TARGET BUYER (e.g., 'Fintech Marketer', 'Eco-friendly Brand Designer').
  - Mixes evergreen business themes with upcoming seasonal trends.
  - Is NOT saturated.

Return ONLY a valid JSON object:
{{
    "niches": [
        {{
            "name": "specific commercial use-case (4-8 words)",
            "target_buyer": "profession of target buyer",
            "visual_directive": "Specific visual styling instruction based on LIVE MARKET trends (e.g., 'Use soft pastel gradients trending for spring', 'Incorporate tech-noir neon as currently demanded')",
            "viability_score": 85,
            "type": "evergreen or seasonal",
            "assigned_style_index": 0
        }}
    ],
    "global_keywords": ["20", "cross-market", "high-volume", "stock", "keywords"]
}}

RULES:
1. Provide exactly {target_count} niches, one per image slot, in order.
2. Distribute across different buyer markets.
"""
    print("  Consulting LLM for style-matched niche strategy...")
    try:
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
        )
        return json.loads(completion.choices[0].message.content)
    except Exception as e:
        print(f"  Strategy LLM failed: {e}. Using safe defaults.")
        return {
            "niches": [{"name": "cybersecurity network background", "target_buyer": "Tech Presentation Designer", "visual_directive": "Focus on glowing nodes and deep blue tech styling", "viability_score": 90, "exclusive_percent": 50, "type": "evergreen", "assigned_style_index": i} for i in range(target_count)],
            "global_keywords": ["abstract", "business", "modern", "professional", "technology", "creative"],
        }

# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────
def main():
    target_count = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    os.makedirs("temp_images", exist_ok=True)
    os.makedirs("Other_Stock_Batches", exist_ok=True)
    #os.makedirs("Shutterstock_Batches", exist_ok=True)

    print(f"\n{'='*65}\n  LAUNCHING DIVERSIFIED PRODUCTION: {target_count} ASSETS\n{'='*65}\n")

    timing = get_optimal_upload_timing()
    print(f"  Upload timing: {timing['day_info']['name']} — {timing['recommendation']}\n")

    cycler      = StyleCycler(target_count)
    style_queue = [cycler.next() for _ in range(target_count)]

    live_context    = get_dynamic_market_context()
    intel           = get_global_intelligence(live_context, target_count, style_queue)
    niches          = intel.get("niches", [])
    global_keywords = intel.get("global_keywords", ["business", "abstract", "modern"])

    while len(niches) < target_count:
        niches.append({
            "name": "abstract commercial background", "viability_score": 75,
            "type": "evergreen", "assigned_style_index": len(niches),
        })

    batch_results  = []
    failed_uploads = []

    for i in range(target_count):
        niche_data  = niches[i] if i < len(niches) else niches[-1]
        style_key   = style_queue[i]
        base_niche  = niche_data.get("name", "abstract commercial background")
        niche_type   = niche_data.get("type", "evergreen")
        target_buyer = niche_data.get("target_buyer", "Corporate Designer")
        excl_thresh  = niche_data.get("exclusive_percent", 40) / 100.0

        print(f"\n  ── IMAGE {i+1}/{target_count} ───────────────────────────────")
        print(f"  Niche    : [{niche_type.upper()}] {base_niche} (For: {target_buyer})")

        max_retries = 2
        for attempt in range(max_retries):
            try:
                trend_directive = niche_data.get("visual_directive", "")
                
                visual_prompt, meta = metadata.generate_prompt_and_metadata(
                    niche=base_niche, style=STYLE_PROFILES[style_key]["label"],
                    palette=STYLE_PROFILES[style_key]["palette"].split("—")[0].strip(),
                    global_keywords=global_keywords, style_key=style_key,
                    niche_type=niche_type,
                    trend_directive=trend_directive,
                    target_buyer=target_buyer
                )

                img_path = generator.generate_and_save(
                    visual_prompt=visual_prompt, ratio_index=i,
                    is_exclusive=False, style_key=style_key,
                    meta_data=meta
                )

                batch_results.append({
                    "path": img_path, "meta": meta,
                    "is_exclusive": False,
                    "niche": base_niche, "style_key": style_key, "timestamp": time.time(),
                })

                update_ledger(base_niche, style_key)
                time.sleep(5)
                break
            except Exception as e:
                print(f"  Pipeline error (attempt {attempt+1}/{max_retries}): {e}")
                time.sleep(10)
                if attempt == max_retries - 1:
                    failed_uploads.append({"keyword": base_niche, "error": str(e)})

    if batch_results:
        print(f"\n  BATCH SUMMARY:")
        uploader.batch_upload_to_dreamstime(batch_results)
    else:
        print("  No assets generated successfully.")

    if failed_uploads:
        print(f"\n  {len(failed_uploads)} failure(s):")
        for f in failed_uploads:
            print(f"    - {f['keyword']}: {f['error']}")

    print(f"\n{'='*65}\n  DONE: {len(batch_results)}/{target_count} assets processed.\n{'='*65}\n")

if __name__ == "__main__":
    main()
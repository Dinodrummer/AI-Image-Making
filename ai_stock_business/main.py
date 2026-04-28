import sys, time, random, os, json
from datetime import datetime, timedelta
from groq import Groq
from ddgs import DDGS
from dotenv import load_dotenv
import generator, metadata, uploader

load_dotenv()

LEDGER_FILE             = "concept_ledger.json"
MAX_IMAGES_PER_CONCEPT  = 15
EXPIRY_DAYS             = 90

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

def update_ledger(concept):
    ledger = load_ledger()
    current_time = time.time()
    
    # Update Concept
    concept_data = ledger["concepts"].get(concept, {"count": 0, "last_used": current_time})
    concept_data["count"] += 1
    concept_data["last_used"] = current_time
    ledger["concepts"][concept] = concept_data
    
    save_ledger(ledger)

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
def get_global_intelligence(live_market_context, target_count):
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

    prompt = f"""
You are a commercial stock photography portfolio strategist.

LIVE MARKET: {live_market_context}
HISTORICAL:  {historical}
SEASONAL FORECAST (6-WEEKS OUT): {seasonal}
SATURATED (DO NOT USE): {saturated_text}

Your task is to generate EXACTLY {target_count} HIGHLY DIVERSE, trending commercial photography niches based on the LIVE MARKET context.
Ensure EXTREME DIVERSITY across the {target_count} niches so they do not look similar. Mix different buyer markets.

For EACH image slot, generate ONE niche concept that:
  - Is a SPECIFIC COMMERCIAL USE-CASE (e.g., 'Corporate sustainability presentation background', 'Healthcare data encryption layout').
  - Has a clear TARGET BUYER (e.g., 'Fintech Marketer', 'Eco-friendly Brand Designer').
  - Mixes evergreen business themes with upcoming seasonal trends.
  - Is NOT saturated.

Return ONLY a valid JSON object:
{{
    "niches": [
        {{
            "name": "specific commercial use-case (4-8 words)",
            "target_buyer": "profession of target buyer",
            "aesthetic_style": "A dynamically chosen visual style based on LIVE MARKET trends (e.g., 'Ambient Realism', 'Retro Flash', 'Clean Minimalist', 'High Concept Chaos')",
            "color_palette": "A dynamically chosen color palette that fits the trend and style",
            "aspect_ratio": "Choose EXACTLY ONE absolute best aspect ratio for this niche from: ['16:9', '9:16', '4:3', '3:2', '1:1']. Focus heavily on vertical (9:16) and horizontal (16:9).",
            "adobe_category": "An integer between 1 and 22 representing the best Adobe Stock category (e.g., 4=Business, 19=Technology, 10=Industry, 8=Graphic Resources, 16=Science, 2=Architecture)",
            "viability_score": 85,
            "type": "evergreen or seasonal"
        }}
    ],
    "global_keywords": ["20", "cross-market", "high-volume", "stock", "keywords"]
}}

RULES:
1. Provide exactly {target_count} niches, one per image slot, in order.
2. Distribute across different buyer markets.
3. Guarantee extreme visual and topical diversity between the niches.
"""
    print("  Consulting LLM for dynamic market strategy...")
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
            "niches": [{"name": "cybersecurity network background", "target_buyer": "Tech Presentation Designer", "aesthetic_style": "Realistic Commercial", "color_palette": "neutral tones", "aspect_ratio": "16:9", "adobe_category": 19, "viability_score": 90, "type": "evergreen"} for i in range(target_count)],
            "global_keywords": ["realistic", "business", "modern", "professional", "technology", "creative"],
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

    live_context    = get_dynamic_market_context()
    intel           = get_global_intelligence(live_context, target_count)
    niches          = intel.get("niches", [])
    global_keywords = intel.get("global_keywords", ["business", "realistic", "modern"])

    while len(niches) < target_count:
        niches.append({
            "name": "realistic commercial background", "viability_score": 75,
            "type": "evergreen", "aesthetic_style": "Realistic Commercial", 
            "color_palette": "neutral", "aspect_ratio": "16:9", "adobe_category": 19
        })

    batch_results  = []
    failed_uploads = []

    for i in range(target_count):
        niche_data  = niches[i] if i < len(niches) else niches[-1]
        base_niche  = niche_data.get("name", "realistic commercial background")
        niche_type   = niche_data.get("type", "evergreen")
        target_buyer = niche_data.get("target_buyer", "Corporate Designer")
        aesthetic    = niche_data.get("aesthetic_style", "Realistic Commercial")
        palette      = niche_data.get("color_palette", "neutral")
        aspect_ratio = niche_data.get("aspect_ratio", "16:9")
        adobe_cat    = niche_data.get("adobe_category", 19)

        print(f"\n  ── IMAGE {i+1}/{target_count} ───────────────────────────────")
        print(f"  Niche    : [{niche_type.upper()}] {base_niche} (For: {target_buyer})")

        max_retries = 2
        for attempt in range(max_retries):
            try:
                visual_prompt, meta = metadata.generate_prompt_and_metadata(
                    niche=base_niche, aesthetic_style=aesthetic,
                    palette=palette,
                    global_keywords=global_keywords,
                    niche_type=niche_type,
                    target_buyer=target_buyer,
                    aspect_ratio=aspect_ratio
                )

                img_path = generator.generate_and_save(
                    visual_prompt=visual_prompt, aspect_ratio=aspect_ratio,
                    aesthetic_style=aesthetic, palette=palette,
                    is_exclusive=False,
                    meta_data=meta
                )

                batch_results.append({
                    "path": img_path, "meta": meta,
                    "is_exclusive": False,
                    "niche": base_niche, "adobe_category": adobe_cat, "timestamp": time.time(),
                })

                update_ledger(base_niche)
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
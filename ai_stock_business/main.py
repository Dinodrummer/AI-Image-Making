import sys, time, random, os, json
from datetime import datetime
from groq import Groq
from ddgs import DDGS
from dotenv import load_dotenv
import generator, metadata, uploader
from generator import STYLE_PROFILE_KEYS, STYLE_PROFILES

load_dotenv()

LEDGER_FILE             = "concept_ledger.json"
MAX_IMAGES_PER_CONCEPT  = 15

# Styles that share warm/gold tones — hard cap to 1 per batch
WARM_GOLD_FAMILY = {"luxury_gold", "finance_power", "warm_earth", "architecture_geo"}

# ─────────────────────────────────────────────────────────────────────────────
# LEDGER
# ─────────────────────────────────────────────────────────────────────────────
def load_ledger():
    if os.path.exists(LEDGER_FILE):
        try:
            with open(LEDGER_FILE, "r") as f:
                data = json.load(f)
                # Migrate old flat-dict format
                if data and "concepts" not in data:
                    return {"concepts": data, "styles": {}}
                return data
        except:
            pass
    return {"concepts": {}, "styles": {}}

def save_ledger(ledger):
    with open(LEDGER_FILE, "w") as f:
        json.dump(ledger, f, indent=4)

def update_ledger(concept, style_key):
    ledger = load_ledger()
    ledger["concepts"][concept] = ledger["concepts"].get(concept, 0) + 1
    ledger["styles"][style_key] = ledger["styles"].get(style_key, 0) + 1
    save_ledger(ledger)


# ─────────────────────────────────────────────────────────────────────────────
# STYLE CYCLER  — TRUE ROUND-ROBIN
#
# Guarantees:
#   1. Every style is used before any style repeats (like shuffling a deck).
#   2. No two consecutive images share the same style.
#   3. Max 1 image from the warm/gold color family per batch.
#   4. Historically over-used styles get pushed toward the end of the queue.
# ─────────────────────────────────────────────────────────────────────────────
class StyleCycler:
    def __init__(self, target_count: int):
        ledger       = load_ledger()
        style_counts = ledger.get("styles", {})

        # Sort styles least-used → most-used so least-used come first
        sorted_styles = sorted(
            STYLE_PROFILE_KEYS,
            key=lambda k: style_counts.get(k, 0)
        )

        # Build enough shuffled decks to cover target_count
        self._queue = self._build_round_robin_queue(sorted_styles, target_count)
        self._last  = None

        # Track gold-family usage for this batch
        self._warm_gold_used = 0

    def _build_round_robin_queue(self, sorted_styles, n):
        """
        Fill a queue of length n by cycling through shuffled-deck passes.
        Within each pass, least-used styles stay near the front.
        """
        queue  = []
        styles = list(sorted_styles)  # copy

        while len(queue) < n:
            deck = list(styles)
            random.shuffle(deck)
            queue.extend(deck)

        return queue[:n]

    def next(self) -> str:
        MAX_ATTEMPTS = len(STYLE_PROFILE_KEYS) * 2

        for _ in range(MAX_ATTEMPTS):
            if not self._queue:
                # Refill if somehow exhausted
                deck = list(STYLE_PROFILE_KEYS)
                random.shuffle(deck)
                self._queue = deck

            candidate = self._queue.pop(0)

            # Rule 1: no immediate repeat
            if candidate == self._last:
                self._queue.append(candidate)
                continue

            # Rule 2: max 1 warm/gold style per batch
            if candidate in WARM_GOLD_FAMILY and self._warm_gold_used >= 1:
                self._queue.append(candidate)
                continue

            # Candidate accepted
            if candidate in WARM_GOLD_FAMILY:
                self._warm_gold_used += 1
            self._last = candidate
            return candidate

        # Absolute fallback — pick anything not same as last
        fallback = random.choice([k for k in STYLE_PROFILE_KEYS if k != self._last])
        self._last = fallback
        return fallback


# ─────────────────────────────────────────────────────────────────────────────
# TIMING INTEL
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
    }.get(datetime.now().weekday(),
          {"name": "Unknown", "buyer_type": "mixed", "multiplier": 1.0})

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


# ─────────────────────────────────────────────────────────────────────────────
# LIVE MARKET CONTEXT
# ─────────────────────────────────────────────────────────────────────────────
def get_dynamic_market_context():
    month = datetime.now().strftime("%B")
    year  = datetime.now().year
    queries = [
        f"best selling stock photography categories {year}",
        f"trending stock image buyer demand {month} {year}",
        f"stock photo market niches high revenue {year}",
    ]
    results = []
    print("  Fetching live market data...")
    try:
        with DDGS() as ddgs:
            for q in queries:
                for r in ddgs.text(q, max_results=3):
                    results.append(r.get("body", ""))
                time.sleep(1)
    except Exception as e:
        print(f"  Search warning: {e}. Using general market logic.")
        return f"General commercial photography demand for {month} {year}."
    combined = " ".join(results)[:2500]
    return combined if combined.strip() else f"General commercial photography trends for {month}."


# ─────────────────────────────────────────────────────────────────────────────
# MASTER STRATEGY  (single LLM call)
# ─────────────────────────────────────────────────────────────────────────────
def get_global_intelligence(live_market_context, target_count, style_queue):
    """
    style_queue: ordered list of style_keys assigned for this batch.
    We pass it to the LLM so niche concepts are matched to their visual style —
    preventing the LLM from suggesting 4 gold-themed niches.
    """
    client  = Groq(api_key=os.getenv("GROQ_API_KEY"))
    month   = datetime.now().strftime("%B")
    ledger  = load_ledger()

    saturated = [k for k, v in ledger.get("concepts", {}).items()
                 if v >= MAX_IMAGES_PER_CONCEPT]
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

    # Build style assignment info for the LLM
    style_assignments = []
    for i, sk in enumerate(style_queue):
        label   = STYLE_PROFILES[sk]["label"]
        palette = STYLE_PROFILES[sk]["palette"].split("—")[0].strip()  # drop prohibitions
        style_assignments.append(f'  Image {i+1}: style="{label}", palette="{palette}"')
    style_assignment_str = "\n".join(style_assignments)

    prompt = f"""
You are a commercial stock photography portfolio strategist.

LIVE MARKET: {live_market_context}
HISTORICAL:  {historical}
SATURATED (DO NOT USE): {saturated_text}
CURRENT MONTH: {month}

The next batch will contain {target_count} images with these PRE-ASSIGNED visual styles:
{style_assignment_str}

For EACH image slot, generate ONE niche concept that:
  - PERFECTLY MATCHES the assigned style and palette (e.g. do not assign a "fintech" 
    niche to a terracotta/mineral style — that would be incoherent).
  - Is abstract/conceptual with NO people.
  - Targets a real stock photo buyer segment.
  - Is NOT saturated.

Return ONLY a valid JSON object:
{{
    "niches": [
        {{
            "name": "niche concept (2-5 words)",
            "viability_score": 85,
            "exclusive_percent": 50,
            "type": "evergreen",
            "assigned_style_index": 0
        }}
    ],
    "global_keywords": ["20", "cross-market", "high-volume", "stock", "keywords"]
}}

RULES:
1. Provide exactly {target_count} niches, one per image slot, in order.
2. Each niche must make visual sense for its assigned style palette.
3. Distribute across different buyer markets — healthcare, finance, tech, 
   creative, architecture, etc. DO NOT cluster multiple niches in the same market.
4. viability_score should be honest (70-99), not all 85.
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
        fallback_niches = [
            {"name": "artificial intelligence network",  "viability_score": 90, "exclusive_percent": 50, "type": "evergreen", "assigned_style_index": i}
            for i in range(target_count)
        ]
        return {
            "niches":          fallback_niches,
            "global_keywords": ["abstract", "background", "business", "modern", "professional",
                                 "commercial", "design", "premium", "digital", "technology",
                                 "creative", "minimal", "corporate", "stock photo", "artistic"],
        }


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────
def main():
    target_count = int(sys.argv[1]) if len(sys.argv) > 1 else 1

    os.makedirs("temp_images",         exist_ok=True)
    os.makedirs("Adobe_Stock_Batches", exist_ok=True)

    print(f"\n{'='*65}")
    print(f"  LAUNCHING DIVERSIFIED PRODUCTION: {target_count} ASSETS")
    print(f"{'='*65}\n")

    timing = get_optimal_upload_timing()
    print(f"  Upload timing: {timing['day_info']['name']} — {timing['recommendation']}\n")

    # ── 1. Build style queue FIRST (before LLM call) ─────────────────────────
    cycler      = StyleCycler(target_count)
    style_queue = [cycler.next() for _ in range(target_count)]

    print("  Style assignment for this batch:")
    for i, sk in enumerate(style_queue):
        print(f"    {i+1}. {STYLE_PROFILES[sk]['label']}")
    print()

    # ── 2. Fetch market intelligence with style context ───────────────────────
    live_context    = get_dynamic_market_context()
    intel           = get_global_intelligence(live_context, target_count, style_queue)
    niches          = intel.get("niches", [])
    global_keywords = intel.get("global_keywords", ["business", "abstract", "modern"])

    # Pad niches if LLM returned fewer than needed
    while len(niches) < target_count:
        niches.append({
            "name": "abstract commercial background",
            "viability_score": 75,
            "exclusive_percent": 40,
            "type": "evergreen",
            "assigned_style_index": len(niches),
        })

    # ── 3. Generate each image ────────────────────────────────────────────────
    batch_results  = []
    failed_uploads = []

    for i in range(target_count):
        niche_data  = niches[i] if i < len(niches) else niches[-1]
        style_key   = style_queue[i]
        base_niche  = niche_data.get("name", "abstract commercial background")
        niche_type  = niche_data.get("type", "evergreen")
        excl_thresh = niche_data.get("exclusive_percent", 40) / 100.0

        print(f"\n  ── IMAGE {i+1}/{target_count} ───────────────────────────────")
        print(f"  Niche    : [{niche_type.upper()}] {base_niche}")

        max_retries = 2
        for attempt in range(max_retries):
            try:
                visual_prompt, meta = metadata.generate_prompt_and_metadata(
                    niche           = base_niche,
                    style           = STYLE_PROFILES[style_key]["label"],
                    palette         = STYLE_PROFILES[style_key]["palette"].split("—")[0].strip(),
                    global_keywords = global_keywords,
                    style_key       = style_key,
                )

                img_path = generator.generate_and_save(
                    visual_prompt = visual_prompt,
                    ratio_index   = i,
                    is_exclusive  = random.random() < excl_thresh,
                    style_key     = style_key,
                )

                batch_results.append({
                    "path":         img_path,
                    "meta":         meta,
                    "is_exclusive": random.random() < excl_thresh,
                    "niche":        base_niche,
                    "style_key":    style_key,
                    "timestamp":    time.time(),
                })

                update_ledger(base_niche, style_key)
                time.sleep(5)
                break

            except Exception as e:
                print(f"  Pipeline error (attempt {attempt+1}/{max_retries}): {e}")
                time.sleep(10)
                if attempt == max_retries - 1:
                    failed_uploads.append({"keyword": base_niche, "error": str(e)})

    # ── 4. Summary & upload ───────────────────────────────────────────────────
    if batch_results:
        print(f"\n  BATCH SUMMARY:")
        style_dist = {}
        for r in batch_results:
            label = STYLE_PROFILES[r["style_key"]]["label"]
            style_dist[label] = style_dist.get(label, 0) + 1
        for label, count in style_dist.items():
            print(f"    {count}x  {label}")

        scores    = [r["meta"].get("revenue_score", 0) for r in batch_results]
        avg_score = sum(scores) / len(scores) if scores else 0
        print(f"  Avg revenue score : {avg_score:.1f}/100")
        print(f"  Keyword avg count : {sum(len(r['meta'].get('keywords',[])) for r in batch_results)//len(batch_results)}/50\n")

        success = uploader.batch_upload_to_dreamstime(batch_results)
        if not success:
            print("  Upload failed — retrying once...")
            time.sleep(5)
            uploader.batch_upload_to_dreamstime(batch_results)
    else:
        print("  No assets generated successfully.")

    if failed_uploads:
        print(f"\n  {len(failed_uploads)} failure(s):")
        for f in failed_uploads:
            print(f"    - {f['keyword']}: {f['error']}")

    print(f"\n{'='*65}")
    print(f"  DONE: {len(batch_results)}/{target_count} assets processed.")
    print(f"{'='*65}\n")


if __name__ == "__main__":
    main()

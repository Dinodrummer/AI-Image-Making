import sys, time, random, os, json
from datetime import datetime
import pytz
from groq import Groq
from ddgs import DDGS 
from dotenv import load_dotenv
import generator, metadata, uploader

load_dotenv()

def get_current_pst_date():
    pst = pytz.timezone('US/Pacific')
    return datetime.now(pst).strftime("%B %d, %Y")

def get_current_month():
    return datetime.now().strftime("%B")

def get_week_of_month():
    day = datetime.now().day
    return (day - 1) // 7 + 1

def get_day_of_week_impact():
    day = datetime.now().weekday()
    impact_map = {
        0: {"name": "Monday", "buyer_type": "corporate", "multiplier": 1.1},      
        1: {"name": "Tuesday", "buyer_type": "corporate", "multiplier": 1.15},   
        2: {"name": "Wednesday", "buyer_type": "corporate", "multiplier": 1.12},  
        3: {"name": "Thursday", "buyer_type": "corporate", "multiplier": 1.08},   
        4: {"name": "Friday", "buyer_type": "mixed", "multiplier": 1.0},          
        5: {"name": "Saturday", "buyer_type": "leisure", "multiplier": 0.9},      
        6: {"name": "Sunday", "buyer_type": "leisure", "multiplier": 0.85}       
    }
    return impact_map.get(day, {"name": "Unknown", "buyer_type": "mixed", "multiplier": 1.0})

def get_optimal_upload_timing():
    day_info = get_day_of_week_impact()
    week = get_week_of_month()
    timing_score = 0
    if day_info['buyer_type'] == 'corporate': timing_score += 20
    if week <= 2: timing_score += 15  
    if 9 <= datetime.now().hour <= 11: timing_score += 10
    
    return {
        'day_info': day_info,
        'week': week,
        'timing_score': timing_score,
        'recommendation': 'UPLOAD NOW' if timing_score >= 35 else 'WAIT for better timing'
    }

def get_dynamic_market_context():
    current_month = get_current_month()
    current_year = datetime.now().year
    queries = [
        f"major business and tech events {current_month} {current_year}",
        f"trending marketing and design aesthetics {current_month} {current_year}"
    ]
    
    search_context = []
    print(f"Scraping live market intelligence for {current_month} {current_year}...")
    
    try:
        with DDGS() as ddgs:
            for query in queries:
                results = ddgs.text(query, max_results=3)
                for r in results:
                    search_context.append(r.get('body', ''))
                time.sleep(1) 
    except Exception as e:
        print(f"Search API warning: {e}. Falling back to general business logic.")
        return f"General corporate and business trends for {current_month}."

    combined_context = " ".join(search_context)[:2000]
    if not combined_context.strip():
        return f"General corporate and business trends for {current_month}."
        
    return combined_context

def get_master_strategy(live_market_context, target_count):
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    current_month = get_current_month()
    day_info = get_day_of_week_impact()
    
    historical_context = "No historical sales data available yet."
    if os.path.exists("market_memory.json"):
        try:
            with open("market_memory.json", "r") as f:
                memory = json.load(f)
                top_3 = [f"{m['niche']} (${m['revenue']:.2f})" for m in memory[:3]]
                historical_context = f"YOUR ACTUAL ALL-TIME BEST SELLERS: {', '.join(top_3)}. Prioritize generating assets similar to these proven earners."
        except:
            pass

    print(f"Generating Master Strategy from live data and historical memory...")

    prompt = f"""
    You are a stock photography strategist. You must synthesize LIVE market data with the user's HISTORICAL sales data to maximize profit.
    
    LIVE MARKET CONTEXT:
    {live_market_context}
    
    HISTORICAL PERFORMANCE MEMORY:
    {historical_context}
    
    Today is a {day_info['name']}. Buyers are looking for {day_info['buyer_type']} content.
    
    Return ONLY a valid JSON object. Do not include markdown formatting or conversational text.
    Structure the JSON exactly like this:
    {{
        "niches": [
            {{"name": "niche keyword phrase", "viability_score": 85, "exclusive_percent": 60}},
            {{"name": "another specific niche", "viability_score": 92, "exclusive_percent": 80}}
        ]
    }}
    
    Rules:
    1. Provide exactly {max(3, target_count * 2)} niches.
    2. Heavily weight the 'viability_score' toward concepts proven in the HISTORICAL PERFORMANCE MEMORY.
    3. Niches MUST be abstract, business, tech, or design focused. NO faces or humans.
    4. viability_score is 0-100 based on profit potential minus saturation.
    5. exclusive_percent is 20-100 based on how unique the niche is.
    """

    try:
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        return json.loads(completion.choices[0].message.content)
    except Exception as e:
        print(f"Master strategy generation failed: {e}. Using safe defaults.")
        return {
            "niches": [{"name": f"modern {current_month} corporate abstract", "viability_score": 75, "exclusive_percent": 50}]
        }

def main():
    try:
        target_count = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    except: target_count = 1

    if not os.path.exists('temp_images'): os.makedirs('temp_images')
    print(f"--- LAUNCHING OPTIMIZED PRODUCTION: {target_count} ASSETS ---")
    
    timing_intel = get_optimal_upload_timing()
    print(f"Upload timing: {timing_intel['day_info']['name']} - {timing_intel['recommendation']}")
    
    live_context = get_dynamic_market_context()
    strategy = get_master_strategy(live_context, target_count)
    niches = sorted(strategy.get('niches', []), key=lambda x: x.get('viability_score', 0), reverse=True)
    
    global_styles = generator.get_trending_design_styles()
    global_keywords = metadata.get_trending_keywords()
    
    batch_results = []
    failed_uploads = []
    ratio_counter = 0
    
    for niche_data in niches:
        if len(batch_results) >= target_count: break
        
        base_niche = niche_data.get('name', 'abstract corporate')
        viability = niche_data.get('viability_score', 50)
        exclusive_threshold = niche_data.get('exclusive_percent', 40) / 100.0
        
        print(f"Processing ({len(batch_results)+1}/{target_count}): {base_niche} [viability={viability}]")
        
        max_retries = 2
        for attempt in range(max_retries):
            try:
                img_path, dynamic_prompt = generator.generate_and_save(
                    base_niche, 
                    ratio_index=ratio_counter, 
                    is_exclusive=random.random() < exclusive_threshold,
                    global_styles=global_styles
                )
                ratio_counter += 1
                
                # Category demand removed; metadata handles it dynamically now
                meta = metadata.get_image_metadata(dynamic_prompt, global_keywords)
                
                batch_results.append({
                    'path': img_path, 
                    'meta': meta,
                    'is_exclusive': random.random() < exclusive_threshold,
                    'niche': base_niche,
                    'timestamp': time.time()
                })
                
                time.sleep(12) 
                break
                
            except Exception as e:
                error_msg = str(e).lower()
                print(f"Pipeline error (attempt {attempt+1}/{max_retries}): {e}")
                
                if "429" in error_msg or "throttled" in error_msg or "rate limit" in error_msg:
                    print("--> Rate limit hit. Cooling down API for 15 seconds...")
                    time.sleep(15)
                else:
                    time.sleep(2)
                
                if attempt == max_retries - 1:
                    failed_uploads.append({'keyword': base_niche, 'error': str(e)})

    if batch_results:
        upload_success = uploader.batch_upload_to_dreamstime(batch_results)
        if upload_success:
            print(f"--- SUCCESS: {len(batch_results)} assets uploaded ---")
        else:
            print(f"--- WARNING: Upload failed, retrying ---")
            time.sleep(5)
            uploader.batch_upload_to_dreamstime(batch_results)

    if failed_uploads:
        print(f"Notice: {len(failed_uploads)} generations failed or hit hard API limits.")

if __name__ == "__main__":
    main()
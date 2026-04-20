import sys, time, random, os
from dotenv import load_dotenv
from google import genai
from google.genai import types
import generator, metadata, uploader

load_dotenv()

def ai_research_trends(count=2):
    """Gemini performs live research via Google Search grounding."""
    print(f"AI RESEARCH: Analyzing live April 2026 stock photography demand...")
    client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
    
    prompt = (f"Identify {count} highly profitable stock photography keywords "
              "trending in April 2026. Focus on macro sensory textures and "
              "authentic human gestures. Return ONLY the keywords separated by commas.")

    # FIXED: Correct tool instantiation for Gemini 2.5 Flash
    search_tool = types.Tool(google_search=types.GoogleSearch())

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        config=types.GenerateContentConfig(tools=[search_tool]),
        contents=prompt
    )
    
    return [k.strip() for k in response.text.split(",")]

def main():
    try:
        target_count = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    except:
        target_count = 2

    if not os.path.exists('temp_images'): os.makedirs('temp_images')
    print(f"--- LAUNCHING TARGET {target_count} ASSETS ---")
    
    trends = ai_research_trends(count=target_count)
    # FIXED: Initialized as empty list
    batch_results = []
    
    while len(batch_results) < target_count:
        for base in trends:
            if len(batch_results) >= target_count: break
            print(f"Working on ({len(batch_results)+1}/{target_count}): {base}")
            try:
                # Variety flavors avoid repetitiveness seen in Image 1 & 5
                flavor = random.choice(['macro', 'lifestyle', 'detail'])
                variation = f"{flavor} of {base}"
                
                img_path = generator.generate_and_save(variation)
                meta = metadata.get_image_metadata(img_path)
                batch_results.append({'path': img_path, 'meta': meta})
                
                print("Cooling down 15s...")
                time.sleep(15) # Rate limit shield for free tier
            except Exception as e:
                print(f"Pipeline error: {e}")
                time.sleep(60)

    print(f"--- UPLOADING BATCH OF {len(batch_results)} ---")
    uploader.batch_upload_to_dreamstime(batch_results)
    print("--- PROCESS COMPLETE ---")

if __name__ == "__main__":
    main()
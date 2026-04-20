from google import genai
from PIL import Image
import json, os

def get_image_metadata(image_path):
    client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
    img = Image.open(image_path)
    
    prompt = ("Analyze this image. Return ONLY a JSON object: "
              "{\"title\": \"MUST start with 'AI generated' followed by 5W description, no commas\", "
              "\"keywords\": [\"exactly 50 relevance-ordered tags\"], "
              "\"category_id\": 11}")

    response = client.models.generate_content(
        model="gemini-2.5-flash", 
        contents=[prompt, img]
    )
    
    clean_json = response.text.replace('```json', '').replace('```', '').strip()
    data = json.loads(clean_json)
    
    # RUGGEDIZATION: STAY UNDER 80-WORD TOTAL CAP
    if len(data['keywords']) > 50:
        data['keywords'] = data['keywords'][:50]
    
    data['title'] = data['title'].replace(',', '') # Prevent column shifting
    return data
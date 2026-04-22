import replicate, os, requests, time, random
from groq import Groq
from datetime import datetime
from PIL import Image
from io import BytesIO

def get_trending_design_styles():
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    current_month = datetime.now().strftime("%B")
    prompt = (f"What are the TOP 5 design/photography styles trending for commercial stock photography in {current_month} 2026?\n"
              f"Return ONLY a comma-separated list.")
    try:
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}]
        )
        content = completion.choices[0].message.content
        styles = [s.strip() for s in content.split(",") if len(s.strip()) > 5]
        return styles if len(styles) >= 3 else ["modern minimal luxury", "contemporary corporate", "premium abstract"]
    except:
        return ["modern minimal luxury", "contemporary corporate", "premium abstract"]

def get_seasonal_color_palette():
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    month = datetime.now().month
    month_name = datetime.now().strftime("%B")
    
    palettes = {
        1: "cool blues, grays, minimalist whites", 2: "warm reds, pinks, romantic tones",
        3: "fresh greens, pastels, spring colors", 4: "professional neutrals, earth tones",
        5: "bright yellows, ocean blues", 6: "vibrant summer colors, gold accents",
        7: "bold primary colors, creative vibrancy", 8: "professional tones, structured palettes",
        9: "warm oranges, browns, harvest colors", 10: "dark oranges, purples, moody tones",
        11: "warm golds, harvest browns", 12: "festive reds, golds, cool silvers"
    }
    baseline = palettes.get(month, "neutral professional tones")
    
    prompt = (f"It is {month_name} 2026. The traditional stock photography palette is: '{baseline}'.\n"
              f"Based on current commercial design trends, modernize this palette.\n"
              f"Give me a highly specific string (max 15 words). Example: 'moody cyberpunk purples with warm neon orange'.\n"
              f"Return ONLY the palette description.")
    try:
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}]
        )
        enhanced = completion.choices[0].message.content.strip().replace('"', '').replace("'", "")
        return enhanced if len(enhanced) < 150 else baseline
    except:
        return baseline

def determine_aspect_ratio(niche):
    niche_lower = niche.lower()
    if any(x in niche_lower for x in ["social", "phone", "mobile", "portrait", "story"]):
        return "9:16"
    if any(x in niche_lower for x in ["presentation", "background", "desktop", "banner", "landscape"]):
        return "16:9"
    if any(x in niche_lower for x in ["instagram", "icon", "logo", "profile"]):
        return "1:1"
    return random.choice(["16:9", "4:3", "1:1"]) 

def generate_and_save(keyword, ratio_index=0, is_exclusive=False, global_styles=None):
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    
    styles = global_styles if global_styles else ["modern luxury"]
    style = styles[hash(keyword) % len(styles)]
    color_palette = get_seasonal_color_palette()
    
    text_prevention = "Pure visual design. Clean, 100% text-free composition. Do NOT include any text, numbers, labels, report headers, UI overlays, graphs, or typography of any kind."
    
    system_brief = f"Premium stock photography director creating commercial-grade images. Style: {style}. Palette: {color_palette}."
    user_prompt = f"Create a premium {style} commercial concept for: {keyword}. Use {color_palette}. CRITICAL: {text_prevention} NO FACES. NO HUMANS."
    
    completion = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "system", "content": system_brief}, {"role": "user", "content": user_prompt}]
    )
    dynamic_prompt = completion.choices[0].message.content

    unique_seed = int(time.time_ns() % 10000000)
    aspect_ratio = determine_aspect_ratio(keyword)

    output = replicate.run(
        "black-forest-labs/flux-2-pro",
        input={
            "prompt": dynamic_prompt + " (absolutely no text, numbers, or UI elements: 1.5)",
            "aspect_ratio": aspect_ratio,
            "resolution": "1 MP",  
            "seed": unique_seed,
            "output_format": "jpg",
            "safety_tolerance": 3  
        }
    )
    
    img_url = output if isinstance(output, str) else output[0] if isinstance(output, list) else str(output)
    
    print(f"Upscaling image to guarantee Dreamstime 3MP minimum requirement...")
    upscale_output = replicate.run(
        "nightmareai/real-esrgan:42fed1c4974146d4d2414e2be2c5277c7fcf05fcc3a73abf41610695738c1d7b",
        input={
            "image": img_url,
            "scale": 2,
            "face_enhance": False
        }
    )
    
    final_url = upscale_output if isinstance(upscale_output, str) else str(upscale_output)
    
    # NEW: Fetch bytes, strip alpha channels if any, and explicitly save as JPEG
    img_data = requests.get(final_url).content
    image_obj = Image.open(BytesIO(img_data))
    
    # Convert RGBA (PNG) or P (Palette) to standard RGB for JPEG encoding
    if image_obj.mode in ("RGBA", "P"): 
        image_obj = image_obj.convert("RGB")
        
    local_path = f"temp_images/gen_{unique_seed}_{aspect_ratio.replace(':', 'x')}_upscaled.jpg"
    
    # Save with high quality to preserve the upscale fidelity
    image_obj.save(local_path, format="JPEG", quality=95)
    
    return local_path, dynamic_prompt
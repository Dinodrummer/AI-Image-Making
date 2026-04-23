import replicate, os, requests, time, random
from groq import Groq
from datetime import datetime
from PIL import Image
from io import BytesIO

# ── Hard prohibition strings injected into every prompt ───────────────────────
# These appear in both the Groq prompt-writing call AND the final Replicate call.
NO_NATURE = (
    "ABSOLUTELY NO nature scenes, outdoor landscapes, fields, forests, deserts, beaches, "
    "oceans, mountains, rivers, plants, trees, flowers, animals, insects, birds, soil, "
    "rocks, sky, clouds, sunsets, or any organic outdoor environment whatsoever."
)
NO_PEOPLE = "NO faces, NO human figures, NO body parts, NO silhouettes of people."
NO_TEXT   = (
    "Pure visual design. 100% text-free composition. "
    "Do NOT include any text, numbers, labels, UI overlays, graphs, charts, "
    "report headers, or typography of any kind."
)
COMMERCIAL_MANDATE = (
    "This is a STUDIO-QUALITY commercial stock image: abstract, digital, architectural, "
    "or conceptual business imagery only. Think: glowing data networks, geometric "
    "corporate structures, futuristic dashboards (no UI text), metallic surfaces, "
    "gradient light compositions, or bold abstract shapes."
)


def get_trending_design_styles():
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    current_month = datetime.now().strftime("%B")
    prompt = (
        f"What are the TOP 5 design/photography styles trending for commercial stock photography "
        f"in {current_month} 2026?\n"
        f"Focus on abstract, digital, architectural, and corporate aesthetics. "
        f"NO nature or outdoor styles.\n"
        f"Return ONLY a comma-separated list."
    )
    try:
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}]
        )
        content = completion.choices[0].message.content
        styles = [s.strip() for s in content.split(",") if len(s.strip()) > 5]
        return styles if len(styles) >= 3 else [
            "modern minimal luxury", "contemporary corporate", "premium abstract"
        ]
    except Exception:
        return ["modern minimal luxury", "contemporary corporate", "premium abstract"]


def get_seasonal_color_palette():
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    month = datetime.now().month
    month_name = datetime.now().strftime("%B")

    palettes = {
        1:  "cool blues, grays, minimalist whites",
        2:  "warm reds, pinks, romantic tones",
        3:  "fresh greens, pastels, spring colors",
        4:  "professional neutrals, earth tones",
        5:  "bright yellows, ocean blues",
        6:  "vibrant summer colors, gold accents",
        7:  "bold primary colors, creative vibrancy",
        8:  "professional tones, structured palettes",
        9:  "warm oranges, browns, harvest colors",
        10: "dark oranges, purples, moody tones",
        11: "warm golds, harvest browns",
        12: "festive reds, golds, cool silvers",
    }
    baseline = palettes.get(month, "neutral professional tones")

    prompt = (
        f"It is {month_name} 2026. The baseline stock photography palette is: '{baseline}'.\n"
        f"Modernize this palette for abstract/digital/corporate commercial stock images.\n"
        f"Give me a highly specific string (max 15 words). "
        f"Example: 'moody cyberpunk purples with warm neon orange'.\n"
        f"Return ONLY the palette description. No explanation."
    )
    try:
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}]
        )
        enhanced = completion.choices[0].message.content.strip().replace('"', '').replace("'", "")
        return enhanced if len(enhanced) < 150 else baseline
    except Exception:
        return baseline


def determine_aspect_ratio(niche):
    niche_lower = niche.lower()
    if any(x in niche_lower for x in ["social", "phone", "mobile", "portrait", "story"]):
        return "9:16"
    if any(x in niche_lower for x in
           ["presentation", "background", "desktop", "banner", "landscape"]):
        return "16:9"
    if any(x in niche_lower for x in ["instagram", "icon", "logo", "profile"]):
        return "1:1"
    return random.choice(["16:9", "4:3", "1:1"])


def generate_and_save(keyword, ratio_index=0, is_exclusive=False, global_styles=None):
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    styles = global_styles if global_styles else ["modern luxury"]
    style  = styles[hash(keyword) % len(styles)]
    color_palette = get_seasonal_color_palette()

    system_brief = (
        f"You are a premium commercial stock photography art director. "
        f"You create abstract, digital, and corporate concepts — never nature or lifestyle. "
        f"Style: {style}. Palette: {color_palette}. "
        f"{NO_NATURE} {NO_PEOPLE} {NO_TEXT} {COMMERCIAL_MANDATE}"
    )

    user_prompt = (
        f"Write a detailed image generation prompt for a premium {style} commercial concept "
        f"representing: '{keyword}'. Use {color_palette}. "
        f"Translate any organic/nature metaphors (e.g. 'eco', 'cycle', 'growth', 'flow') into "
        f"ABSTRACT VISUAL EQUIVALENTS — glowing geometric loops, flowing light trails, "
        f"interconnected nodes, gradient energy fields, or crystalline structures. "
        f"MANDATORY CONSTRAINTS: {NO_NATURE} {NO_PEOPLE} {NO_TEXT}"
    )

    completion = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": system_brief},
            {"role": "user",   "content": user_prompt},
        ]
    )
    dynamic_prompt = completion.choices[0].message.content

    unique_seed  = int(time.time_ns() % 10_000_000)
    aspect_ratio = determine_aspect_ratio(keyword)

    # Build the final Replicate prompt — append hard-stop suffixes so they survive
    # even if the Groq-generated prompt contradicts them.
    replicate_prompt = (
        f"{dynamic_prompt} "
        f"-- {NO_NATURE} {NO_PEOPLE} {NO_TEXT} "
        f"Photorealistic studio render, no text, no humans, no nature."
    )

    output = replicate.run(
        "black-forest-labs/flux-2-pro",
        input={
            "prompt":           replicate_prompt,
            "aspect_ratio":     aspect_ratio,
            "resolution":       "1 MP",
            "seed":             unique_seed,
            "output_format":    "jpg",
            "safety_tolerance": 3,
        }
    )

    img_url = (output if isinstance(output, str)
               else output[0] if isinstance(output, list)
               else str(output))

    print(f"Upscaling image to guarantee Dreamstime 3 MP minimum requirement...")
    upscale_output = replicate.run(
        "nightmareai/real-esrgan:42fed1c4974146d4d2414e2be2c5277c7fcf05fcc3a73abf41610695738c1d7b",
        input={
            "image":        img_url,
            "scale":        2,
            "face_enhance": False,
        }
    )

    final_url = (upscale_output if isinstance(upscale_output, str) else str(upscale_output))

    img_data  = requests.get(final_url).content
    image_obj = Image.open(BytesIO(img_data))

    # Convert RGBA / palette modes to RGB for clean JPEG encoding
    if image_obj.mode in ("RGBA", "P"):
        image_obj = image_obj.convert("RGB")

    local_path = (
        f"temp_images/gen_{unique_seed}_{aspect_ratio.replace(':', 'x')}_upscaled.jpg"
    )
    image_obj.save(local_path, format="JPEG", quality=95)

    return local_path, dynamic_prompt
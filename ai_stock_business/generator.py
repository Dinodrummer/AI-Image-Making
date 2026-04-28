import replicate, os, requests, time, random, piexif
from PIL import Image, ImageCms
from io import BytesIO

NO_PEOPLE = "NO faces, NO human figures, NO body parts, NO silhouettes, NO crowd shapes whatsoever."
NO_TEXT   = (
    "100% text-free composition. ZERO text, logos, numbers, labels, UI elements, graphs, "
    "charts, legends, watermarks, or typography of any kind anywhere in the image."
)

def generate_and_save(visual_prompt, aspect_ratio="16:9", aesthetic_style="Realistic Commercial", palette="neutral", is_exclusive=False, meta_data=None):
    unique_seed   = random.randint(1, 999999999)

    # Standardize the aspect ratio string
    valid_ratios = ["16:9", "1:1", "21:9", "2:3", "3:2", "4:5", "5:4", "9:16", "9:21"]
    if aspect_ratio not in valid_ratios:
        aspect_ratio = "16:9"

    # Base quality guardrails that we ALWAYS want, regardless of dynamic style
    quality_guardrails = "High quality commercial stock photography, technically flawless, no digital noise, no chaotic visual artifacts. Ensure layout has abundant negative space for copy if it is a background."

    replicate_prompt = (
        f"{visual_prompt}, "
        f"Aesthetic Style: {aesthetic_style}, "
        f"Color Palette: {palette}. "
        f"{quality_guardrails} "
        f"MANDATORY EXCLUSIONS: {NO_PEOPLE} {NO_TEXT}"
    )

    print(f"  Style    : [{aesthetic_style}]")
    print(f"  Ratio    : {aspect_ratio}")

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
    time.sleep(4)

    print(f"  Upscaling to ≥4 MP...")
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

    if image_obj.mode in ("RGBA", "P"):
        image_obj = image_obj.convert("RGB")

    # Pre-screening: check dimensions
    width, height = image_obj.size
    if width < 1500 or height < 1500:
        raise ValueError(f"Image generation failed quality screen. Resolution too low: {width}x{height}")

    os.makedirs("temp_images", exist_ok=True)
    filename = f"gen_{unique_seed}_{aspect_ratio.replace(':', 'x')}_upscaled.jpg"
    filepath = os.path.join("temp_images", filename)
    
    # Construct EXIF data using piexif
    exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}, "thumbnail": None}
    if meta_data:
        title = meta_data.get("title", "")
        keywords = ";".join(meta_data.get("keywords", []))
        desc = meta_data.get("description", "")
        
        exif_dict["0th"][piexif.ImageIFD.ImageDescription] = desc.encode("utf-8")
        exif_dict["0th"][piexif.ImageIFD.XPTitle] = title.encode("utf-16le")
        exif_dict["0th"][piexif.ImageIFD.XPKeywords] = keywords.encode("utf-16le")
        exif_dict["0th"][piexif.ImageIFD.Software] = b"AI Generated"
        
    exif_bytes = piexif.dump(exif_dict)

    # Generate sRGB ICC Profile
    icc_profile = ImageCms.createProfile("sRGB")
    icc_bytes = ImageCms.ImageCmsProfile(icc_profile).tobytes()

    # Save with generated EXIF, ICC profile, and max quality
    image_obj.save(filepath, format="JPEG", quality=100, subsampling=0, exif=exif_bytes, icc_profile=icc_bytes)
    print(f"  Saved    : {filepath} ({width}x{height})")

    return filepath
import replicate, os, requests, time, random
from PIL import Image
from io import BytesIO

NO_PEOPLE = "NO faces, NO human figures, NO body parts, NO silhouettes, NO crowd shapes whatsoever."
NO_TEXT   = (
    "100% text-free composition. ZERO text, numbers, labels, UI elements, graphs, "
    "charts, legends, watermarks, or typography of any kind anywhere in the image."
)

STYLE_PROFILES = {
    "tech_network": {
        "label":   "Tech / Data Network",
        "palette": "electric blue, cyan, steel gray, pure white",
        "no_nature": True,
        "dt_cats": [210, 110],
        "adobe_cat": 19,
        "sub_variants": [
            "Dense 3D web of glowing cyan fiber-optic nodes suspended in dark space",
            "Flat isometric circuit-board plane stretching to the horizon",
            "Cascading vertical columns of luminous blue data particles",
            "Rotating holographic wireframe globe made of intersecting great-circle arcs",
        ],
    },
    "healthcare_science": {
        "label":   "Healthcare / Life Science",
        "palette": "clinical white, soft aqua-teal, pale sky blue, frosted glass transparency",
        "no_nature": True,
        "dt_cats": [92, 209],
        "adobe_cat": 16,
        "sub_variants": [
            "Abstract crystalline double-helix structure in frosted glass and aqua",
            "Geometric molecular lattice of translucent spheres and connecting rods",
            "Cross-section of a glowing hexagonal honeycomb cell structure",
            "Floating transparent 3D capsule forms with internal glowing cores",
        ],
    },
    "dark_neon": {
        "label":   "Dark Mode / Neon Synthwave",
        "palette": "matte black, deep indigo, neon magenta, electric cyan, hot violet",
        "no_nature": True,
        "dt_cats": [45, 112],
        "adobe_cat": 8,
        "sub_variants": [
            "Razor-thin neon magenta grid lines receding to a vanishing point on a matte-black plane",
            "Floating fractured geometric shards in deep indigo with neon cyan edge-glow",
            "Abstract neon circuit-tree topology growing upward",
            "Concentric neon rings in magenta and violet pulsing outward",
        ],
    },
    "luxury_gold": {
        "label":   "Luxury / 24K Gold",
        "palette": "24K polished gold, champagne, obsidian black, deep shadow — NO SILVER, NO NAVY",
        "no_nature": True,
        "dt_cats": [45, 87],
        "adobe_cat": 8,
        "sub_variants": [
            "Extreme macro of a polished 24K gold geometric dodecahedron on a black marble slab",
            "Abstract stacked gold ingot pyramid composition against pure black",
            "Gold liquid metal pour frozen mid-flow",
            "Close-up brushed-gold hexagonal tile mosaic",
        ],
    },
    "architecture_geo": {
        "label":   "Architecture / Brutalist Geometry",
        "palette": "raw concrete gray, warm sand beige, rust-orange accent, deep charcoal — NO GOLD, NO BLUE",
        "no_nature": True,
        "dt_cats": [89, 141],
        "adobe_cat": 3,
        "sub_variants": [
            "Abstract Brutalist concrete facade repeating rectangular window voids",
            "Isometric aerial view of interlocking geometric building blocks",
            "Close-up of a parametric concrete lattice screen",
            "Stacked cantilevered concrete planes at extreme angles",
        ],
    },
    "organic_texture": {
        "label":   "Organic / Mineral Abstract",
        "palette": "terracotta red, mineral teal-green, sandstone cream, slate gray, oxidized copper — NO GOLD",
        "no_nature": True,
        "dt_cats": [141, 164],
        "adobe_cat": 8,
        "sub_variants": [
            "Extreme macro of a polished agate cross-section",
            "Abstract geological strata layers",
            "Terrazzo surface close-up fragments embedded in cream cement",
            "Crystal geode interior jagged oxidized-copper and teal mineral formations",
        ],
    },
    "vibrant_gradient": {
        "label":   "Vibrant Fluid Gradient",
        "palette": "vivid coral, electric violet, cobalt blue, acid yellow-green — NO GOLD, NO GRAY",
        "no_nature": False,
        "dt_cats": [164, 199],
        "adobe_cat": 8,
        "sub_variants": [
            "Huge swirling fluid-simulation paint pour coral and violet merging",
            "Diagonal split-field color composition cobalt blue to acid yellow",
            "Abstract liquid marble veins of hot-pink and electric violet flowing",
            "Four-quadrant color-block gradient soft feathered center blend",
        ],
    },
    "energy_explosive": {
        "label":   "Energy / Power Burst",
        "palette": "deep crimson, fiery orange, electric yellow, white-hot core — NO BLUE, NO GOLD",
        "no_nature": True,
        "dt_cats": [47, 97],
        "adobe_cat": 19,
        "sub_variants": [
            "Radial energy burst plasma arcs shooting outward",
            "Abstract molten lava flow surface glowing orange fissures",
            "Electric arc-discharge close-up branching lightning fractal",
            "Abstract forge fire churning light-painting shapes",
        ],
    },
    "sustainability_green": {
        "label":   "Sustainability / Clean Energy",
        "palette": "deep forest green, bright lime, clean white, translucent glass — NO GOLD, NO BLUE",
        "no_nature": False,
        "dt_cats": [99, 97],
        "adobe_cat": 19,
        "sub_variants": [
            "Abstract 3D hexagonal solar-cell array in deep green and silver",
            "Glowing green data-flow network on dark background",
            "Translucent green geometric leaf-shaped prism forms in repeating pattern",
            "Abstract circular topology of green and silver arrows forming an infinite loop",
        ],
    },
    "chrome_mechanical": {
        "label":   "Chrome / Precision Mechanical",
        "palette": "mirror chrome, brushed platinum steel, pure white highlight, deep black shadow — NO GOLD, NO COLOR",
        "no_nature": True,
        "dt_cats": [100, 113],
        "adobe_cat": 10,
        "sub_variants": [
            "Extreme macro of interlocking precision gear teeth in mirror-polished chrome",
            "Abstract mechanical turbine cross-section",
            "Stacked chrome cylinders at varying heights",
            "Chrome liquid-mercury surface with geometric standing wave ripples",
        ],
    },
    "royal_purple": {
        "label":   "Royal Purple / Amethyst",
        "palette": "deep royal purple, amethyst violet, rose-gold accent, matte black — NO YELLOW GOLD, NO BLUE",
        "no_nature": True,
        "dt_cats": [45, 52],
        "adobe_cat": 8,
        "sub_variants": [
            "Deep purple velvet-texture abstract background with rose-gold geometric line overlay",
            "Amethyst crystal cluster macro catching silver and rose-gold specular highlights",
            "Abstract royal purple fluid with silver iridescent foil sheen slow pour freeze-frame",
            "Purple smoke formation in geometric cone shape perfect symmetry",
        ],
    },
    "warm_earth": {
        "label":   "Warm Earth / Adobe Tones",
        "palette": "burnt sienna, warm terracotta, dusty blush pink, aged linen cream — NO GOLD, NO GRAY",
        "no_nature": True,
        "dt_cats": [141, 48],
        "adobe_cat": 8,
        "sub_variants": [
            "Abstract layered sand dune cross-section forms",
            "Close-up of handmade ceramic bowl interior crackle texture",
            "Burnt sienna plaster wall abstract organic impasto texture",
            "Layered kraft paper strata torn horizontal bands",
        ],
    },
    "ice_glass": {
        "label":   "Ice / Glass / Refraction",
        "palette": "crystal clear, ice blue, cold white, deep navy shadow — NO WARM TONES, NO GOLD",
        "no_nature": True,
        "dt_cats": [39, 112],
        "adobe_cat": 8,
        "sub_variants": [
            "Shattered safety glass abstract crystalline fracture web",
            "Extreme macro of ice crystal formation dendritic branching structure",
            "Stack of clear glass geometric prisms refracting rainbow caustics",
            "Frosted glass sphere on mirror surface deep internal refraction",
        ],
    },
    "minimal_geometric": {
        "label":   "Minimal / Scandinavian Geo",
        "palette": "warm off-white, dusty rose, sage green, muted slate blue — NO GOLD, NO BRIGHT COLORS",
        "no_nature": True,
        "dt_cats": [112, 54],
        "adobe_cat": 8,
        "sub_variants": [
            "Single large sage-green circle on warm off-white extreme negative space",
            "Two overlapping dusty-rose rectangles on cream hard geometric overlap",
            "Three muted slate-blue equilateral triangles in asymmetric constellation",
            "One perfect matte-black square centered on warm white",
        ],
    },
    "finance_power": {
        "label":   "Finance / Corporate Ascent",
        "palette": "deep navy blue, brushed steel silver, pure stark white — NO GOLD, NO WARM TONES",
        "no_nature": True,
        "dt_cats": [80, 52],
        "adobe_cat": 4,
        "sub_variants": [
            "Abstract ascending 3D bar forms in brushed steel and navy",
            "Dark navy abstract corridor of repeating steel arches",
            "Silver metallic arrow forms clustered in upward-angled composition",
            "Abstract precision balance scale in polished steel on white background",
        ],
    },
}

STYLE_PROFILE_KEYS = list(STYLE_PROFILES.keys())

def get_style_sub_variant(style_key: str) -> str:
    profile = STYLE_PROFILES.get(style_key, STYLE_PROFILES["tech_network"])
    return random.choice(profile["sub_variants"])

def generate_and_save(visual_prompt, ratio_index=0, is_exclusive=False, style_key=None):
    unique_seed   = random.randint(1, 999999999)
    # Heavily favor commercial ratios: 16:9, 4:3, 3:2
    aspect_ratios = ["16:9", "16:9", "4:3", "3:2", "3:2", "1:1", "9:16"]
    aspect_ratio  = aspect_ratios[ratio_index % len(aspect_ratios)]

    profile     = STYLE_PROFILES.get(style_key) or STYLE_PROFILES["tech_network"]
    sub_variant = get_style_sub_variant(style_key)

    if profile["no_nature"]:
        nature_clause = "NO nature, NO landscapes, NO organic environments."
    else:
        nature_clause = "Abstract forms ONLY. No recognizable literal landscapes."

    # RESTRUCTURED PROMPT: Subject first, comma separated, camera specs added.
    replicate_prompt = (
        f"{sub_variant}, {visual_prompt}, "
        f"color palette: {profile['palette']}, "
        f"shot on Hasselblad X2D, 100MP, commercial product photography, 8K cinematic studio render, "
        f"technically flawless composition. "
        f"MANDATORY EXCLUSIONS: {NO_PEOPLE} {nature_clause} {NO_TEXT}"
    )

    print(f"  Style    : [{profile['label']}]")
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

    print(f"  Upscaling to ≥3 MP...")
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
    
    # Save while stripping EXIF data via exif=b""
    image_obj.save(filepath, format="JPEG", quality=95, exif=b"")
    print(f"  Saved    : {filepath} ({width}x{height})")

    return filepath
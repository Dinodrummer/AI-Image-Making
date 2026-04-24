import replicate, os, requests, time, random
from PIL import Image
from io import BytesIO

NO_PEOPLE = "NO faces, NO human figures, NO body parts, NO silhouettes, NO crowd shapes whatsoever."
NO_TEXT   = (
    "100% text-free composition. ZERO text, numbers, labels, UI elements, graphs, "
    "charts, legends, watermarks, or typography of any kind anywhere in the image."
)

# ─────────────────────────────────────────────────────────────────────────────
# 15 VISUALLY DISTINCT STYLE PROFILES
#
# Design rule: no two profiles share a dominant color family.
# Each has 4 SUB_VARIANTS — randomly selected at generation time so the same
# style key never produces the same-looking image twice.
# ─────────────────────────────────────────────────────────────────────────────
STYLE_PROFILES = {

    # ── COOL BLUE ────────────────────────────────────────────────────────────
    "tech_network": {
        "label":   "Tech / Data Network",
        "palette": "electric blue, cyan, steel gray, pure white",
        "no_nature": True,
        "dt_cats": [210, 110],
        "adobe_cat": 19,
        "sub_variants": [
            "A dense 3D web of glowing cyan fiber-optic nodes suspended in dark space, "
            "each node a luminous sphere connected by hair-thin light strands, deep cinematic DOF.",
            "A flat isometric circuit-board plane stretching to the horizon, electric-blue "
            "trace lines forming geometric grid patterns, single overhead cold-white key light.",
            "Cascading vertical columns of luminous blue data particles, waterfall motion-blur "
            "effect, dark void background, teal-to-white gradient core glow.",
            "A rotating holographic wireframe globe made of intersecting great-circle arcs "
            "in cyan, floating above a reflective dark surface, atmospheric rim lighting.",
        ],
    },

    # ── AQUA / CLINICAL ──────────────────────────────────────────────────────
    "healthcare_science": {
        "label":   "Healthcare / Life Science",
        "palette": "clinical white, soft aqua-teal, pale sky blue, frosted glass transparency",
        "no_nature": True,
        "dt_cats": [92, 209],
        "adobe_cat": 16,
        "sub_variants": [
            "Abstract crystalline double-helix structure in frosted glass and aqua, "
            "rotating upward against pure white infinity backdrop, soft diffused lab lighting.",
            "Geometric molecular lattice of translucent spheres and connecting rods in pale teal, "
            "pristine clinical white environment, even shadowless illumination.",
            "Cross-section of a glowing hexagonal honeycomb cell structure in ice-blue, "
            "each cell subtly luminous from within, clean white gradient background.",
            "Floating transparent 3D capsule forms with internal glowing cores in aqua-green, "
            "arranged in a precise orbital pattern, studio white light from above.",
        ],
    },

    # ── DARK INDIGO / NEON ───────────────────────────────────────────────────
    "dark_neon": {
        "label":   "Dark Mode / Neon Synthwave",
        "palette": "matte black, deep indigo, neon magenta, electric cyan, hot violet",
        "no_nature": True,
        "dt_cats": [45, 112],
        "adobe_cat": 8,
        "sub_variants": [
            "Razor-thin neon magenta grid lines receding to a vanishing point on a matte-black "
            "plane, atmospheric purple haze horizon, perfect 1-point perspective.",
            "Floating fractured geometric shards in deep indigo with neon cyan edge-glow, "
            "scattered across black void, dramatic individual rim-lighting on each shard.",
            "Abstract neon circuit-tree topology — branching violet and cyan lines growing "
            "upward from bottom edge, dark background, glowing intersection nodes.",
            "Concentric neon rings in magenta and violet pulsing outward from a blinding "
            "white-hot center point, dark atmospheric depth fog, bokeh light scatter.",
        ],
    },

    # ── GOLD / BLACK ─────────────────────────────────────────────────────────
    "luxury_gold": {
        "label":   "Luxury / 24K Gold",
        "palette": "24K polished gold, champagne, obsidian black, deep shadow — NO SILVER, NO NAVY",
        "no_nature": True,
        "dt_cats": [45, 87],
        "adobe_cat": 8,
        "sub_variants": [
            "Extreme macro of a polished 24K gold geometric dodecahedron on a black marble slab, "
            "single hard overhead spotlight, mirror-sharp metallic reflections, rich shadows.",
            "Abstract stacked gold ingot pyramid composition against pure black, dramatic "
            "45-degree side light, crisp shadow edges, champagne highlight on beveled edges.",
            "Gold liquid metal pour frozen mid-flow, ultra-high detail droplets and surface "
            "tension, matte black seamless background, single key light.",
            "Close-up brushed-gold hexagonal tile mosaic, angled raking light casting long "
            "directional shadows across each facet, deep black grout lines, champagne glow.",
        ],
    },

    # ── CONCRETE / WARM SAND ─────────────────────────────────────────────────
    "architecture_geo": {
        "label":   "Architecture / Brutalist Geometry",
        "palette": "raw concrete gray, warm sand beige, rust-orange accent, deep charcoal — NO GOLD, NO BLUE",
        "no_nature": True,
        "dt_cats": [89, 141],
        "adobe_cat": 3,
        "sub_variants": [
            "Abstract Brutalist concrete facade — repeating rectangular window voids casting "
            "deep angular shadows, warm raking side-light, raw poured-concrete texture detail.",
            "Isometric aerial view of interlocking geometric building blocks in concrete and "
            "rust-orange, hard midday shadow geometry, earthy warm palette.",
            "Close-up of a parametric concrete lattice screen — diamond-shaped perforations "
            "with beveled edges, late-afternoon warm light through the voids.",
            "Stacked cantilevered concrete planes at extreme angles, each casting crisp "
            "hard-edged shadows on the plane below, desert-warm ambient light.",
        ],
    },

    # ── TERRACOTTA / MINERAL ─────────────────────────────────────────────────
    "organic_texture": {
        "label":   "Organic / Mineral Abstract",
        "palette": "terracotta red, mineral teal-green, sandstone cream, slate gray, oxidized copper — NO GOLD",
        "no_nature": True,
        "dt_cats": [141, 164],
        "adobe_cat": 8,
        "sub_variants": [
            "Extreme macro of a polished agate cross-section — concentric mineral banding "
            "in terracotta, cream, and teal, glowing translucency, studio light from below.",
            "Abstract geological strata layers — horizontal bands of sandstone, slate, and "
            "copper ore, dramatic cross-section view, matte surface texture detail.",
            "Terrazzo surface close-up — irregular fragments of marble, granite, and "
            "oxidized copper embedded in cream cement, soft even lighting.",
            "Crystal geode interior — jagged oxidized-copper and teal mineral formations "
            "radiating from a dark hollow center, macro detail, cool overhead light.",
        ],
    },

    # ── VIVID CORAL / VIOLET ─────────────────────────────────────────────────
    "vibrant_gradient": {
        "label":   "Vibrant Fluid Gradient",
        "palette": "vivid coral, electric violet, cobalt blue, acid yellow-green — NO GOLD, NO GRAY",
        "no_nature": False,
        "dt_cats": [164, 199],
        "adobe_cat": 8,
        "sub_variants": [
            "Huge swirling fluid-simulation paint pour — coral and violet merging in "
            "slow-motion spiral, ultra-smooth color transitions, no texture, pure color field.",
            "Diagonal split-field color composition — cobalt blue to acid yellow gradient "
            "divided by a sharp diagonal, iridescent holographic foil sheen overlay.",
            "Abstract liquid marble — veins of hot-pink and electric violet flowing through "
            "cobalt blue base, ultra-high detail fluid dynamics freeze-frame.",
            "Four-quadrant color-block gradient — coral top-left, violet top-right, "
            "yellow bottom-left, blue bottom-right, soft feathered center blend.",
        ],
    },

    # ── CRIMSON / ORANGE / FIRE ──────────────────────────────────────────────
    "energy_explosive": {
        "label":   "Energy / Power Burst",
        "palette": "deep crimson, fiery orange, electric yellow, white-hot core — NO BLUE, NO GOLD",
        "no_nature": True,
        "dt_cats": [47, 97],
        "adobe_cat": 19,
        "sub_variants": [
            "Radial energy burst — plasma arcs shooting outward from a white-hot center, "
            "crimson and orange motion trails, dark void background, extreme radial blur.",
            "Abstract molten lava flow surface — glowing orange fissures cracking through "
            "dark basalt crust, top-down macro view, self-illuminated glow.",
            "Electric arc-discharge close-up — branching white-yellow lightning fractal "
            "on deep crimson background, freeze-frame ultra-detail.",
            "Abstract forge fire — churning orange and yellow light-painting shapes, "
            "long-exposure style, deep black background, no recognizable flame forms.",
        ],
    },

    # ── FOREST GREEN / LIME ──────────────────────────────────────────────────
    "sustainability_green": {
        "label":   "Sustainability / Clean Energy",
        "palette": "deep forest green, bright lime, clean white, translucent glass — NO GOLD, NO BLUE",
        "no_nature": False,
        "dt_cats": [99, 97],
        "adobe_cat": 19,
        "sub_variants": [
            "Abstract 3D hexagonal solar-cell array in deep green and silver, "
            "isometric overhead view, bright even diffused light, crisp clean aesthetic.",
            "Glowing green data-flow network on dark background, lime-green luminous nodes, "
            "silver connectors, representing clean energy grid interconnection.",
            "Translucent green geometric leaf-shaped prism forms in repeating pattern, "
            "white studio background, complex glass refraction and caustic detail.",
            "Abstract circular topology of green and silver arrows forming an infinite loop "
            "in 3D chrome, studio white seamless background, crisp precision.",
        ],
    },

    # ── CHROME / PLATINUM ────────────────────────────────────────────────────
    "chrome_mechanical": {
        "label":   "Chrome / Precision Mechanical",
        "palette": "mirror chrome, brushed platinum steel, pure white highlight, deep black shadow — NO GOLD, NO COLOR",
        "no_nature": True,
        "dt_cats": [100, 113],
        "adobe_cat": 10,
        "sub_variants": [
            "Extreme macro of interlocking precision gear teeth in mirror-polished chrome, "
            "dramatic single hard light, crisp reflections, deep black background.",
            "Abstract mechanical turbine cross-section — concentric chrome rings and "
            "radial vanes, top-down view, platinum sheen, industrial precision.",
            "Stacked chrome cylinders at varying heights — brushed vs. polished surface "
            "contrast, hard directional studio light, white infinity background.",
            "Chrome liquid-mercury surface with geometric standing wave ripples, "
            "perfectly reflective, top-down macro, subtle cold light only.",
        ],
    },

    # ── AMETHYST / ROSE-GOLD ─────────────────────────────────────────────────
    "royal_purple": {
        "label":   "Royal Purple / Amethyst",
        "palette": "deep royal purple, amethyst violet, rose-gold accent, matte black — NO YELLOW GOLD, NO BLUE",
        "no_nature": True,
        "dt_cats": [45, 52],
        "adobe_cat": 8,
        "sub_variants": [
            "Deep purple velvet-texture abstract background with rose-gold geometric line "
            "overlay, soft moody studio light, luxury brand aesthetic.",
            "Amethyst crystal cluster macro — faceted purple gem surfaces catching "
            "silver and rose-gold specular highlights, black background, beauty lighting.",
            "Abstract royal purple fluid with silver iridescent foil sheen — "
            "slow pour freeze-frame, studio key light, extreme surface detail.",
            "Purple smoke formation in geometric cone shape on black — "
            "perfect symmetry, rose-gold ambient edge glow, high-fashion editorial.",
        ],
    },

    # ── BURNT SIENNA / BLUSH ─────────────────────────────────────────────────
    "warm_earth": {
        "label":   "Warm Earth / Adobe Tones",
        "palette": "burnt sienna, warm terracotta, dusty blush pink, aged linen cream — NO GOLD, NO GRAY",
        "no_nature": True,
        "dt_cats": [141, 48],
        "adobe_cat": 8,
        "sub_variants": [
            "Abstract layered sand dune cross-section forms — undulating horizontal "
            "bands of terracotta, blush, and cream, side raking warm light, matte surface.",
            "Close-up of handmade ceramic bowl interior — earthy terracotta glaze with "
            "crackle texture, warm directional light, extreme tactile surface detail.",
            "Burnt sienna plaster wall abstract — organic impasto texture with trowel "
            "marks, single warm side-light raking across surface, blush undertones.",
            "Layered kraft paper strata — torn horizontal bands in cream, sienna, and "
            "umber, overhead diffused light, raw paper fiber texture visible.",
        ],
    },

    # ── ICE / CRYSTAL CLEAR ──────────────────────────────────────────────────
    "ice_glass": {
        "label":   "Ice / Glass / Refraction",
        "palette": "crystal clear, ice blue, cold white, deep navy shadow — NO WARM TONES, NO GOLD",
        "no_nature": True,
        "dt_cats": [39, 112],
        "adobe_cat": 8,
        "sub_variants": [
            "Shattered safety glass abstract — crystalline fracture web in clear and ice-blue, "
            "backlit from below, each shard refracting cold blue-white light.",
            "Extreme macro of ice crystal formation — dendritic branching structure in "
            "clear and pale blue, dark navy background, crisp scientific lighting.",
            "Stack of clear glass geometric prisms — each refracting rainbow caustics "
            "across a white surface, clean studio overhead light.",
            "Frosted glass sphere on mirror surface — deep internal refraction, "
            "ice-blue ambient glow, dark seamless background, sharp reflection.",
        ],
    },

    # ── DUSTY ROSE / SAGE ────────────────────────────────────────────────────
    "minimal_geometric": {
        "label":   "Minimal / Scandinavian Geo",
        "palette": "warm off-white, dusty rose, sage green, muted slate blue — NO GOLD, NO BRIGHT COLORS",
        "no_nature": True,
        "dt_cats": [112, 54],
        "adobe_cat": 8,
        "sub_variants": [
            "Single large sage-green circle on warm off-white — extreme negative space, "
            "one soft drop shadow, Bauhaus composition, absolutely nothing else.",
            "Two overlapping dusty-rose rectangles on cream — hard geometric overlap "
            "creating a darker intersection tone, Swiss design grid precision.",
            "Three muted slate-blue equilateral triangles in asymmetric constellation "
            "on warm white, subtle long cast shadow, zero ornamentation.",
            "One perfect matte-black square centered on warm white with a single "
            "thin dusty-rose horizontal rule — pure minimalist Scandinavian aesthetic.",
        ],
    },

    # ── DEEP NAVY / STEEL (Finance — distinct from gold) ────────────────────
    "finance_power": {
        "label":   "Finance / Corporate Ascent",
        "palette": "deep navy blue, brushed steel silver, pure stark white — NO GOLD, NO WARM TONES",
        "no_nature": True,
        "dt_cats": [80, 52],
        "adobe_cat": 4,
        "sub_variants": [
            "Abstract ascending 3D bar forms in brushed steel and navy, rising steeply "
            "left to right, dramatic single overhead studio spot, white background.",
            "Dark navy abstract corridor of repeating steel arches receding to a bright "
            "white vanishing point — corporate architectural perspective.",
            "Silver metallic arrow forms clustered in upward-angled composition, "
            "deep navy background, crisp studio rim-lighting on each edge.",
            "Abstract precision balance scale in polished steel on white background, "
            "machined forms, single hard overhead light, deep geometric shadow.",
        ],
    },
}

STYLE_PROFILE_KEYS = list(STYLE_PROFILES.keys())


def get_style_sub_variant(style_key: str) -> str:
    """Randomly select one of 4 sub-variants for the given style."""
    profile = STYLE_PROFILES.get(style_key, STYLE_PROFILES["tech_network"])
    return random.choice(profile["sub_variants"])


def generate_and_save(visual_prompt, ratio_index=0, is_exclusive=False, style_key=None):
    unique_seed   = random.randint(1, 999999999)
    aspect_ratios = ["16:9", "3:2", "4:3", "1:1", "3:4", "2:3", "9:16"]
    aspect_ratio  = aspect_ratios[ratio_index % len(aspect_ratios)]

    profile     = STYLE_PROFILES.get(style_key) or STYLE_PROFILES["tech_network"]
    sub_variant = get_style_sub_variant(style_key)

    if profile["no_nature"]:
        nature_clause = (
            "ABSOLUTELY NO nature scenes, outdoor landscapes, fields, forests, deserts, "
            "beaches, oceans, mountains, rivers, plants, trees, flowers, animals, insects, "
            "birds, soil, rocks, sky, clouds, sunsets, or any organic outdoor environment."
        )
    else:
        nature_clause = (
            "Abstract forms ONLY. No recognizable plants, animals, people, or literal "
            "landscapes. Abstract color and form inspired by organic shapes is acceptable."
        )

    replicate_prompt = (
        f"PRIMARY COMPOSITION: {sub_variant} "
        f"SUPPLEMENTARY DETAIL: {visual_prompt} "
        f"MANDATORY COLOR PALETTE — use ONLY these colors, no others: {profile['palette']}. "
        f"HARD PROHIBITIONS: {NO_PEOPLE} {nature_clause} {NO_TEXT} "
        f"QUALITY TARGET: Award-winning commercial stock image, 8K cinematic studio render, "
        f"technically flawless composition, suitable for premium editorial licensing."
    )

    print(f"  Style    : [{profile['label']}]")
    print(f"  Variant  : {sub_variant[:90]}...")
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

    os.makedirs("temp_images", exist_ok=True)
    filename = f"gen_{unique_seed}_{aspect_ratio.replace(':', 'x')}_upscaled.jpg"
    filepath = os.path.join("temp_images", filename)
    image_obj.save(filepath, format="JPEG", quality=95)
    print(f"  Saved    : {filepath}")

    return filepath

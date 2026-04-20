import replicate
import os, requests, time, random

def generate_and_save(keyword):
    # Nanosecond seeding prevents repetitive images
    unique_seed = int(time.time_ns() % 10000000)
    
    # MODIFIED: Removed 'negative space' to fix white-block bug
    prompt = (f"A Natural Lo-Fi style professional photograph of {keyword}, "
              f"shot on 35mm f/1.8 lens, centered full-frame composition, " 
              f"300 DPI ultra-high frequency detail, authentic textures, "
              f"natural skin and material textures, real light, no plastic sheen.")
    
    # Dreamstime Safety: Favor faceless or gestural shots
    if any(x in keyword.lower() for x in ["people", "human", "connection"]):
        prompt += ", focus on hands and movements, faceless, cinematic depth."

    output = replicate.run(
        "black-forest-labs/flux-2-pro",
        input={
            "prompt": prompt,
            "aspect_ratio": "3:2",
            "seed": unique_seed,
            "output_format": "jpg",
            "safety_tolerance": 2
        }
    )
    
    image_url = output if isinstance(output, list) else output
    img_data = requests.get(image_url).content
    
    local_path = f"temp_images/gen_{unique_seed}.jpg"
    with open(local_path, 'wb') as f:
        f.write(img_data)
        
    print(f"GEN SUCCESS: {keyword} (Seed {unique_seed})")
    return local_path
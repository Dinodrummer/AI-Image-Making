import os, json
from groq import Groq
from datetime import datetime

def get_trending_keywords():
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    current_month = datetime.now().strftime("%B")
    prompt = (f"What are the TOP 15 HIGHEST-PROFIT keywords buyers are searching for on Dreamstime in {current_month}?\n"
              f"Return ONLY a comma-separated list. Focus on: business, luxury, abstract. No humans. DO NOT suggest AI-related buzzwords unless they are extremely high volume.")
    try:
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}]
        )
        return [k.strip() for k in completion.choices[0].message.content.split(",")[:15]] 
    except:
        return ["modern abstract", "luxury design", "corporate aesthetic"]

def optimize_keyword_density(keywords):
    premium_terms = ['luxury', 'premium', 'business', 'corporate', 'design', 'modern', 'professional', 'abstract']
    premium_kws = [kw for kw in keywords if any(term in kw.lower() for term in premium_terms)]
    regular_kws = [kw for kw in keywords if kw not in premium_kws]
    optimized = premium_kws[:int(len(keywords) * 0.6)] + regular_kws[:int(len(keywords) * 0.4)]
    return optimized[:50] 

def score_metadata_revenue_potential(title, keywords, category_id):
    score = 0
    if 50 <= len(title) <= 80: score += 15 
    elif 40 <= len(title) < 50: score += 10
    else: score += 5
    
    premium_terms = ['luxury', 'premium', 'business', 'corporate', 'design', 'modern', 'abstract']
    premium_count = sum(1 for kw in keywords if any(term in kw.lower() for term in premium_terms))
    score += min(40, premium_count * 2)
    
    longtail_count = sum(1 for kw in keywords if len(kw.split()) >= 2)
    score += min(15, longtail_count)
    
    # Revenue optimization
    if category_id in [19, 43, 26]: score += 20
    elif category_id == 11: score += 15
    else: score += 10
    
    return min(100, score)

def get_image_metadata(dynamic_prompt, global_keywords):
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    # Updated Prompt: Extreme category constraints and de-advertised description mandate
    prompt = f"""
    You are a stock photography SEO expert. Create metadata for an image generated with this exact visual prompt:
    "{dynamic_prompt}"

    DREAMSTIME COMMERCIAL CATEGORIES (Strict Selection):
    allowed_categories = {{
        11: "Abstract (Backgrounds, Concepts, Blurs)",
        19: "Business (Corporate, Finance, Teamwork)",
        20: "Concepts (Metaphors, Ideas)",
        24: "Industry (Manufacturing, Construction)",
        26: "IT & C (Information Technology, AI, Data Visualization)",
        42: "Science (Research, Medical)",
        43: "Design / Architecture",
        50: "Textures & Backgrounds"
    }}
    
    **FORBIDDEN MAIN CATEGORIES** (Do NOT Select These or Any of Their Subcategories):
    Re-read this constraint. You are FORBIDDEN from selecting any category under Nature (31), Seasons Specific (36), Water (39), or People (41). Doing so will result in a zero revenue score. Your entire output will be discarded and replaced with a default. The ONLY allowed categories are from the list below. Re-read this constraint.

    Return ONLY a JSON object with:
    1. "title": Commercial title (60-80 chars, NO commas). Make it highly descriptive. Combine the core concept with practical use-case nouns (e.g., "Abstract Neural Nexus Hub Data Visualization Background"). DO NOT default to AI terms (e.g., "AI-Powered").
    2. "description": A compelling, non-advertising professional 2-3 sentence commercial description (100-200 chars). Act as a describer, not a salesperson. Explain the visual components and suggest how a business might use it (e.g., for presentations, web design, or marketing). CRITICAL: Append " (AI Generated)" at the very end.
    3. "keywords": List of 50 revenue-optimized keywords ordered by commercial value (total words < 80). INCLUDE these trending keywords if relevant: {', '.join(global_keywords[:5])}. Include multi-word long-tail keywords.
    4. "category_id": Pick the BEST primary category ID integer from the strict list above.
    5. "category_id_2": Pick the BEST secondary category ID integer from the strict list above.
    """
    
    try:
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        data = json.loads(completion.choices[0].message.content)
    except Exception as e:
        print(f"Metadata generation failed: {e}")
        # Robust default: abstract tech background, relevant categories
        data = {
            "title": "Modern Abstract Corporate Technology Background", 
            "description": "Premium modern abstract technology background. Perfect for corporate presentations, digital marketing, and data visualization concepts. (AI Generated)",
            "keywords": ["abstract", "modern", "background", "technology", "data"], 
            "category_id": 11, # Abstract
            "category_id_2": 26 # IT&C
        }

    # Post-processing keywords
    all_keywords = data.get('keywords', [])
    final_keywords = []
    total_words = 0
    
    premium_keywords = [kw for kw in all_keywords if any(term in kw.lower() for term in 
                        ['business', 'corporate', 'luxury', 'modern', 'design', 'abstract', 'tech', 'data'])]
    regular_keywords = [kw for kw in all_keywords if kw not in premium_keywords]
    
    premium_keywords.sort(key=lambda x: len(x.split()), reverse=True)
    sorted_keywords = premium_keywords + regular_keywords
    
    for kw in sorted_keywords:
        kw_word_count = len(kw.split())
        if (total_words + kw_word_count) <= 80 and len(final_keywords) < 50:
            final_keywords.append(kw)
            total_words += kw_word_count
        else:
            break
    
    data['keywords'] = optimize_keyword_density(final_keywords)
    
    # Secure title commas
    data['title'] = data.get('title', 'Modern Abstract Tech Design')[:80].replace(',', '')
    
    # Post-processing to enforce " (AI Generated)"
    desc = data.get('description', 'Premium abstract commercial stock photography background. (AI Generated)')
    # Secure it at the description level
    data['description'] = (desc[:1485] + " (AI Generated)").replace(" (AI Generated) (AI Generated)", " (AI Generated)")
    
    data['revenue_score'] = score_metadata_revenue_potential(data['title'], data['keywords'], data.get('category_id', 11))
    
    return data
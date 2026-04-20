import os, time, ftplib, io
from unittest.mock import MagicMock
from PIL import Image
import main

# 1. MOCK GENERATION (Creates a local test image)
def mock_gen_save(keyword):
    if not os.path.exists('temp_images'): os.makedirs('temp_images')
    path = f"temp_images/test_{int(time.time())}.jpg"
    img = Image.new('RGB', (2400, 1600), color=(0, 0, 255))
    img.save(path)
    print(f"MOCK GEN: Created local image for '{keyword}'")
    return path

# 2. MOCK VISION (Returns fake tags)
def mock_get_meta(image_path):
    return {
        "title": "Minimalist Abstract Stock Photo",
        "keywords": ["test", "abstract", "blue", "minimalist"],
        "category_id": 11,
        "ai_flag": True
    }

# 3. MOCK UPLOADER (Connects to your local port 2121 server)
def mock_upload(img_path, meta):
    ftp = ftplib.FTP()
    ftp.connect("127.0.0.1", 2125) # Must match the server port
    ftp.login("test", "test")
    
    img_name = os.path.basename(img_path)
    with open(img_path, 'rb') as f:
        ftp.storbinary(f"STOR {img_name}", f)
        
    csv_name = img_name.replace(".jpg", ".csv")
    csv_content = f"Filename,Title,Keywords,Category\n{img_name},{meta['title']},\"{','.join(meta['keywords'])}\",{meta['category_id']}"
    ftp.storbinary(f"STOR {csv_name}", io.BytesIO(csv_content.encode('utf-8')))
    
    ftp.quit()
    print(f"MOCK UPLOAD: Successfully sent {img_name} to local server.")

# THE FIX: Safely replace the functions and the sleep delay
main.generate_and_save = mock_gen_save
main.get_image_metadata = mock_get_meta
main.upload_to_adobe = mock_upload
# This line now safely disables the delay without recursion
main.time.sleep = MagicMock() 

if __name__ == "__main__":
    print("--- STARTING SYSTEM VALIDATION RUN ---")
    main.main() 
    print("--- VALIDATION COMPLETE ---")
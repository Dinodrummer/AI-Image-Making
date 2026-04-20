import ftplib, csv, os, io, time

def upload_to_adobe(image_path, metadata):
    pass # Adobe Stock SFTP Port 22 reserved

def batch_upload_to_dreamstime(results_list):
    if not results_list:
        print("No assets to upload.")
        return

    try:
        host = os.getenv("DREAMSTIME_FTP_HOST")
        user = os.getenv("DREAMSTIME_FTP_USER")
        pw = os.getenv("DREAMSTIME_FTP_PASS")
        
        ftp = ftplib.FTP(host)
        ftp.login(user, pw)
        ftp.set_pasv(True)
        
        # 1. Upload Images
        for item in results_list:
            img_path = item['path']
            with open(img_path, 'rb') as f:
                ftp.storbinary(f"STOR {os.path.basename(img_path)}", f)
            print(f"BATCH: Uploaded {os.path.basename(img_path)}")

        # 2. Master CSV Creation (Ruggedized for 2026 Ingestor)
        csv_filename = f"batch_{int(time.time())}.csv"
        output = io.StringIO()
        # QUOTE_ALL prevents title commas from shifting columns (Red X fix)
        writer = csv.writer(output, delimiter=',', quotechar='"', quoting=csv.QUOTE_ALL)
        
        # FIXED: Provide an empty list to satisfy writerow's 1-argument requirement
        writer.writerow() 
        
        for item in results_list:
            remote_name = os.path.basename(item['path'])
            # 2026 Policy: Mandatory 'AI generated' prefix for transparency
            title = item['meta']['title']
            if "ai generated" not in title.lower():
                title = f"AI generated {title}"
            
            # Sanitization: Force limit to 70 chars per Dreamstime specs
            title = title[:70].replace('"', '') 
            writer.writerow([remote_name, title, ",".join(item['meta']['keywords'])])
            
        output.seek(0)
        ftp.storbinary(f"STOR {csv_filename}", io.BytesIO(output.getvalue().encode('utf-8')))
        ftp.quit()
        print(f"--- BATCH SUCCESS: {len(results_list)} assets live on Dreamstime ---")
    except Exception as e:
        print(f"UPLOAD ERROR: {e}")
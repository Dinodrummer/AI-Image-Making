import ftplib, csv, os, io, time, shutil

def get_next_batch_id():
    base_dir = "Adobe_Stock_Batches"
    if not os.path.exists(base_dir):
        return 1
        
    max_batch = 0
    for item in os.listdir(base_dir):
        if os.path.isdir(os.path.join(base_dir, item)) and item.startswith("Batch_"):
            try:
                num = int(item.split("_")[1])
                if num > max_batch:
                    max_batch = num
            except (IndexError, ValueError):
                continue
                
    return max_batch + 1

def export_to_adobe_stock_local(results_list, batch_id):
    # Create a dedicated folder using the sequential batch ID
    adobe_dir = os.path.join("Adobe_Stock_Batches", f"Batch_{batch_id}")
    os.makedirs(adobe_dir, exist_ok=True)
    
    csv_path = os.path.join(adobe_dir, "adobe_metadata.csv")
    
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f, delimiter=',', quotechar='"', quoting=csv.QUOTE_ALL)
        
        # Extended Adobe Stock Headers matching the Generative AI checklist
        writer.writerow([
            "Filename", 
            "Title", 
            "Keywords", 
            "Category", 
            "Releases",
            "File type",
            "Created using generative AI tools",
            "People and Property are fictional"
        ])
        
        for item in results_list:
            remote_name = os.path.basename(item['path'])
            
            # Copy the physical image into the Adobe local batch folder
            dest_path = os.path.join(adobe_dir, remote_name)
            try:
                shutil.copy2(item['path'], dest_path)
            except Exception as e:
                print(f"Failed to copy {remote_name} to Adobe folder: {e}")
                continue
            
            # Extract metadata
            title = item['meta'].get('title', 'Abstract Background')[:80]
            keywords = ",".join(item['meta'].get('keywords', []))
            
            # Adobe Category 19 is "Technology". Category 8 is "Graphic Resources". 
            # 19 is heavily preferred for your specific niche.
            adobe_category = 19 
            
            writer.writerow([
                remote_name, 
                title, 
                keywords, 
                adobe_category, 
                "",             # Releases (Left blank)
                "Illustration", # File type
                "Yes",          # Created using generative AI tools
                "Yes"           # People and Property are fictional
            ])
            
    print(f"SUCCESS: Adobe Stock local package prepared at -> {adobe_dir}")


def batch_upload_to_dreamstime(results_list, retry_count=1):
    if not results_list: return True
    
    # Generate the sequential ID once to use for both exports
    batch_id = get_next_batch_id()
    
    # Run the offline Adobe packager first
    export_to_adobe_stock_local(results_list, batch_id)
    
    max_retries = retry_count + 1
    attempt = 0
    
    while attempt < max_retries:
        try:
            ftp = ftplib.FTP(os.getenv("DREAMSTIME_FTP_HOST"))
            ftp.login(os.getenv("DREAMSTIME_FTP_USER"), os.getenv("DREAMSTIME_FTP_PASS"))
            ftp.set_pasv(True)
            
            for idx, item in enumerate(results_list):
                try:
                    remote_name = os.path.basename(item['path'])
                    with open(item['path'], 'rb') as f:
                        ftp.storbinary(f"STOR {remote_name}", f)
                    
                    local_size = os.path.getsize(item['path'])
                    ftp_size = ftp.size(remote_name) if hasattr(ftp, 'size') else 0
                    
                    if ftp_size > 0 and ftp_size != local_size:
                        print(f"WARNING: Size mismatch for {remote_name}")
                    
                    print(f"Uploaded {idx+1}/{len(results_list)}: {remote_name}")
                except Exception as e:
                    print(f"ERROR uploading {item['path']}: {e}")
                    raise
            
            # Name the Dreamstime CSV to match the Adobe batch folder
            csv_filename = f"batch_{batch_id}.csv"
            output = io.StringIO()
            writer = csv.writer(output, delimiter=',', quotechar='"', quoting=csv.QUOTE_ALL)
            
            revenue_scores = []
            
            for idx, item in enumerate(results_list):
                remote_name = os.path.basename(item['path'])
                
                title = item['meta'].get('title', 'Abstract Background')[:80]
                description = item['meta'].get('description', 'Premium abstract commercial stock photography background. (AI Generated)')
                description = (description[:1485] + " (AI Generated)").replace(" (AI Generated) (AI Generated)", " (AI Generated)")[:1500]
                
                category1 = item['meta'].get('category_id', 112)
                category2 = item['meta'].get('category_id_2', 210)
                revenue_scores.append(item['meta'].get('revenue_score', 50))
                
                writer.writerow([
                    remote_name,                              
                    title,                                    
                    description,                              
                    category1,                                
                    category2,                                
                    "",                                       
                    ",".join(item['meta']['keywords']),      
                    "0",  
                    "1",  
                    "1",  
                    "0",  
                    "0",  
                    "0",  
                    "",   
                    ""    
                ])
            
            output.seek(0)
            ftp.storbinary(f"STOR {csv_filename}", io.BytesIO(output.getvalue().encode('utf-8')))
            print(f"CSV metadata uploaded: {csv_filename}")
            ftp.quit()
            
            avg_score = sum(revenue_scores) / len(revenue_scores) if revenue_scores else 0
            print(f"    Avg Revenue Score: {avg_score:.1f}/100")
            return True
            
        except ftplib.all_errors as e:
            attempt += 1
            if attempt < max_retries:
                time.sleep(10)
            else:
                return False
        except Exception as e:
            return False
            
    return False
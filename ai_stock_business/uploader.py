import ftplib, csv, os, io, time

def batch_upload_to_dreamstime(results_list, retry_count=1):
    if not results_list: return True
    
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
            
            csv_filename = f"batch_{int(time.time())}.csv"
            output = io.StringIO()
            writer = csv.writer(output, delimiter=',', quotechar='"', quoting=csv.QUOTE_ALL)
            
            revenue_scores = []
            
            for idx, item in enumerate(results_list):
                remote_name = os.path.basename(item['path'])
                
                title = item['meta'].get('title', 'Abstract Background')[:80]
                description = item['meta'].get('description', 'Premium abstract commercial stock photography background. (AI Generated)')
                description = (description[:1485] + " (AI Generated)").replace(" (AI Generated) (AI Generated)", " (AI Generated)")[:1500]
                
                # REPLACED: Changed the old bad fallback IDs (11, 19) to the REAL IDs (112, 210)
                # 112 = Abstract -> Backgrounds | 210 = IT & C -> Artificial Intelligence
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
                    "0",  # FREE SECTION: 0 (Disabled)
                    "1",  # W-EL: 1 (Enabled)
                    "1",  # P-EL: 1 (Enabled)
                    "0",  # SR-EL
                    "0",  # SR-Price
                    "0",  # Editorial
                    "",   # MR
                    ""    # PR
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
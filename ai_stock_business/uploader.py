import ftplib, csv, os, io, time, shutil

# ─────────────────────────────────────────────────────────────────────────────
# ADOBE STOCK CATEGORY MAP  (style_key → Adobe category integer)
# Adobe: 3=Architecture, 4=Business, 8=Graphic Resources, 10=Industry,
#        16=Science, 19=Technology, 22=Buildings
# ─────────────────────────────────────────────────────────────────────────────
STYLE_ADOBE_CATEGORY = {
    "tech_network":         19,   # Technology
    "luxury_gold":           8,   # Graphic Resources
    "finance_power":         3,   # Business (was 4 Drinks)
    "vibrant_gradient":      8,   # Graphic Resources
    "healthcare_science":   16,   # Science
    "architecture_geo":      2,   # Buildings and Architecture (was 3 Business)
    "energy_explosive":     10,   # Industry
    "dark_neon":             8,   # Graphic Resources
    "organic_texture":       8,   # Graphic Resources
    "minimal_geometric":     8,   # Graphic Resources
    "sustainability_green": 19,   # Technology
    "chrome_mechanical":    10,   # Industry
    "royal_purple":          8,   # Graphic Resources
    "warm_earth":            8,   # Graphic Resources
    "ice_glass":             8,   # Graphic Resources
}

DEFAULT_ADOBE_CATEGORY = 19


def get_next_batch_id():
    base_dir = "Other_Stock_Batches"
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


def export_to_other_stock_local(results_list, batch_id):
    adobe_dir = os.path.join("Other_Stock_Batches", f"Batch_{batch_id}")
    os.makedirs(adobe_dir, exist_ok=True)
    adobe_csv_path = os.path.join(adobe_dir, "adobe_stock_metadata.csv")
    rf123_csv_path = os.path.join(adobe_dir, "123rf_metadata.csv")

    with open(adobe_csv_path, "w", newline="", encoding="utf-8") as f_adobe, \
         open(rf123_csv_path, "w", newline="", encoding="utf-8") as f_123rf:
        
        writer_adobe = csv.writer(f_adobe, delimiter=",", quotechar='"', quoting=csv.QUOTE_ALL)
        writer_123rf = csv.writer(f_123rf, delimiter=",", quotechar='"', quoting=csv.QUOTE_ALL)
        
        writer_adobe.writerow([
            "Filename",
            "Title",
            "Keywords",
            "Category",
            "Releases",
        ])
        
        writer_123rf.writerow([
            "oldfilename",
            "123rf_filename",
            "description",
            "keywords",
            "country"
        ])

        for item in results_list:
            remote_name = os.path.basename(item["path"])
            dest_path   = os.path.join(adobe_dir, remote_name)
            try:
                if not os.path.exists(dest_path):
                    shutil.copy2(item["path"], dest_path)
            except Exception as e:
                print(f"  Copy failed {remote_name}: {e}")
                continue

            title     = item["meta"].get("title", "Abstract Commercial Background")[:80].replace('\n', ' ').replace('\r', '')
            desc      = item["meta"].get("description", "Premium abstract commercial background. (AI Generated)")
            if "(AI Generated)" not in desc:
                desc += " (AI Generated)"
            desc = desc.replace(" (AI Generated) (AI Generated)", " (AI Generated)").replace('\n', ' ').replace('\r', '')[:1500]
            
            keywords  = ",".join(item["meta"].get("keywords", []))
            style_key = item.get("style_key", "")
            adobe_cat = STYLE_ADOBE_CATEGORY.get(style_key, DEFAULT_ADOBE_CATEGORY)

            writer_adobe.writerow([
                remote_name,
                title,
                keywords,
                adobe_cat,
                "",              # Releases — blank for abstract AI
            ])
            
            writer_123rf.writerow([
                remote_name,
                "",              # 123rf_filename (optional)
                desc,
                keywords,
                "US"
            ])

    print(f"  Other Stock package ready → {adobe_dir}")
    return adobe_dir


def batch_upload_to_dreamstime(results_list, retry_count=1):
    if not results_list:
        return True

    batch_id = get_next_batch_id()
    export_to_other_stock_local(results_list, batch_id)

    max_retries = retry_count + 1
    attempt     = 0

    while attempt < max_retries:
        try:
            ftp = ftplib.FTP(os.getenv("DREAMSTIME_FTP_HOST"))
            ftp.login(os.getenv("DREAMSTIME_FTP_USER"), os.getenv("DREAMSTIME_FTP_PASS"))
            ftp.set_pasv(True)

            for idx, item in enumerate(results_list):
                remote_name = os.path.basename(item["path"])
                with open(item["path"], "rb") as f:
                    ftp.storbinary(f"STOR {remote_name}", f)

                local_size = os.path.getsize(item["path"])
                try:
                    ftp_size = ftp.size(remote_name)
                    if ftp_size and ftp_size != local_size:
                        print(f"  Size mismatch: {remote_name} "
                              f"(local={local_size}B remote={ftp_size}B)")
                except Exception:
                    pass

                print(f"  Uploaded {idx+1}/{len(results_list)}: {remote_name}")

            # Build Dreamstime metadata CSV
            csv_filename = f"batch_{batch_id}.csv"
            output       = io.StringIO()
            writer       = csv.writer(output, delimiter=",", quotechar='"',
                                      quoting=csv.QUOTE_ALL)

            revenue_scores = []
            for item in results_list:
                remote_name = os.path.basename(item["path"])
                title       = item["meta"].get("title", "Abstract Background")[:80].replace('\n', ' ').replace('\r', '')

                desc = item["meta"].get(
                    "description",
                    "Premium abstract commercial background. (AI Generated)"
                )
                if "(AI Generated)" not in desc:
                    desc += " (AI Generated)"
                desc = desc.replace(" (AI Generated) (AI Generated)", " (AI Generated)").replace('\n', ' ').replace('\r', '')[:1500]

                cat1  = item["meta"].get("category_id",   112)
                cat2  = item["meta"].get("category_id_2", 210)
                score = item["meta"].get("revenue_score",  50)
                revenue_scores.append(score)

                writer.writerow([
                    remote_name,
                    title,
                    desc,
                    cat1,
                    cat2,
                    "212", # Category 3: Illustrations & Clipart -> AI generated
                    ",".join(item["meta"].get("keywords", [])),
                    "0",  # License Type: 0 = Commercial, 1 = Editorial
                    "0",  # Model Release ID (0 or blank = none)
                    "0",  # Property Release ID (0 or blank = none)
                    "0",  # Price Level (0 = default)
                    "1",  # Extended License (Toggles W-EL and P-EL on)
                    "0",  # Exclusive
                ])

            output.seek(0)
            ftp.storbinary(
                f"STOR {csv_filename}",
                io.BytesIO(output.getvalue().encode("utf-8"))
            )
            print(f"  CSV uploaded: {csv_filename}")
            ftp.quit()

            avg  = sum(revenue_scores) / len(revenue_scores) if revenue_scores else 0
            best = max(revenue_scores) if revenue_scores else 0
            print(f"  Revenue scores — avg: {avg:.1f}  best: {best}/100")
            return True

        except ftplib.all_errors as e:
            attempt += 1
            print(f"  FTP error (attempt {attempt}/{max_retries}): {e}")
            if attempt < max_retries:
                time.sleep(10)
        except Exception as e:
            print(f"  Upload error: {e}")
            return False

    return False

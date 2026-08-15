import os
import sys
import datetime
import zipfile
import requests

BLOB_READ_WRITE_TOKEN = os.environ.get("BLOB_READ_WRITE_TOKEN", "")

def backup_vercel_blob_to_zip():
    token = BLOB_READ_WRITE_TOKEN.strip()
    if not token:
        # Prompt user if token is not set in environment
        token = input("Enter your Vercel BLOB_READ_WRITE_TOKEN: ").strip()

    if not token:
        print("Error: BLOB_READ_WRITE_TOKEN is required to backup Vercel Blob data.")
        sys.exit(1)

    # Generate output zip filename with timestamp in the current working directory
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_filename = f"vercel_blob_backup_{timestamp}.zip"
    zip_path = os.path.abspath(zip_filename)

    headers = {
        "Authorization": f"Bearer {token}"
    }

    has_more = True
    cursor = None
    total_count = 0
    total_bytes = 0

    print(f"Starting Vercel Blob backup to archive: {zip_path}")

    try:
        with zipfile.ZipFile(zip_filename, "w", zipfile.ZIP_DEFLATED) as zip_file:
            while has_more:
                params = {"limit": 1000}
                if cursor:
                    params["cursor"] = cursor

                res = requests.get("https://blob.vercel-storage.com", headers=headers, params=params)
                if res.status_code != 200:
                    print(f"\nError fetching blob list: Status {res.status_code}")
                    print(res.text)
                    sys.exit(1)

                data = res.json()
                blobs = data.get("blobs", [])

                for blob in blobs:
                    pathname = blob["pathname"]
                    download_url = blob.get("downloadUrl") or blob["url"]
                    size = blob.get("size", 0)

                    print(f"Archiving [{size} bytes]: {pathname}")
                    
                    try:
                        with requests.get(download_url, stream=True) as blob_res:
                            blob_res.raise_for_status()
                            # Stream directly into zip member without loading full file into memory
                            with zip_file.open(pathname, "w") as dest:
                                for chunk in blob_res.iter_content(chunk_size=65536):
                                    dest.write(chunk)

                        total_count += 1
                        total_bytes += size
                    except Exception as e:
                        print(f"  FAILED to download {pathname}: {e}")

                has_more = data.get("hasMore", False)
                cursor = data.get("cursor")

        print("\n" + "=" * 50)
        print("Backup successfully completed!")
        print(f"Total files archived: {total_count}")
        print(f"Total uncompressed size: {total_bytes / (1024 * 1024):.2f} MB")
        print(f"Zip archive path: {zip_path}")
        print("=" * 50)

    except KeyboardInterrupt:
        print("\nBackup cancelled by user.")
    except Exception as e:
        print(f"\nUnexpected error during backup: {e}")

if __name__ == "__main__":
    backup_vercel_blob_to_zip()

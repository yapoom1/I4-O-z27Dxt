import asyncio
import httpx
import os
import sys

# Make sure this points to your project's .env file
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.config import settings

VERCEL_BLOB_URL = "https://blob.vercel-storage.com"
BACKUP_DIR = "vercel_blob_backup"

async def backup_blobs():
    if not settings.VERCEL_BLOB_READ_WRITE_TOKEN:
        print("Error: VERCEL_BLOB_READ_WRITE_TOKEN is not set in your .env file")
        return

    print("Fetching list of files from Vercel Blob...")
    
    headers = {
        "Authorization": f"Bearer {settings.VERCEL_BLOB_READ_WRITE_TOKEN}",
        "x-api-version": "7"
    }

    async with httpx.AsyncClient() as client:
        # Step 1: List all blobs
        response = await client.get(
            f"{VERCEL_BLOB_URL}?limit=1000", 
            headers=headers
        )
        
        if response.status_code != 200:
            print(f"Failed to list blobs. Status: {response.status_code}")
            print(response.text)
            return
            
        data = response.json()
        blobs = data.get("blobs", [])
        
        if not blobs:
            print("No files found in the Blob Store.")
            return
            
        print(f"Found {len(blobs)} files. Starting download...")
        
        # Step 2: Create backup directory
        if not os.path.exists(BACKUP_DIR):
            os.makedirs(BACKUP_DIR)
            
        # Step 3: Download each file
        for index, blob in enumerate(blobs, 1):
            url = blob.get("url")
            download_url = blob.get("downloadUrl")
            pathname = blob.get("pathname")
            
            print(f"[{index}/{len(blobs)}] Downloading: {pathname}")
            
            # Create subdirectories if the pathname contains them
            local_path = os.path.join(BACKUP_DIR, pathname)
            local_dir = os.path.dirname(local_path)
            if not os.path.exists(local_dir):
                os.makedirs(local_dir)
                
            try:
                # If downloadUrl is provided, it handles the short-lived token access for private blobs
                fetch_url = download_url if download_url else url 
                
                # IMPORTANT: For private blobs, we MUST pass the authentication headers!
                async with client.stream('GET', fetch_url, headers=headers) as r:
                    if r.status_code == 200:
                        with open(local_path, 'wb') as f:
                            async for chunk in r.aiter_bytes():
                                f.write(chunk)
                        print(f"  -> Saved to {local_path}")
                    else:
                        print(f"  -> Failed to download. Status: {r.status_code}")
            except Exception as e:
                print(f"  -> Error downloading {pathname}: {str(e)}")

    print("\nBackup complete! All files are saved in the 'vercel_blob_backup' folder.")

if __name__ == "__main__":
    asyncio.run(backup_blobs())

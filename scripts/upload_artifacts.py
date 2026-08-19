import asyncio
import uuid
import httpx
import os
import time

import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.config import settings
from app.database.postgres import AsyncSessionLocal, init_postgres
from app.database.mongodb import init_mongodb
from app.media.models import Media
from app.products.products.mongo_models import Product

TENANT_ID = uuid.UUID("2374e160-33dd-4c78-b49e-f8ab4297df1c")
VERCEL_BLOB_URL = "https://blob.vercel-storage.com"

# The artifact files we successfully generated
FILES_TO_UPLOAD = {
    "Makkana (தாமரை விதை)": r"C:\Users\Admin\.gemini\antigravity-ide\brain\599e21d9-17f4-444a-a743-19220efad23e\makkana_1787125436048.png",
    "Dry Strawberry": r"C:\Users\Admin\.gemini\antigravity-ide\brain\599e21d9-17f4-444a-a743-19220efad23e\dry_strawberry_1787125529487.png",
    "Dry Pineapple": r"C:\Users\Admin\.gemini\antigravity-ide\brain\599e21d9-17f4-444a-a743-19220efad23e\dry_pineapple_1787125542014.png"
}

async def upload_to_vercel(file_path: str, entity_id: uuid.UUID) -> dict:
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return None

    with open(file_path, "rb") as f:
        file_bytes = f.read()

    timestamp = int(time.time() * 1000)
    safe_filename = f"{entity_id}-{timestamp}.png"
    blob_path = f"{TENANT_ID}/product/{safe_filename}"

    headers = {
        "Authorization": f"Bearer {settings.VERCEL_BLOB_READ_WRITE_TOKEN}",
        "x-api-version": "7"
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        print(f"Uploading {blob_path} to Vercel...")
        response = await client.put(
            f"{VERCEL_BLOB_URL}/{blob_path}",
            headers=headers,
            content=file_bytes
        )
        
        if response.status_code != 200:
            print(f"Failed to upload {file_path}. Status: {response.status_code}")
            return None
            
        data = response.json()
        return {
            "url": data.get("url"),
            "path": blob_path,
        }

async def main():
    await init_postgres()
    await init_mongodb()
    
    async with AsyncSessionLocal() as session:
        for title, path in FILES_TO_UPLOAD.items():
            # Find the product
            product = await Product.find_one({"tenant_id": TENANT_ID, "title": title, "parent_id": None})
            if not product:
                print(f"Product not found for title: {title}")
                continue
                
            print(f"Found product {product.id} for {title.encode('ascii', 'ignore').decode('ascii')}")
            
            # Upload image
            upload_result = await upload_to_vercel(path, product.id)
            if not upload_result:
                continue
                
            # Create Media record
            media_id = uuid.uuid4()
            media_record = Media(
                id=media_id,
                tenant_id=TENANT_ID,
                entity_name="product",
                entity_id=product.id,
                file_path=upload_result["path"],
                media_url=upload_result["url"],
                media_type="IMAGE",
                file_extension="png",
                alt_text=title
            )
            session.add(media_record)
            
            # Update product with thumbnail
            product.thumbnail_media_id = media_id
            await product.save()
            
            print(f"Successfully mapped Media {media_id} to Product {product.id}")

        await session.commit()
    print("Done uploading images!")

if __name__ == "__main__":
    asyncio.run(main())

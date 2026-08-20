import asyncio
import httpx
import uuid
import time
from app.config import settings

VERCEL_BLOB_URL = "https://blob.vercel-storage.com"

async def test_upload():
    blob_path = f"test-tenant/test-entity/test-{int(time.time())}.txt"
    
    # Try 1: no access header, but in URL
    headers = {
        "Authorization": f"Bearer {settings.VERCEL_BLOB_READ_WRITE_TOKEN}",
        "x-api-version": "7"
    }
    file_bytes = b"hello world"
    
    print("TEST 1: ?access=private")
    async with httpx.AsyncClient() as client:
        response = await client.put(
            f"{VERCEL_BLOB_URL}/{blob_path}?access=private",
            headers=headers,
            content=file_bytes
        )
        print("Status:", response.status_code)
        print("Text:", response.text)

    # Try 2: x-access header
    headers2 = {
        "Authorization": f"Bearer {settings.VERCEL_BLOB_READ_WRITE_TOKEN}",
        "x-api-version": "7",
        "x-vercel-blob-access": "public"
    }
    print("\nTEST 2: headers x-access=private")
    async with httpx.AsyncClient() as client:
        response = await client.put(
            f"{VERCEL_BLOB_URL}/{blob_path}",
            headers=headers2,
            content=file_bytes
        )
        print("Status:", response.status_code)
        print("Text:", response.text)


if __name__ == "__main__":
    asyncio.run(test_upload())

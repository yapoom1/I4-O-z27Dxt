import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import uuid

async def main():
    client = AsyncIOMotorClient("mongodb+srv://Vercel-Admin-atlas-cordovan-cable:qJzu6fq0eeMfWJLT@atlas-cordovan-cable.qprw0vw.mongodb.net/?retryWrites=true&w=majority", uuidRepresentation="standard")
    db = client.gubera_mongo
    p = await db.products.find_one({"_id": uuid.UUID("3316f6c9-75b4-41e0-8f1f-f733a2b9bd99")})
    if p:
        print("Found product!")
        print(f"Product title: {p.get('title')}")
        print(f"Tenant ID: {p.get('tenant_id')}")
    else:
        print("Product not found.")
        
if __name__ == '__main__':
    asyncio.run(main())

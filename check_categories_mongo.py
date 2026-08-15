import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import uuid

async def main():
    client = AsyncIOMotorClient("mongodb+srv://Vercel-Admin-atlas-cordovan-cable:qJzu6fq0eeMfWJLT@atlas-cordovan-cable.qprw0vw.mongodb.net/?retryWrites=true&w=majority", uuidRepresentation="standard")
    db = client.gubera_mongo
    categories = await db.categories.find().to_list(length=100)
    print(f"Total categories: {len(categories)}")
    for c in categories:
        print(f"[{c.get('_id')}] {c.get('title')} (Tenant: {c.get('tenant_id')}) (Parent: {c.get('parent_id')})")
        
if __name__ == '__main__':
    asyncio.run(main())

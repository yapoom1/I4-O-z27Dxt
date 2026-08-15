import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import uuid

async def main():
    client = AsyncIOMotorClient("mongodb+srv://Vercel-Admin-atlas-cordovan-cable:qJzu6fq0eeMfWJLT@atlas-cordovan-cable.qprw0vw.mongodb.net/?retryWrites=true&w=majority")
    db = client.gubera_mongo
    
    docs = await db.products.find({"tenant_id": uuid.UUID("6b1e8aed-ed2c-4d4f-8fd2-682488943f2a")}, {"_id": 1, "title": 1, "tenant_id": 1}).to_list(100)
    print(f"Total products for 6b1e: {len(docs)}")
    for doc in docs[:10]:
        print(doc)

    docs2 = await db.products.find({"tenant_id": uuid.UUID("4c7b9c85-0963-49ba-bd2f-7776a0be4b71")}, {"_id": 1, "title": 1, "tenant_id": 1}).to_list(100)
    print(f"Total products for 4c7b: {len(docs2)}")
    for doc in docs2[:10]:
        print(doc)

if __name__ == "__main__":
    asyncio.run(main())

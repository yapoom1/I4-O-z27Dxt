import asyncio
import uuid
import sys
import os

# Add the project root to the python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.products.categories.services import CategoryService
from app.database.mongodb import init_mongodb

async def main():
    await init_mongodb()
    
    tenant_id = uuid.UUID("3df7a430-2eb8-45a6-8e99-552c13ad88f9")
    try:
        cat = await CategoryService.create_category(
            tenant_id=tenant_id,
            title="Backend Test Cat",
            sku="backend-test-cat"
        )
        print("Success! Created category:", cat.id)
    except Exception as e:
        print("Failed to create category:", str(e))

if __name__ == '__main__':
    asyncio.run(main())

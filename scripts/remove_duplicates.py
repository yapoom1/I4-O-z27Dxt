import asyncio
import uuid
from datetime import datetime

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database.postgres import AsyncSessionLocal, init_postgres
from app.database.mongodb import init_mongodb
from app.products.products.mongo_models import Product
from app.products.pricing.models import ProductPrice, ProductPricingRule
from sqlalchemy import select, delete

TENANT_ID = uuid.UUID("2374e160-33dd-4c78-b49e-f8ab4297df1c")

async def main():
    await init_postgres()
    await init_mongodb()
    
    print("Fetching products...")
    # Find all base products (no parent_id)
    products = await Product.find({"tenant_id": TENANT_ID, "parent_id": None}).to_list()
    
    # Group by title
    from collections import defaultdict
    grouped = defaultdict(list)
    for p in products:
        grouped[p.title].append(p)
        
    async with AsyncSessionLocal() as session:
        for title, prods in grouped.items():
            if len(prods) > 1:
                print(f"Found {len(prods)} duplicates for '{title.encode('ascii', 'ignore').decode('ascii')}'")
                # Sort by created_at descending (newest first)
                prods.sort(key=lambda x: x.created_at, reverse=True)
                
                newest = prods[0]
                duplicates = prods[1:]
                
                print(f"  Keeping: {newest.id} ({newest.created_at})")
                for dup in duplicates:
                    print(f"  Deleting: {dup.id} ({dup.created_at})")
                    
                    # Delete child products
                    children = await Product.find({"parent_id": dup.id, "tenant_id": TENANT_ID}).to_list()
                    child_ids = [c.id for c in children]
                    if child_ids:
                        print(f"    Deleting {len(child_ids)} child variants...")
                        # Delete child prices
                        await session.execute(delete(ProductPrice).where(ProductPrice.product_id.in_(child_ids)))
                        await session.execute(delete(ProductPricingRule).where(ProductPricingRule.product_id.in_(child_ids)))
                        # Delete child products from Mongo
                        await Product.find({"parent_id": dup.id}).delete()
                    
                    # Delete parent prices
                    await session.execute(delete(ProductPrice).where(ProductPrice.product_id == dup.id))
                    await session.execute(delete(ProductPricingRule).where(ProductPricingRule.product_id == dup.id))
                    
                    # Delete parent product from Mongo
                    await dup.delete()
                    
        await session.commit()
    print("Done cleaning up duplicates.")

if __name__ == "__main__":
    asyncio.run(main())

import asyncio
import uuid
from datetime import datetime
from decimal import Decimal

# Add root folder to sys.path
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database.postgres import AsyncSessionLocal, init_postgres
from app.database.mongodb import init_mongodb
from app.products.products.mongo_models import Product
from app.products.pricing.models import ProductPrice, PricingType
from sqlalchemy import select

TENANT_ID = uuid.UUID("2374e160-33dd-4c78-b49e-f8ab4297df1c") # ASHAROYDEN

PRODUCTS_DATA = [
    {"name": "Makkana (தாமரை விதை)", "base_price": 1500, "base_weight_kg": 1, "variants": ["100g", "250g", "500g", "1kg"]},
    {"name": "Dry Strawberry", "base_price": 1000, "base_weight_kg": 1, "variants": ["100g", "250g", "500g", "1kg"]},
    {"name": "Dry Pineapple", "base_price": 1000, "base_weight_kg": 1, "variants": ["100g", "250g", "500g", "1kg"]},
    {"name": "Dry papaya", "base_price": 800, "base_weight_kg": 1, "variants": ["100g", "250g", "500g", "1kg"]},
    {"name": "Dry kiwi (Green)", "base_price": 800, "base_weight_kg": 1, "variants": ["100g", "250g", "500g", "1kg"]},
    {"name": "Dry kiwi (Yellow)", "base_price": 800, "base_weight_kg": 1, "variants": ["100g", "250g", "500g", "1kg"]},
    {"name": "Dry jackfruit", "base_price": 1600, "base_weight_kg": 1, "variants": ["100g", "250g", "500g", "1kg"]},
    {"name": "Craneberry", "base_price": 800, "base_weight_kg": 1, "variants": ["100g", "250g", "500g", "1kg"]},
    {"name": "Roseberry", "base_price": 800, "base_weight_kg": 1, "variants": ["100g", "250g", "500g", "1kg"]},
    {"name": "Gooseberry (dry amala)", "base_price": 800, "base_weight_kg": 1, "variants": ["100g", "250g", "500g", "1kg"]},
    {"name": "Dry pomelo", "base_price": 800, "base_weight_kg": 1, "variants": ["100g", "250g", "500g", "1kg"]},
    {"name": "Dry mango candy", "base_price": 1000, "base_weight_kg": 1, "variants": ["100g", "250g", "500g", "1kg"]},
    {"name": "Dry peach", "base_price": 800, "base_weight_kg": 1, "variants": ["100g", "250g", "500g", "1kg"]},
    {"name": "Premium dried strawberry", "base_price": 1000, "base_weight_kg": 1, "variants": ["100g", "250g", "500g", "1kg"]},
    {"name": "Fruit chips", "base_price": 1400, "base_weight_kg": 1, "variants": ["100g", "250g", "500g", "1kg"]},
    {"name": "Vegitable chips", "base_price": 1200, "base_weight_kg": 1, "variants": ["100g", "250g", "500g", "1kg"]},
    {"name": "அயலை கருவாடு (Ayala)", "base_price": 50, "type": "piece", "variants": []},
    {"name": "Mutton uppukandam", "base_price": 2500, "base_weight_kg": 1, "variants": ["100g", "250g", "500g", "1kg"]},
    {"name": "Beef uppukandam", "base_price": 1500, "base_weight_kg": 1, "variants": ["100g", "250g", "500g", "1kg"]},
    {"name": "Ribbon fish - வாளை மீன்", "base_price": 50, "type": "piece", "variants": []},
    {"name": "anchovies dry fish - நெத்திலி கருவாடு", "base_price": 700, "base_weight_kg": 1, "variants": ["100g", "250g", "500g", "1kg"]},
    {"name": "லவ்லோலிக்காய்", "base_price": 100, "type": "bottle", "variants": []},
    {"name": "சீமை நெல்லிக்காய்", "base_price": 100, "type": "bottle", "variants": []},
    {"name": "காரைக்காய்", "base_price": 100, "type": "bottle", "variants": []},
    {"name": "மாசி கருவாடு - dried tuna fish", "base_price": 800, "base_weight_kg": 1, "variants": ["100g", "250g", "500g", "1kg"]},
    {"name": "சாளை/ மத்தி மீன் கருவாடு - sardine dry fish (20 pieces)", "base_price": 100, "type": "pack", "variants": []},
    {"name": "சாளை/ மத்தி மீன் கருவாடு - sardine dry fish (40 pieces)", "base_price": 200, "type": "pack", "variants": []},
    {"name": "Old tamarind - பழைய புளி", "base_price": 200, "base_weight_kg": 1, "variants": ["100g", "250g", "500g", "1kg"]},
    {"name": "New nadan - நல்ல புளி", "base_price": 250, "base_weight_kg": 1, "variants": ["100g", "250g", "500g", "1kg"]},
    {"name": "குடம்புளி - malabar tamarind", "base_price": 500, "base_weight_kg": 1, "variants": ["100g", "250g", "500g", "1kg"]},
    
    # Karupatti has specific pricing per size, not perfectly proportional
    {"name": "Karupatti - palm jaggery", "base_price": 500, "base_weight_kg": 1, "variants": [
        {"name": "Small size (1/2 kg)", "price": 250},
        {"name": "Medium size (1 kg)", "price": 500},
        {"name": "Big size (1.5 kg)", "price": 750}
    ]},
    
    {"name": "தேன் - honey", "base_price": 300, "base_weight_kg": 1, "variants": [
        {"name": "1/2 kg", "price": 150},
        {"name": "1 kg", "price": 300}
    ]},
    
    {"name": "Blackberry", "base_price": 800, "base_weight_kg": 1, "variants": ["100g", "250g", "500g", "1kg"]},
    
    # Pickles are available in 1kg, 1/2 size, 1/4 size
    {"name": "Tuna Fish Pickle", "base_price": 1000, "base_weight_kg": 1, "variants": ["1/4 kg", "1/2 kg", "1kg"]},
    {"name": "Prawn Pickle", "base_price": 1400, "base_weight_kg": 1, "variants": ["1/4 kg", "1/2 kg", "1kg"]},
    {"name": "Squid Pickle", "base_price": 1200, "base_weight_kg": 1, "variants": ["1/4 kg", "1/2 kg", "1kg"]},
    {"name": "Netili Pickle", "base_price": 1000, "base_weight_kg": 1, "variants": ["1/4 kg", "1/2 kg", "1kg"]},
    {"name": "Chicken Pickle", "base_price": 1200, "base_weight_kg": 1, "variants": ["1/4 kg", "1/2 kg", "1kg"]},
    {"name": "Beef Pickle", "base_price": 1200, "base_weight_kg": 1, "variants": ["1/4 kg", "1/2 kg", "1kg"]},
    
    {"name": "முலிகை கருபட்டி", "base_price": 1000, "base_weight_kg": 1, "variants": [
        {"name": "1 piece", "price": 250},
        {"name": "1 kg", "price": 1000}
    ]},
    
    {"name": "Combo offer: Pineapple, mango, kiwi, Rose berry, black berry all 100grams", "base_price": 499, "type": "combo", "variants": []}
]

def calculate_price(base_price, variant_name):
    if "100g" in variant_name:
        return base_price * 0.1
    elif "250g" in variant_name or "1/4 kg" in variant_name:
        return base_price * 0.25
    elif "500g" in variant_name or "1/2 kg" in variant_name:
        return base_price * 0.5
    elif "1kg" in variant_name:
        return base_price
    return base_price

async def get_or_create_selling_price_type(session):
    stmt = select(PricingType).where(PricingType.tenant_id == TENANT_ID, PricingType.type == 'selling_price')
    result = await session.execute(stmt)
    pt = result.scalar_one_or_none()
    
    if not pt:
        pt = PricingType(tenant_id=TENANT_ID, type='selling_price')
        session.add(pt)
        await session.commit()
        await session.refresh(pt)
    
    return pt

async def main():
    await init_postgres()
    await init_mongodb()
    
    async with AsyncSessionLocal() as session:
        pricing_type = await get_or_create_selling_price_type(session)
        pricing_type_id = pricing_type.id
        print(f"Pricing Type ID: {pricing_type_id}")
        
        for item in PRODUCTS_DATA:
            print(f"Adding product: {item['name'].encode('ascii', 'ignore').decode('ascii')}")
            
            # Create Parent Product
            parent_product = Product(
                tenant_id=TENANT_ID,
                title=item["name"],
                product_type="GOODS",
                sku=f"SKU-{uuid.uuid4().hex[:8].upper()}"
            )
            await parent_product.insert()
            
            # Add base price if it's a stand-alone item (no variants) or just to have a price on parent
            base_price_val = Decimal(str(item["base_price"]))
            pp = ProductPrice(
                product_id=parent_product.id,
                pricing_type_id=pricing_type_id,
                price=base_price_val
            )
            session.add(pp)
            await session.commit()
            
            # Create variants
            for v in item.get("variants", []):
                if isinstance(v, str):
                    v_name = f"{item['name']} - {v}"
                    v_price = calculate_price(item["base_price"], v)
                else:
                    v_name = f"{item['name']} - {v['name']}"
                    v_price = v["price"]
                
                print(f"  -> Adding variant: {v_name.encode('ascii', 'ignore').decode('ascii')} @ {v_price}")
                child_product = Product(
                    tenant_id=TENANT_ID,
                    title=v_name,
                    parent_id=parent_product.id,
                    product_type="GOODS",
                    sku=f"SKU-{uuid.uuid4().hex[:8].upper()}"
                )
                await child_product.insert()
                
                child_pp = ProductPrice(
                    product_id=child_product.id,
                    pricing_type_id=pricing_type_id,
                    price=Decimal(str(v_price))
                )
                session.add(child_pp)
            
            await session.commit()
            
    print("DONE importing products!")

if __name__ == "__main__":
    asyncio.run(main())

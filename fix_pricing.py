import asyncio
import asyncpg

DB_URL = 'postgres://neondb_owner:npg_Kj5Bl0fRNJpu@ep-rough-queen-aoh350r2-pooler.c-2.ap-southeast-1.aws.neon.tech/neondb?sslmode=require'

async def main():
    conn = await asyncpg.connect(DB_URL)
    try:
        print("=== Checking Product Prices table ===")
        # Check if there are any null prices or anomalies
        null_prices = await conn.fetch('SELECT COUNT(*) as count FROM product_prices WHERE price IS NULL')
        print(f"Null prices found: {null_prices[0]['count']}")
        
        zero_prices = await conn.fetch('SELECT COUNT(*) as count FROM product_prices WHERE price <= 0')
        print(f"Zero or negative prices found: {zero_prices[0]['count']}")

        print("\n=== Fixing Pricing Types ===")
        # 1. Update "Selling Price" to "selling_price"
        res1 = await conn.execute("UPDATE pricing_types SET type = 'selling_price' WHERE type = 'Selling Price'")
        print(f"Updated {res1} rows to 'selling_price'.")
        
        # 2. Update "MRP" to "original_price"
        res2 = await conn.execute("UPDATE pricing_types SET type = 'original_price' WHERE type = 'MRP'")
        print(f"Updated {res2} rows to 'original_price'.")
        
        print("\nAll database pricing types have been standardized!")
        
    finally:
        await conn.close()

if __name__ == '__main__':
    asyncio.run(main())

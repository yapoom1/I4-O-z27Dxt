import asyncio
import asyncpg

DB_URL = 'postgres://neondb_owner:npg_Kj5Bl0fRNJpu@ep-rough-queen-aoh350r2-pooler.c-2.ap-southeast-1.aws.neon.tech/neondb?sslmode=require'

async def main():
    conn = await asyncpg.connect(DB_URL)
    try:
        print("=== Migrating 'Selling Price' -> 'selling_price' ===")
        # 1. Get all tenants that have 'Selling Price'
        bad_types = await conn.fetch("SELECT id, tenant_id FROM pricing_types WHERE type = 'Selling Price'")
        
        for bad in bad_types:
            # Check if this tenant already has a good 'selling_price'
            good = await conn.fetchrow("SELECT id FROM pricing_types WHERE tenant_id = $1 AND type = 'selling_price'", bad['tenant_id'])
            
            if good:
                # Merge: move all product_prices from bad to good
                res = await conn.execute("UPDATE product_prices SET pricing_type_id = $1 WHERE pricing_type_id = $2", good['id'], bad['id'])
                print(f"Tenant {bad['tenant_id']}: Moved {res} product prices to existing 'selling_price'.")
                # Delete the bad type
                await conn.execute("DELETE FROM pricing_types WHERE id = $1", bad['id'])
            else:
                # No good type exists, safe to just rename the bad one
                await conn.execute("UPDATE pricing_types SET type = 'selling_price' WHERE id = $1", bad['id'])
                print(f"Tenant {bad['tenant_id']}: Renamed 'Selling Price' to 'selling_price'.")

        print("\n=== Migrating 'MRP' -> 'original_price' ===")
        # 1. Get all tenants that have 'MRP'
        bad_mrps = await conn.fetch("SELECT id, tenant_id FROM pricing_types WHERE type = 'MRP'")
        
        for bad in bad_mrps:
            good = await conn.fetchrow("SELECT id FROM pricing_types WHERE tenant_id = $1 AND type = 'original_price'", bad['tenant_id'])
            
            if good:
                res = await conn.execute("UPDATE product_prices SET pricing_type_id = $1 WHERE pricing_type_id = $2", good['id'], bad['id'])
                print(f"Tenant {bad['tenant_id']}: Moved {res} product prices to existing 'original_price'.")
                await conn.execute("DELETE FROM pricing_types WHERE id = $1", bad['id'])
            else:
                await conn.execute("UPDATE pricing_types SET type = 'original_price' WHERE id = $1", bad['id'])
                print(f"Tenant {bad['tenant_id']}: Renamed 'MRP' to 'original_price'.")

        print("\nFix completed successfully!")
        
    finally:
        await conn.close()

if __name__ == '__main__':
    asyncio.run(main())

import asyncio
import asyncpg
from decimal import Decimal

DB_URL = 'postgres://neondb_owner:npg_Kj5Bl0fRNJpu@ep-rough-queen-aoh350r2-pooler.c-2.ap-southeast-1.aws.neon.tech/neondb?sslmode=require'

async def main():
    conn = await asyncpg.connect(DB_URL)
    try:
        print("=== Pricing Types ===")
        types = await conn.fetch('SELECT id, type, tenant_id FROM pricing_types ORDER BY tenant_id, type')
        for t in types:
            print(f"ID: {t['id']} | Type: '{t['type']}' | Tenant: {t['tenant_id']}")
            
        print("\n=== Pricing Distribution (How many products have each type) ===")
        dist = await conn.fetch('''
            SELECT pt.type, COUNT(pp.id) as count
            FROM pricing_types pt
            LEFT JOIN product_prices pp ON pt.id = pp.pricing_type_id
            GROUP BY pt.type
            ORDER BY count DESC
        ''')
        for d in dist:
            print(f"Type: '{d['type']}' -> {d['count']} prices found")
            
    finally:
        await conn.close()

if __name__ == '__main__':
    asyncio.run(main())

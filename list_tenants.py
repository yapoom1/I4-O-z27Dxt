import asyncio
import asyncpg

DB_URL = 'postgres://neondb_owner:npg_Kj5Bl0fRNJpu@ep-rough-queen-aoh350r2-pooler.c-2.ap-southeast-1.aws.neon.tech/neondb?sslmode=require'

async def main():
    conn = await asyncpg.connect(DB_URL)
    try:
        rows = await conn.fetch('SELECT id, business_name FROM tenants')
        print("Available Tenants:")
        for r in rows:
            print(f"- {r['business_name']}: {r['id']}")
    finally:
        await conn.close()

if __name__ == '__main__':
    asyncio.run(main())

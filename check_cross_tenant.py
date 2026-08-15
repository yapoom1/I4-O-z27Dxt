import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
import uuid

async def main():
    engine = create_async_engine('postgresql+asyncpg://neondb_owner:npg_Kj5Bl0fRNJpu@ep-rough-queen-aoh350r2-pooler.c-2.ap-southeast-1.aws.neon.tech/neondb?ssl=require')
    async with engine.connect() as conn:
        res = await conn.execute(text("""
            SELECT pp.product_id, pt.tenant_id, pt.id as pricing_type_id
            FROM product_prices pp
            JOIN pricing_types pt ON pp.pricing_type_id = pt.id
            LIMIT 20
        """))
        print("Product prices and their pricing type's tenant:")
        for row in res.fetchall():
            print(row)
            
if __name__ == '__main__':
    asyncio.run(main())

import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def main():
    engine = create_async_engine('postgresql+asyncpg://neondb_owner:npg_Kj5Bl0fRNJpu@ep-rough-queen-aoh350r2-pooler.c-2.ap-southeast-1.aws.neon.tech/neondb?ssl=require')
    
    commands = [
        "ALTER TABLE order_items DROP CONSTRAINT IF EXISTS order_items_product_id_fkey;",
        "ALTER TABLE product_reviews DROP CONSTRAINT IF EXISTS product_reviews_product_id_fkey;"
    ]
    
    for cmd in commands:
        try:
            # Execute each drop constraint in its own transaction context
            async with engine.begin() as conn:
                await conn.execute(text(cmd))
                print(f"Successfully executed: {cmd}")
        except Exception as e:
            print(f"Error executing {cmd}: {e}")

if __name__ == '__main__':
    asyncio.run(main())

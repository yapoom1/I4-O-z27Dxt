import asyncio, asyncpg

async def main():
    conn = await asyncpg.connect('postgres://neondb_owner:npg_Kj5Bl0fRNJpu@ep-rough-queen-aoh350r2-pooler.c-2.ap-southeast-1.aws.neon.tech/neondb?sslmode=require')
    
    print('Checking rritstore tenant...')
    row = await conn.fetchrow('SELECT id, business_name FROM tenants WHERE business_name = $1', 'rritstore')
    if row:
        print('Found rritstore:', row['id'])
    else:
        print('Not found rritstore')

    row2 = await conn.fetchrow('SELECT id, business_name FROM tenants WHERE id = $1', 'c71a69fc-d701-4500-95a7-d956a80a7f2d')
    if row2:
        print('Tenant for c71a69fc-d701-4500-95a7-d956a80a7f2d:', row2['business_name'])
    else:
        print('Tenant c71a69fc-d701-4500-95a7-d956a80a7f2d not found')

    await conn.close()

asyncio.run(main())

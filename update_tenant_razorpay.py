import asyncio
import asyncpg
import json
import uuid
from datetime import datetime

DB_URL = 'postgres://neondb_owner:npg_gZAeSy0sbn3I@ep-raspy-queen-aztfxgbc-pooler.c-3.ap-southeast-1.aws.neon.tech/neondb?sslmode=require'

async def update_tenant_razorpay(tenant_name: str, key_id: str, key_secret: str, webhook_secret: str):
    conn = await asyncpg.connect(DB_URL)
    try:
        # 1. Get Tenant ID
        tenant = await conn.fetchrow('SELECT id, business_name FROM tenants WHERE business_name = $1', tenant_name)
        if not tenant:
            print(f"Error: Tenant '{tenant_name}' not found.")
            return
        tenant_id = tenant['id']
        print(f"Found tenant: {tenant['business_name']} (ID: {tenant_id})")

        # 2. Get RAZORPAY Platform Gateway ID
        gateway = await conn.fetchrow('SELECT id FROM payment_gateways WHERE name = $1', 'RAZORPAY')
        if not gateway:
            print("Error: RAZORPAY platform gateway not found. Creating it first...")
            gateway_id = uuid.uuid4()
            await conn.execute('''
                INSERT INTO payment_gateways (id, name, credentials, is_active, created_at, updated_at) 
                VALUES ($1, $2, $3, $4, $5, $6)
            ''', gateway_id, 'RAZORPAY', '{}', True, datetime.utcnow(), datetime.utcnow())
        else:
            gateway_id = gateway['id']
        print(f"Found RAZORPAY gateway ID: {gateway_id}")

        # 3. Upsert Tenant Payment Gateway
        credentials = json.dumps({"key_id": key_id, "key_secret": key_secret})
        
        existing = await conn.fetchrow('''
            SELECT id FROM tenant_payment_gateways 
            WHERE tenant_id = $1 AND gateway_id = $2
        ''', tenant_id, gateway_id)

        if existing:
            await conn.execute('''
                UPDATE tenant_payment_gateways 
                SET credentials = $1, webhook_secret = $2, is_active = $3, updated_at = $4
                WHERE id = $5
            ''', credentials, webhook_secret, True, datetime.utcnow(), existing['id'])
            print(f"Updated existing Razorpay credentials for tenant '{tenant_name}'.")
        else:
            new_id = uuid.uuid4()
            await conn.execute('''
                INSERT INTO tenant_payment_gateways (id, tenant_id, gateway_id, credentials, webhook_secret, is_active, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            ''', new_id, tenant_id, gateway_id, credentials, webhook_secret, True, datetime.utcnow(), datetime.utcnow())
            print(f"Inserted new Razorpay credentials for tenant '{tenant_name}'.")

        # 4. Check & Verify
        verify = await conn.fetchrow('''
            SELECT credentials, is_active FROM tenant_payment_gateways 
            WHERE tenant_id = $1 AND gateway_id = $2
        ''', tenant_id, gateway_id)
        
        print("\n--- Verification ---")
        print(f"Is Active: {verify['is_active']}")
        print(f"Credentials stored: {verify['credentials']}")

    finally:
        await conn.close()

if __name__ == '__main__':
    # Replace these with real credentials!
    TARGET_TENANT = 'Vathukadai'
    RAZORPAY_KEY_ID = 'rzp_live_TUkduudrj5mxx7'
    RAZORPAY_KEY_SECRET = 'qLtEdpcbKZiS7c4o3omOjn0Z'
    WEBHOOK_SECRET = None

    print(f"Updating Razorpay for {TARGET_TENANT}...")
    asyncio.run(update_tenant_razorpay(TARGET_TENANT, RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET, WEBHOOK_SECRET))

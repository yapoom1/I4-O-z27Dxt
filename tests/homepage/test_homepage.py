import pytest
import uuid
import json
from httpx import AsyncClient
from app.main import app
from app.homepage.models import HomepageConfig
from app.database.redis import redis_client

@pytest.fixture
async def admin_token():
    # Helper to generate admin token
    from app.auth.services import auth_service
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    tokens = auth_service.generate_tokens(str(user_id), str(tenant_id), role="SUPER_ADMIN")
    return tokens["access_token"], tenant_id

@pytest.fixture
async def auth_headers(admin_token):
    token, tenant_id = admin_token
    return {
        "Authorization": f"Bearer {token}",
        "X-Tenant-ID": str(tenant_id)
    }

@pytest.fixture(autouse=True)
def override_admin_dependency():
    from app.homepage.dependencies import get_current_admin
    from app.users.models import User
    
    def override():
        return User(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            name="Test Admin",
            email="admin@test.com",
            status="ACTIVE",
            role="SUPER_ADMIN"
        )
    
    app.dependency_overrides[get_current_admin] = override
    yield
    app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_homepage_crud(auth_headers, admin_token):
    _, tenant_id = admin_token
    
    # 1. Create Draft Homepage
    payload = {
        "status": "draft",
        "sections": [
            {
                "type": "banner",
                "title": "Hero Banners",
                "order": 1,
                "config": {
                    "banners": [
                        {"title": "Summer Sale", "image_url": "http://img.com/1", "order": 1}
                    ]
                }
            }
        ]
    }
    
    from httpx import ASGITransport
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/homepage/config", json=payload, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["tenant_id"] == str(tenant_id)
        assert data["status"] == "draft"
        assert len(data["sections"]) == 1
        assert data["version"] == 1
        
        # 2. Get Customer Homepage (Should be 404 because it's draft)
        resp2 = await client.get("/homepage", headers={"X-Tenant-ID": str(tenant_id)})
        assert resp2.status_code == 404
        
        # 3. Get Admin Homepage
        resp3 = await client.get("/homepage/config", headers=auth_headers)
        assert resp3.status_code == 200
        assert resp3.json()["status"] == "draft"
        
        # 4. Update to Published
        update_payload = {"status": "published"}
        resp4 = await client.put("/homepage/config", json=update_payload, headers=auth_headers)
        assert resp4.status_code == 200
        assert resp4.json()["status"] == "published"
        assert resp4.json()["version"] == 2
        
        # 5. Get Customer Homepage (Should be 200 now)
        resp5 = await client.get("/homepage", headers={"X-Tenant-ID": str(tenant_id)})
        assert resp5.status_code == 200
        published_data = resp5.json()
        assert len(published_data["sections"]) == 1
        assert published_data["sections"][0]["type"] == "banner"
        assert len(published_data["sections"][0]["data"]) == 1 # Resolved banner data
        
        # 6. Verify Redis Cache is populated
        cache_key = f"homepage:{tenant_id}"
        cached = await redis_client.get(cache_key)
        assert cached is not None
        
        # 7. Delete Section
        section_id = data["sections"][0]["id"]
        resp6 = await client.delete(f"/homepage/section/{section_id}", headers=auth_headers)
        assert resp6.status_code == 200
        
        # 8. Verify Redis Cache is Invalidated
        cached_after_delete = await redis_client.get(cache_key)
        assert cached_after_delete is None

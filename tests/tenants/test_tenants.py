import pytest
import uuid

# Define mutations and queries at the module level
CREATE_TENANT_MUTATION = """
    mutation CreateTenant($input: CreateTenantInput!) {
        createTenant(input: $input) {
            id
            businessName
        }
    }
"""

GET_TENANT_QUERY = """
    query {
        tenant {
            id
            businessName
        }
    }
"""

@pytest.mark.asyncio
async def test_tenant_flow(execute_query):
    """
    Test the full lifecycle of a Tenant available in the schema: Create -> Read.
    """
    rand_id = uuid.uuid4().hex[:6]
    business_name = f"TestCorp {rand_id}"
    
    # 1. CREATE
    create_variables = {
        "input": {
            "businessName": business_name,
            "adminName": "Admin User",
            "adminEmail": f"admin_{rand_id}@testcorp.com",
            "adminMobile": f"8899{rand_id}",
            "adminPassword": "Password123!"
        }
    }
    
    result = await execute_query(CREATE_TENANT_MUTATION, variables=create_variables)
    assert not result.errors, f"CreateTenant Error: {result.errors}"
    
    tenant_data = result.data["createTenant"]
    tenant_id = tenant_data["id"]
    assert tenant_data["businessName"] == business_name
    
    # 2. READ
    result = await execute_query(GET_TENANT_QUERY, tenant_id=uuid.UUID(tenant_id))
    assert not result.errors, f"GetTenant Error: {result.errors}"
    
    fetched_tenant = result.data["tenant"]
    assert fetched_tenant["id"] == tenant_id
    assert fetched_tenant["businessName"] == business_name


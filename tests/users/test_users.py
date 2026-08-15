import pytest
import uuid

CREATE_USER_ADDRESS_MUTATION = """
    mutation CreateUserAddress($input: CreateUserAddressInput!) {
        createUserAddress(input: $input) {
            id
            addressLine1
            isPrimary
        }
    }
"""

UPDATE_USER_ADDRESS_MUTATION = """
    mutation UpdateUserAddress($id: UUID!, $input: UpdateUserAddressInput!) {
        updateUserAddress(id: $id, input: $input) {
            id
            addressLine1
            isPrimary
        }
    }
"""

MY_ADDRESSES_QUERY = """
    query {
        myAddresses {
            id
            addressLine1
            isPrimary
        }
    }
"""

DELETE_USER_ADDRESS_MUTATION = """
    mutation DeleteUserAddress($id: UUID!) {
        deleteUserAddress(id: $id)
    }
"""

@pytest.mark.asyncio
async def test_users_address_flow(execute_query, db_session):
    """
    Test the full lifecycle of User Address: Create -> Read -> Update -> Delete.
    """
    from app.users.models import User
    from app.tenants.models import Tenant
    
    tenant_id = uuid.uuid4()
    mock_tenant = Tenant(id=tenant_id, business_name="Mock Tenant")
    db_session.add(mock_tenant)
    
    mock_user = User(id=uuid.uuid4(), name="Test User", mobilenumber="9988771122", role="USER", tenant_id=tenant_id)
    db_session.add(mock_user)
    await db_session.commit()
    
    # 1. CREATE
    create_variables = {
        "input": {
            "addressLine1": "123 Test St",
            "pincode": "123456",
            "state": "TestState",
            "district": "TestDistrict",
            "customerName": "Test Customer",
            "phoneNumber": "9988776655",
            "isPrimary": True
        }
    }
    
    result = await execute_query(CREATE_USER_ADDRESS_MUTATION, variables=create_variables, user=mock_user, tenant_id=tenant_id)
    assert not result.errors, f"CreateUserAddress Error: {result.errors}"
    
    address = result.data["createUserAddress"]
    address_id = address["id"]
    assert address["addressLine1"] == "123 Test St"
    assert address["isPrimary"] is True
    
    # 2. READ
    result = await execute_query(MY_ADDRESSES_QUERY, user=mock_user, tenant_id=tenant_id)
    assert not result.errors, f"MyAddresses Error: {result.errors}"
    
    addresses = result.data["myAddresses"]
    assert len(addresses) > 0
    assert any(a["id"] == address_id for a in addresses)
    
    # 3. UPDATE
    update_variables = {
        "id": address_id,
        "input": {
            "addressLine1": "456 Updated St",
            "isPrimary": False
        }
    }
    result = await execute_query(UPDATE_USER_ADDRESS_MUTATION, variables=update_variables, user=mock_user, tenant_id=tenant_id)
    assert not result.errors, f"UpdateUserAddress Error: {result.errors}"
    
    updated_address = result.data["updateUserAddress"]
    assert updated_address["addressLine1"] == "456 Updated St"
    assert updated_address["isPrimary"] is False
    
    # 4. DELETE
    delete_variables = {"id": address_id}
    result = await execute_query(DELETE_USER_ADDRESS_MUTATION, variables=delete_variables, user=mock_user, tenant_id=tenant_id)
    assert not result.errors, f"DeleteUserAddress Error: {result.errors}"
    
    deleted = result.data["deleteUserAddress"]
    assert deleted is True

import pytest
import uuid

SEND_OTP_MUTATION = """
    mutation SendOtp($mobilenumber: String!) {
        sendOtp(mobilenumber: $mobilenumber) {
            success
            message
            otp
        }
    }
"""

LOGIN_OTP_MUTATION = """
    mutation LoginWithOtp($mobilenumber: String!, $otp: String!) {
        loginWithOtp(mobilenumber: $mobilenumber, otp: $otp) {
            tokens {
                accessToken
                refreshToken
            }
            user {
                id
                name
            }
        }
    }
"""

ME_QUERY = """
    query {
        me {
            id
            name
            mobilenumber
        }
    }
"""

@pytest.mark.asyncio
async def test_auth_flow(execute_query, db_session):
    """
    Test the Auth flow: Generate OTP -> Login with OTP -> Fetch Me -> Log out (or token valid check).
    """
    from app.users.models import User
    from app.tenants.models import Tenant
    
    tenant_id = uuid.uuid4()
    mock_tenant = Tenant(id=tenant_id, business_name="Mock Tenant")
    db_session.add(mock_tenant)
    
    mobile = f"998877{uuid.uuid4().hex[:4]}"
    
    # Pre-create user in DB for login
    user = User(
        id=uuid.uuid4(),
        name="Auth Test User",
        mobilenumber=mobile,
        tenant_id=tenant_id,
        role="USER"
    )
    db_session.add(user)
    await db_session.commit()
    
    # 1. SEND OTP
    send_variables = {"mobilenumber": mobile}
    result = await execute_query(SEND_OTP_MUTATION, variables=send_variables, tenant_id=tenant_id)
    assert not result.errors, f"SendOtp Error: {result.errors}"
    
    otp_data = result.data["sendOtp"]
    assert otp_data["success"] is True
    otp_code = otp_data["otp"]
    
    # 2. LOGIN WITH OTP
    login_variables = {
        "mobilenumber": mobile,
        "otp": otp_code
    }
    result = await execute_query(LOGIN_OTP_MUTATION, variables=login_variables, tenant_id=tenant_id)
    assert not result.errors, f"LoginWithOtp Error: {result.errors}"
    
    auth_data = result.data["loginWithOtp"]
    assert "accessToken" in auth_data["tokens"]
    assert auth_data["user"]["name"] == "Auth Test User"
    
    # 3. QUERY ME (Authenticated)
    # We simulate authentication by passing the user object to the context
    result = await execute_query(ME_QUERY, user=user, tenant_id=tenant_id)
    assert not result.errors, f"Me Query Error: {result.errors}"
    
    me_data = result.data["me"]
    assert me_data["id"] == str(user.id)
    assert me_data["mobilenumber"] == mobile
    
    # Cleanup
    await db_session.delete(user)
    await db_session.commit()

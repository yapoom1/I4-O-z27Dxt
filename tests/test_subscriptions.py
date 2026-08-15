"""
Integration tests for the Subscription Module.

Follows the same pattern as tests/test_flow.py:
- Uses schema.execute() with a real AsyncSession and GraphQLContext
- Uses MockRequest to supply headers
- Uses a unique rand_id prefix to avoid unique-constraint failures across runs

Run with:
    python tests/test_subscriptions.py
"""
import asyncio
import uuid
import sys
import os
from datetime import datetime, timedelta

# Adjust sys.path to run from the root of the project
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.graphql.schema import schema
from app.graphql.context import GraphQLContext
from app.database.postgres import AsyncSessionLocal
from app.database.mongodb import init_mongodb
from app.database.redis import redis_client
from app.users.models import User
from app.tenants.models import Tenant
from sqlalchemy.future import select

# --------------------------------------------------------------------------
# Test identifiers — unique per run
# --------------------------------------------------------------------------
rand_id = uuid.uuid4().hex[:6]

PLAN_TITLE_BASIC = f"Basic Plan {rand_id}"
PLAN_TITLE_PRO = f"Pro Plan {rand_id}"

# A SUPER_ADMIN user must exist in DB or we create a tenant + user inline.
# For isolation we create a fresh tenant + admin user, then promote to SUPER_ADMIN.
TEST_BUSINESS_NAME = f"SubTestCorp {rand_id}"
TEST_ADMIN_EMAIL = f"subadmin_{rand_id}@testcorp.com"
TEST_ADMIN_MOBILE = f"777{rand_id}"
TEST_ADMIN_PASSWORD = "SuperSecret123!"


class MockRequest:
    """Mock HTTP request to supply headers."""
    def __init__(self, headers=None):
        self.headers = headers or {}


# --------------------------------------------------------------------------
# Helper
# --------------------------------------------------------------------------

def make_context(db, user=None, tenant_id=None):
    return GraphQLContext(db=db, tenant_id=tenant_id, user=user)


# --------------------------------------------------------------------------
# Main test runner
# --------------------------------------------------------------------------

async def run_subscription_tests():
    print("=== STARTING SUBSCRIPTION MODULE INTEGRATION TESTS ===\n")

    # 1. Initialize infrastructure
    print("Initializing Redis...")
    redis_client.connect()

    print("Initializing MongoDB...")
    try:
        await init_mongodb()
        print("MongoDB connected!")
    except Exception as e:
        print(f"Warning: MongoDB unavailable ({e}). Audit logs will fall back to Python logging.")

    async with AsyncSessionLocal() as db:

        # ----------------------------------------------------------------
        # Step 1: Create Tenant + Admin user
        # ----------------------------------------------------------------
        print("\n--- [1] Creating Test Tenant ---")
        create_tenant_mutation = """
            mutation CreateTenant($input: CreateTenantInput!) {
                createTenant(input: $input) { id businessName }
            }
        """
        result = await schema.execute(
            create_tenant_mutation,
            variable_values={"input": {
                "businessName": TEST_BUSINESS_NAME,
                "adminName": "Sub Admin",
                "adminEmail": TEST_ADMIN_EMAIL,
                "adminMobile": TEST_ADMIN_MOBILE,
                "adminPassword": TEST_ADMIN_PASSWORD,
            }},
            context_value=make_context(db)
        )
        if result.errors:
            print(f"CreateTenant Error: {result.errors}")
            return
        tenant_data = result.data["createTenant"]
        tenant_id = uuid.UUID(tenant_data["id"])
        print(f"Tenant created: {tenant_data['businessName']} (ID: {tenant_data['id']})")

        # ----------------------------------------------------------------
        # Step 2: Login as admin
        # ----------------------------------------------------------------
        print("\n--- [2] Logging in as Admin ---")
        login_mutation = """
            mutation Login($emailOrMobile: String!, $password: String!) {
                loginWithPassword(emailOrMobile: $emailOrMobile, password: $password) {
                    user { id role }
                }
            }
        """
        result = await schema.execute(
            login_mutation,
            variable_values={
                "emailOrMobile": TEST_ADMIN_EMAIL,
                "password": TEST_ADMIN_PASSWORD,
            },
            context_value=make_context(db, tenant_id=tenant_id)
        )
        if result.errors:
            print(f"Login Error: {result.errors}")
            return
        user_data = result.data["loginWithPassword"]["user"]
        print(f"Logged in as: {user_data['role']} (ID: {user_data['id']})")

        # Fetch DB user
        stmt = select(User).where(User.id == uuid.UUID(user_data["id"]))
        res = await db.execute(stmt)
        db_admin = res.scalar_one()

        # Promote to SUPER_ADMIN for plan management
        db_admin.role = "SUPER_ADMIN"
        await db.flush()
        print("Promoted user to SUPER_ADMIN for plan management tests.")

        # ----------------------------------------------------------------
        # Step 3: Create a Subscription Plan (SUPER_ADMIN)
        # ----------------------------------------------------------------
        print("\n--- [3] Mutation: createSubscriptionPlan ---")
        create_plan_mutation = """
            mutation CreatePlan($input: CreateSubscriptionPlanInput!) {
                createSubscriptionPlan(input: $input) {
                    id title price billingCycle type isActive createdAt
                }
            }
        """
        result = await schema.execute(
            create_plan_mutation,
            variable_values={"input": {
                "title": PLAN_TITLE_BASIC,
                "price": 499.00,
                "billingCycle": "MONTHLY",
                "type": "BASIC",
                "description": "Basic plan with limited features",
                "isActive": True,
            }},
            context_value=make_context(db, user=db_admin, tenant_id=tenant_id)
        )
        if result.errors:
            print(f"createSubscriptionPlan Error: {result.errors}")
            return
        plan = result.data["createSubscriptionPlan"]
        plan_id = plan["id"]
        print(f"Plan created: {plan['title']} @ {plan['price']} / {plan['billingCycle']} (ID: {plan_id})")
        assert plan["type"] == "BASIC"
        assert plan["isActive"] is True

        # ----------------------------------------------------------------
        # Step 4: Create duplicate plan — should fail
        # ----------------------------------------------------------------
        print("\n--- [4] createSubscriptionPlan (Duplicate Title - Expected Fail) ---")
        result = await schema.execute(
            create_plan_mutation,
            variable_values={"input": {
                "title": PLAN_TITLE_BASIC,
                "price": 999.00,
                "billingCycle": "YEARLY",
                "type": "PRO",
            }},
            context_value=make_context(db, user=db_admin, tenant_id=tenant_id)
        )
        if result.errors:
            print(f"SUCCESS: Duplicate plan creation blocked: {result.errors[0].message}")
        else:
            print("FAILURE: Duplicate plan creation should have failed!")
            return

        # ----------------------------------------------------------------
        # Step 5: Create a second PRO plan for renewal tests
        # ----------------------------------------------------------------
        print("\n--- [5] createSubscriptionPlan (PRO) ---")
        result = await schema.execute(
            create_plan_mutation,
            variable_values={"input": {
                "title": PLAN_TITLE_PRO,
                "price": 999.00,
                "billingCycle": "MONTHLY",
                "type": "PRO",
            }},
            context_value=make_context(db, user=db_admin, tenant_id=tenant_id)
        )
        if result.errors:
            print(f"createSubscriptionPlan PRO Error: {result.errors}")
            return
        pro_plan = result.data["createSubscriptionPlan"]
        pro_plan_id = pro_plan["id"]
        print(f"PRO Plan created: {pro_plan['title']} (ID: {pro_plan_id})")

        # ----------------------------------------------------------------
        # Step 6: Update subscription plan
        # ----------------------------------------------------------------
        print("\n--- [6] Mutation: updateSubscriptionPlan ---")
        update_plan_mutation = """
            mutation UpdatePlan($id: UUID!, $input: UpdateSubscriptionPlanInput!) {
                updateSubscriptionPlan(id: $id, input: $input) {
                    id title price description
                }
            }
        """
        result = await schema.execute(
            update_plan_mutation,
            variable_values={
                "id": plan_id,
                "input": {
                    "description": "Updated: Basic plan with essential features",
                    "price": 449.00,
                }
            },
            context_value=make_context(db, user=db_admin, tenant_id=tenant_id)
        )
        if result.errors:
            print(f"updateSubscriptionPlan Error: {result.errors}")
            return
        updated_plan = result.data["updateSubscriptionPlan"]
        print(f"Plan updated: price={updated_plan['price']}, description={updated_plan['description'][:40]}")
        assert float(updated_plan["price"]) == 449.00

        # ----------------------------------------------------------------
        # Step 7: Query all plans
        # ----------------------------------------------------------------
        print("\n--- [7] Query: getSubscriptionPlans ---")
        query_plans = """
            query GetPlans($activeOnly: Boolean) {
                getSubscriptionPlans(activeOnly: $activeOnly) {
                    id title price billingCycle type isActive
                }
            }
        """
        result = await schema.execute(
            query_plans,
            variable_values={"activeOnly": False},
            context_value=make_context(db, user=db_admin, tenant_id=tenant_id)
        )
        if result.errors:
            print(f"getSubscriptionPlans Error: {result.errors}")
            return
        plans_list = result.data["getSubscriptionPlans"]
        print(f"Total plans returned: {len(plans_list)}")
        assert any(p["id"] == plan_id for p in plans_list), "Basic plan should be in list"
        assert any(p["id"] == pro_plan_id for p in plans_list), "PRO plan should be in list"

        # ----------------------------------------------------------------
        # Step 8: Query single plan by ID
        # ----------------------------------------------------------------
        print("\n--- [8] Query: getSubscriptionPlanById ---")
        query_plan_by_id = """
            query GetPlanById($id: UUID!) {
                getSubscriptionPlanById(id: $id) {
                    id title price features { id codEnabled cmsEnabled }
                }
            }
        """
        result = await schema.execute(
            query_plan_by_id,
            variable_values={"id": plan_id},
            context_value=make_context(db, user=db_admin, tenant_id=tenant_id)
        )
        if result.errors:
            print(f"getSubscriptionPlanById Error: {result.errors}")
            return
        fetched_plan = result.data["getSubscriptionPlanById"]
        print(f"Plan fetched by ID: {fetched_plan['title']} | features={fetched_plan['features']}")
        assert fetched_plan["id"] == plan_id
        assert fetched_plan["features"] is None  # Not yet created

        # ----------------------------------------------------------------
        # Step 9: Create subscription features for Basic plan
        # ----------------------------------------------------------------
        print("\n--- [9] Mutation: createSubscriptionFeatures ---")
        create_features_mutation = """
            mutation CreateFeatures($input: CreateSubscriptionFeaturesInput!) {
                createSubscriptionFeatures(input: $input) {
                    id planId userLimit productLimit couponLimit
                    codEnabled cmsEnabled otpLoginEnabled customDomainEnabled
                }
            }
        """
        result = await schema.execute(
            create_features_mutation,
            variable_values={"input": {
                "planId": plan_id,
                "userLimit": 5,
                "productLimit": 50,
                "couponLimit": 10,
                "codEnabled": True,
                "cmsEnabled": False,
                "otpLoginEnabled": True,
                "customDomainEnabled": False,
            }},
            context_value=make_context(db, user=db_admin, tenant_id=tenant_id)
        )
        if result.errors:
            print(f"createSubscriptionFeatures Error: {result.errors}")
            return
        features = result.data["createSubscriptionFeatures"]
        features_id = features["id"]
        print(f"Features created: userLimit={features['userLimit']}, codEnabled={features['codEnabled']}")
        assert features["userLimit"] == 5
        assert features["codEnabled"] is True

        # ----------------------------------------------------------------
        # Step 10: Duplicate features — should fail
        # ----------------------------------------------------------------
        print("\n--- [10] createSubscriptionFeatures (Duplicate - Expected Fail) ---")
        result = await schema.execute(
            create_features_mutation,
            variable_values={"input": {"planId": plan_id, "userLimit": 10}},
            context_value=make_context(db, user=db_admin, tenant_id=tenant_id)
        )
        if result.errors:
            print(f"SUCCESS: Duplicate features blocked: {result.errors[0].message}")
        else:
            print("FAILURE: Duplicate features creation should have failed!")
            return

        # ----------------------------------------------------------------
        # Step 11: Update subscription features
        # ----------------------------------------------------------------
        print("\n--- [11] Mutation: updateSubscriptionFeatures ---")
        update_features_mutation = """
            mutation UpdateFeatures($planId: UUID!, $input: UpdateSubscriptionFeaturesInput!) {
                updateSubscriptionFeatures(planId: $planId, input: $input) {
                    id cmsEnabled userLimit
                }
            }
        """
        result = await schema.execute(
            update_features_mutation,
            variable_values={
                "planId": plan_id,
                "input": {"cmsEnabled": True, "userLimit": 10}
            },
            context_value=make_context(db, user=db_admin, tenant_id=tenant_id)
        )
        if result.errors:
            print(f"updateSubscriptionFeatures Error: {result.errors}")
            return
        updated_features = result.data["updateSubscriptionFeatures"]
        print(f"Features updated: cmsEnabled={updated_features['cmsEnabled']}, userLimit={updated_features['userLimit']}")
        assert updated_features["cmsEnabled"] is True
        assert updated_features["userLimit"] == 10

        # ----------------------------------------------------------------
        # Step 12: Subscribe tenant to Basic plan
        # ----------------------------------------------------------------
        print("\n--- [12] Mutation: subscribeTenant ---")
        subscribe_mutation = """
            mutation Subscribe($input: SubscribeTenantInput!) {
                subscribeTenant(input: $input) {
                    id tenantId planId planTitleSnapshot planPriceSnapshot
                    amount status startDate endDate
                }
            }
        """
        now = datetime.utcnow()
        start_dt = now.strftime("%Y-%m-%dT%H:%M:%S")
        end_dt = (now + timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%S")
        result = await schema.execute(
            subscribe_mutation,
            variable_values={"input": {
                "planId": plan_id,
                "startDate": start_dt,
                "endDate": end_dt,
                "status": "ACTIVE",
            }},
            context_value=make_context(db, user=db_admin, tenant_id=tenant_id)
        )
        if result.errors:
            print(f"subscribeTenant Error: {result.errors}")
            return
        subscription = result.data["subscribeTenant"]
        subscription_id = subscription["id"]
        print(
            f"Tenant subscribed: ID={subscription_id} | plan={subscription['planTitleSnapshot']} "
            f"@ snapshot_price={subscription['planPriceSnapshot']} | amount={subscription['amount']} "
            f"| status={subscription['status']}"
        )
        # Snapshot should reflect the price AT subscription time (449.00, not original 499)
        assert float(subscription["planPriceSnapshot"]) == 449.00, \
            "Price snapshot should be current plan price"
        assert float(subscription["amount"]) == 449.00
        assert subscription["status"] == "ACTIVE"

        # ----------------------------------------------------------------
        # Step 13: Duplicate subscription — should fail
        # ----------------------------------------------------------------
        print("\n--- [13] subscribeTenant (Duplicate Active - Expected Fail) ---")
        result = await schema.execute(
            subscribe_mutation,
            variable_values={"input": {
                "planId": pro_plan_id,
                "startDate": start_dt,
                "endDate": end_dt,
            }},
            context_value=make_context(db, user=db_admin, tenant_id=tenant_id)
        )
        if result.errors:
            print(f"SUCCESS: Duplicate subscription blocked: {result.errors[0].message}")
        else:
            print("FAILURE: Duplicate active subscription should have failed!")
            return

        # ----------------------------------------------------------------
        # Step 14: Query active subscription
        # ----------------------------------------------------------------
        print("\n--- [14] Query: getTenantSubscription ---")
        query_subscription = """
            query GetSub {
                getTenantSubscription {
                    id status planTitleSnapshot plan { id title }
                    features { userLimit codEnabled cmsEnabled }
                }
            }
        """
        result = await schema.execute(
            query_subscription,
            context_value=make_context(db, user=db_admin, tenant_id=tenant_id)
        )
        if result.errors:
            print(f"getTenantSubscription Error: {result.errors}")
            return
        active_sub = result.data["getTenantSubscription"]
        print(
            f"Active subscription: status={active_sub['status']} | plan={active_sub['planTitleSnapshot']} "
            f"| features={{ userLimit={active_sub['features']['userLimit']}, cms={active_sub['features']['cmsEnabled']} }}"
        )
        assert active_sub["status"] == "ACTIVE"
        assert active_sub["plan"]["id"] == plan_id
        assert active_sub["features"]["cmsEnabled"] is True

        # ----------------------------------------------------------------
        # Step 15: Query subscription features via dedicated query
        # ----------------------------------------------------------------
        print("\n--- [15] Query: getSubscriptionFeatures ---")
        query_features = """
            query GetFeatures {
                getSubscriptionFeatures {
                    userLimit productLimit couponLimit
                    codEnabled cmsEnabled otpLoginEnabled customDomainEnabled
                }
            }
        """
        result = await schema.execute(
            query_features,
            context_value=make_context(db, user=db_admin, tenant_id=tenant_id)
        )
        if result.errors:
            print(f"getSubscriptionFeatures Error: {result.errors}")
            return
        resolved_features = result.data["getSubscriptionFeatures"]
        print(f"Resolved features: {resolved_features}")
        assert resolved_features["userLimit"] == 10
        assert resolved_features["codEnabled"] is True
        assert resolved_features["cmsEnabled"] is True

        # ----------------------------------------------------------------
        # Step 16: Record a payment
        # ----------------------------------------------------------------
        print("\n--- [16] Mutation: createTenantSubscriptionPayment ---")
        create_payment_mutation = """
            mutation CreatePayment($input: CreateTenantSubscriptionPaymentInput!) {
                createTenantSubscriptionPayment(input: $input) {
                    id tenantSubscriptionId amount paymentMethod status transactionId
                }
            }
        """
        result = await schema.execute(
            create_payment_mutation,
            variable_values={"input": {
                "tenantSubscriptionId": subscription_id,
                "amount": 449.00,
                "paymentMethod": "UPI",
                "status": "SUCCESS",
                "transactionId": f"TXN_{rand_id}_001",
            }},
            context_value=make_context(db, user=db_admin, tenant_id=tenant_id)
        )
        if result.errors:
            print(f"createTenantSubscriptionPayment Error: {result.errors}")
            return
        payment = result.data["createTenantSubscriptionPayment"]
        print(f"Payment recorded: ID={payment['id']} | amount={payment['amount']} | status={payment['status']}")
        assert payment["status"] == "SUCCESS"
        assert float(payment["amount"]) == 449.00

        # ----------------------------------------------------------------
        # Step 17: Query payments
        # ----------------------------------------------------------------
        print("\n--- [17] Query: getTenantSubscriptionPayments ---")
        query_payments = """
            query GetPayments($tenantSubscriptionId: UUID!) {
                getTenantSubscriptionPayments(tenantSubscriptionId: $tenantSubscriptionId) {
                    id amount status transactionId paymentMethod
                }
            }
        """
        result = await schema.execute(
            query_payments,
            variable_values={"tenantSubscriptionId": subscription_id},
            context_value=make_context(db, user=db_admin, tenant_id=tenant_id)
        )
        if result.errors:
            print(f"getTenantSubscriptionPayments Error: {result.errors}")
            return
        payments = result.data["getTenantSubscriptionPayments"]
        print(f"Payments for subscription: {len(payments)} record(s)")
        assert len(payments) == 1
        assert payments[0]["status"] == "SUCCESS"

        # ----------------------------------------------------------------
        # Step 18: Renew subscription (cancels current, creates new)
        # ----------------------------------------------------------------
        print("\n--- [18] Mutation: renewTenantSubscription (switch to PRO) ---")
        renew_mutation = """
            mutation Renew($input: RenewTenantSubscriptionInput!) {
                renewTenantSubscription(input: $input) {
                    id planTitleSnapshot planPriceSnapshot amount status
                }
            }
        """
        new_start = (now + timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%S")
        new_end = (now + timedelta(days=60)).strftime("%Y-%m-%dT%H:%M:%S")
        result = await schema.execute(
            renew_mutation,
            variable_values={"input": {
                "planId": pro_plan_id,
                "startDate": new_start,
                "endDate": new_end,
            }},
            context_value=make_context(db, user=db_admin, tenant_id=tenant_id)
        )
        if result.errors:
            print(f"renewTenantSubscription Error: {result.errors}")
            return
        renewed_sub = result.data["renewTenantSubscription"]
        print(
            f"Renewed: plan={renewed_sub['planTitleSnapshot']} | "
            f"snapshot_price={renewed_sub['planPriceSnapshot']} | amount={renewed_sub['amount']} | status={renewed_sub['status']}"
        )
        assert renewed_sub["status"] == "ACTIVE"
        assert float(renewed_sub["planPriceSnapshot"]) == 999.00  # PRO plan price

        # Verify new subscription is now the active one
        result = await schema.execute(
            query_subscription,
            context_value=make_context(db, user=db_admin, tenant_id=tenant_id)
        )
        new_active = result.data["getTenantSubscription"]
        print(f"New active subscription plan: {new_active['planTitleSnapshot']}")
        assert PLAN_TITLE_PRO in new_active["planTitleSnapshot"]

        # ----------------------------------------------------------------
        # Step 19: Cancel subscription
        # ----------------------------------------------------------------
        print("\n--- [19] Mutation: cancelTenantSubscription ---")
        cancel_mutation = """
            mutation Cancel($remark: String) {
                cancelTenantSubscription(remark: $remark) {
                    id status remark
                }
            }
        """
        result = await schema.execute(
            cancel_mutation,
            variable_values={"remark": "Test cancellation"},
            context_value=make_context(db, user=db_admin, tenant_id=tenant_id)
        )
        if result.errors:
            print(f"cancelTenantSubscription Error: {result.errors}")
            return
        cancelled_sub = result.data["cancelTenantSubscription"]
        print(f"Subscription cancelled: status={cancelled_sub['status']} | remark={cancelled_sub['remark']}")
        assert cancelled_sub["status"] == "CANCELLED"

        # Verify no active subscription now
        result = await schema.execute(
            query_subscription,
            context_value=make_context(db, user=db_admin, tenant_id=tenant_id)
        )
        assert result.data["getTenantSubscription"] is None
        print("Confirmed: getTenantSubscription returns None after cancellation.")

        # ----------------------------------------------------------------
        # Step 20: Delete plan — should succeed (no active subscriptions)
        # ----------------------------------------------------------------
        print("\n--- [20] Mutation: deleteSubscriptionPlan (PRO, no active subs) ---")
        delete_plan_mutation = """
            mutation DeletePlan($id: UUID!) {
                deleteSubscriptionPlan(id: $id)
            }
        """
        result = await schema.execute(
            delete_plan_mutation,
            variable_values={"id": pro_plan_id},
            context_value=make_context(db, user=db_admin, tenant_id=tenant_id)
        )
        if result.errors:
            print(f"deleteSubscriptionPlan Error: {result.errors}")
            return
        deleted = result.data["deleteSubscriptionPlan"]
        print(f"PRO Plan deleted: {deleted}")
        assert deleted is True

        # ----------------------------------------------------------------
        # Done
        # ----------------------------------------------------------------
        print("\n=== ALL SUBSCRIPTION MODULE TESTS PASSED! ===\n")


if __name__ == "__main__":
    asyncio.run(run_subscription_tests())

import os
import sys
import pytest
import asyncio

# Adjust sys.path to run from the root of the project
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database.postgres import AsyncSessionLocal
from app.database.redis import redis_client
from app.database.mongodb import init_mongodb
from app.graphql.context import GraphQLContext
from app.graphql.schema import schema

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test case."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session", autouse=True)
async def setup_databases():
    """Initialize Redis and MongoDB for the test session."""
    redis_client.connect()
    
    try:
        mongo_client = await init_mongodb()
    except Exception as e:
        print(f"Warning: MongoDB connection failed ({e}). Proceeding without Beanie ODM.")
        mongo_client = None

    yield
    
    await redis_client.close()
    if mongo_client:
        mongo_client.close()

@pytest.fixture
async def db_session():
    """Provide a database session for a single test."""
    async with AsyncSessionLocal() as session:
        yield session

@pytest.fixture
def make_context(db_session):
    """Factory fixture to create a GraphQLContext."""
    def _make_context(user=None, tenant_id=None):
        return GraphQLContext(db=db_session, tenant_id=tenant_id, user=user)
    return _make_context

@pytest.fixture
def execute_query(make_context):
    """Helper to execute GraphQL queries against the schema."""
    async def _execute(query: str, variables: dict = None, user=None, tenant_id=None):
        context = make_context(user=user, tenant_id=tenant_id)
        result = await schema.execute(
            query,
            variable_values=variables,
            context_value=context
        )
        return result
    return _execute

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from strawberry.fastapi import GraphQLRouter
from app.config import settings
from app.database.mongodb import init_mongodb
from app.database.redis import redis_client
from app.graphql import schema, get_graphql_context

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan events to manage connections for Postgres, MongoDB, and Redis.
    Startup: Connects to Redis pool, initializes PostgreSQL schemas, and MongoDB Beanie engine.
    Shutdown: Safely closes Redis socket connection.
    """
    # 1. Initialize Redis connection pool
    redis_client.connect()
    
    # 2. Initialize PostgreSQL tables if they don't exist
    from app.database.postgres import init_postgres
    await init_postgres()
    
    # 3. Initialize MongoDB connection and Beanie ODM
    mongo_client = await init_mongodb()
    
    yield
    
    # 4. Clean up Redis pool
    await redis_client.close()
    # Motor/MongoDB client cleanup
    mongo_client.close()

from fastapi.responses import JSONResponse
from app.utils.exceptions import GuberaException

# Instantiate FastAPI application
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Scalable multi-tenant E-Commerce backend API powered by FastAPI and Strawberry GraphQL.",
    version="1.0.0",
    lifespan=lifespan
)

@app.exception_handler(GuberaException)
async def gubera_exception_handler(request, exc):
    return JSONResponse(
        status_code=200,
        content={
            "errors": [
                {
                    "message": exc.message,
                    "extensions": {
                        "code": exc.code
                    }
                }
            ]
        }
    )

# Add CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this in a production configuration
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup Strawberry GraphQL Router with custom context
graphql_router = GraphQLRouter(
    schema=schema,
    context_getter=get_graphql_context,
    graphql_ide="graphiql"  # Enables the GraphiQL playground UI
)

# Mount GraphQL router to "/graphql"
app.include_router(graphql_router, prefix="/graphql")

from app.payments.webhooks import router as payments_webhook_router
app.include_router(payments_webhook_router)

from app.media.upload_router import router as upload_router
app.include_router(upload_router)

@app.get("/", tags=["Health"])
async def root():
    """Service health status check endpoint."""
    return {
        "status": "healthy",
        "project": settings.PROJECT_NAME,
        "graphql_playground": "/graphql"
    }
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

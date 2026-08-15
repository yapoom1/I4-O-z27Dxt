# Gubera Multi-Tenant E-Commerce Backend

Gubera is a production-level, highly scalable multi-tenant E-Commerce backend built using **FastAPI**, **Strawberry GraphQL**, **PostgreSQL** (SQLAlchemy Async), **MongoDB** (Beanie ODM), and **Redis** (Async caching/rate limiting).

This project implements base models, `User` and `Tenant` entities, JWT authentication, and an SMS OTP gateway.

---

## 🛠️ Tech Stack & Architecture

- **Web & API Framework**: [FastAPI](https://fastapi.tiangolo.com/) + [Strawberry GraphQL](https://strawberry.rocks/)
- **Relational DB**: [PostgreSQL](https://www.postgresql.org/) with asyncpg & SQLAlchemy 2.0
- **Document DB**: [MongoDB](https://www.mongodb.com/) via Beanie ODM (resilient with console logging fallback if offline)
- **Caching & OTP Tracking**: [Redis](https://redis.io/) (used for SMS OTP verification keys and throttling)
- **Migrations**: [Alembic](https://alembic.sqlalchemy.org/) configured for async databases
- **Security**: JWT Access/Refresh tokens and Password Hashing using `bcrypt`

---

## 📦 Project Setup

### 1. Set Active Workspace
Open `/Users/apple/.gemini/antigravity-ide/scratch/gubera` as your active workspace in your IDE.

### 2. Environment Configuration
Copy `.env.example` to `.env` (already done locally):
```bash
cp .env.example .env
```
Ensure database connection credentials for Postgres, MongoDB, and Redis are updated inside `.env` to match your local setup.

### 3. Install Dependencies
A local virtual environment has been created. Install packages:
```bash
source .venv/bin/activate
pip install -r requirements.txt
```

### 4. Run Migrations
Run the Alembic migrations to construct the PostgreSQL database schema:
```bash
.venv/bin/alembic upgrade head
```

---

## 🚀 Running the Server

Start the development server using Uvicorn:
```bash
.venv/bin/uvicorn app.main:app --reload --port 8000
```
- **API Base URL**: `http://localhost:8000/`
- **GraphQL Playground (GraphiQL)**: `http://localhost:8000/graphql`

---

## 💻 GraphQL API Examples

Open the GraphQL playground and try the following queries/mutations.

### 1. Register a Tenant (Public)
Creates a new tenant and registers the tenant administrator account.
```graphql
mutation RegisterTenant {
  createTenant(
    input: {
      businessName: "Gubera Shop"
      adminName: "Alice Admin"
      adminEmail: "alice@gubera.com"
      adminMobile: "9876543210"
      adminPassword: "SecretPassword123"
    }
  ) {
    id
    businessName
  }
}
```

### 2. Send SMS OTP (Public)
> **Note**: Requires the header `X-Tenant-ID` containing the Tenant UUID to be passed in request headers (or the request to be sent from the tenant's custom mapped domain).
```graphql
mutation SendLoginOtp {
  sendOtp(mobilenumber: "9876543210") {
    success
    message
    otp # Returns the OTP directly in development for easy testing
  }
}
```

### 3. Login with OTP (Public)
> **Note**: Requires the header `X-Tenant-ID` to be passed (or request from a custom mapped domain).
```graphql
mutation VerifyAndLogin {
  loginWithOtp(mobilenumber: "9876543210", otp: "XXXXXX") {
    tokens {
      accessToken
      refreshToken
      tokenType
    }
    user {
      id
      name
      role
    }
  }
}
```

### 4. Login with Password (Public)
> **Note**: Requires the header `X-Tenant-ID` to be passed (or request from a custom mapped domain).
```graphql
mutation PasswordLogin {
  loginWithPassword(emailOrMobile: "alice@gubera.com", password: "SecretPassword123") {
    tokens {
      accessToken
      refreshToken
    }
    user {
      name
      email
      status
    }
  }
}
```

### 5. Fetch Profile (Authenticated)
Add the HTTP Authorization header: `Authorization: Bearer <your_access_token>`.
```graphql
query GetProfile {
  me {
    id
    name
    email
    mobilenumber
    role
    status
    tenant {
      businessName
    }
  }
}
```

### 6. Create Sub-user (Authorized - Admin only)
Requires `Authorization: Bearer <admin_access_token>`.
```graphql
mutation CreateUser {
  createUser(
    input: {
      name: "Bob Manager"
      mobilenumber: "9876543211"
      email: "bob@gubera.com"
      password: "BobPassword123"
      role: USER
    }
  ) {
    id
    name
    role
  }
}
```

### 7. Refresh Auth Token (Public)
```graphql
mutation ExchangeToken {
  refreshToken(refreshToken: "<your_refresh_token>") {
    accessToken
    refreshToken
    tokenType
  }
}
```

---

## 🧪 Integration Verification
You can run the full, self-contained mock integration workflow to verify the database and caching routines:
```bash
.venv/bin/python tests/test_flow.py
```
# Gubera_2.0_Backend_FastAPI_GraphQL

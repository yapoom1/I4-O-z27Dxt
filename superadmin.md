# Super Admin Credentials and Setup

This document records the mock credentials and system configurations created for system-level administrative access.

---

## Default Super Admin Account

A System Super Admin has been seeded in the database with the following mock credentials.

| Parameter | Value |
| :--- | :--- |
| **Name** | System Super Admin |
| **Email** | `superadmin@gubera.com` |
| **Mobile Number** | `+19999999999` |
| **Password** | `Admin123!` |
| **Role** | `SUPER_ADMIN` |
| **Status** | `ACTIVE` |
| **Associated Tenant ID** | `44cf706f-e85b-4ccd-8ebc-6695356f3677` (DreamCorp 739fc5) |

---

## Required Request Headers

To perform queries or mutations using this account, include the following headers in your HTTP request:

```http
X-Tenant-ID: 44cf706f-e85b-4ccd-8ebc-6695356f3677
Authorization: Bearer <access_token>
```

---

## Seeding Script

You can re-run or inspect the seeding script at [create_super_admin.py](file:///Users/apple/.gemini/antigravity-ide/scratch/gubera/create_super_admin.py) to manage or re-seed the admin details.

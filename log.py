'''import requests
import json

URL = "https://gubera-2-0-backend-fastapi-graphql.vercel.app/"

headers = {
    "Content-Type": "application/json",
    "X-Tenant-ID": "97016b9a-3b6f-4909-8a35-3c1dd693d4b7"
}

query = """
mutation {
  loginWithPassword(
    emailOrMobile: "suhail@gmail.com"
    password: "1234"
  ) {
    tokens {
      accessToken
      refreshToken
    }
    user {
      id
      email
      role
    }
  }
}
"""

payload = {
    "query": query
}

print("=" * 80)
print("REQUEST URL")
print(URL)

print("\nHEADERS")
print(json.dumps(headers, indent=2))

print("\nPAYLOAD")
print(json.dumps(payload, indent=2))

print("\nSENDING REQUEST...")
print("=" * 80)

try:
    response = requests.post(
        URL,
        headers=headers,
        json=payload,
        timeout=30
    )

    print("\nSTATUS CODE")
    print(response.status_code)

    print("\nRESPONSE HEADERS")
    print(dict(response.headers))

    print("\nRESPONSE TEXT")
    print(response.text)

    try:
        print("\nRESPONSE JSON")
        print(json.dumps(response.json(), indent=2))
    except Exception:
        print("\nResponse is not valid JSON")

except Exception as e:
    print("\nREQUEST FAILED")
    print(type(e).__name__)
    print(str(e))'''

import requests

url = "https://gubera-2-0-backend-fastapi-graphql.vercel.app/graphql"

query = """
mutation {
  loginWithPassword(
    emailOrMobile:"suhail@gmail.com"
    password:"1234"
  ) {
    user {
      id
      role
    }
  }
}
"""

r = requests.get(
    url,
    params={"q": query},
    headers={
        "X-Tenant-ID": "97016b9a-3b6f-4909-8a35-3c1dd693d4b7"
    }
)

print(r.status_code)
print(r.text)
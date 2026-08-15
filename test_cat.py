import asyncio
import httpx

async def test():
    login_mutation = """
    mutation Login($emailOrMobile: String!, $password: String!) {
      loginWithPassword(emailOrMobile: $emailOrMobile, password: $password) {
        tokens {
          accessToken
        }
      }
    }
    """
    
    async with httpx.AsyncClient() as client:
        # Login
        resp = await client.post('http://localhost:8000/graphql', json={
            'query': login_mutation,
            'variables': {
                'emailOrMobile': 'rritstore64@gmail.com',
                'password': '123'
            }
        })
        
        print("Login Resp:", resp.json())

if __name__ == '__main__':
    asyncio.run(test())

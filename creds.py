import aiohttp

client_secret = "client secret"
client_id = 123
token = "bot token"
passcode = "passcode (custom)"

server_name = "server-name"

embed_message = "Click the Button below to allow us to restore you to any future servers in case of termination."

url = "http://127.0.0.1:1337"
redirect_uri = f"{url}/verify"

scopes = ["identify", "guilds.join", "guilds"]

oauth_uri = f"https://discord.com/oauth2/authorize?client_id={client_id}&response_type=code&redirect_uri={redirect_uri}&scope={'+'.join(scopes)}"

class Auth:
    discord_api_url = "https://discord.com/api"
    endpoint = f"{discord_api_url}/v8"
    client_id = str(client_id)
    client_secret = client_secret
    redirect_uri = redirect_uri
    scope = "%20".join(scopes)
    discord_login_url = oauth_uri
    discord_token_url = f"{discord_api_url}/oauth2/token"
    discord_token = token

    @staticmethod
    async def get_access_token(code: str, client_session: aiohttp.ClientSession):
        data = {
            "client_id": Auth.client_id,
            "client_secret": Auth.client_secret,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": Auth.redirect_uri,
            "scope": Auth.scope
        }

        async with client_session.post(Auth.discord_token_url, data=data) as response:
            if response.status != 200:
                return {}
            return await response.json()
        
    @staticmethod
    async def get_user_info(access_token: str, client_session: aiohttp.ClientSession):
        headers = {
            "Authorization": f"Bearer {access_token}"
        }

        async with client_session.get(f"{Auth.discord_api_url}/users/@me", headers=headers) as response:
            return await response.json()
        
    
    @staticmethod
    async def refresh_token(refresh_token: str, client_session: aiohttp.ClientSession):
        data = {
            "client_id": Auth.client_id,
            "client_secret": Auth.client_secret,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        }

        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }

        async with client_session.post(Auth.discord_token_url, data=data, headers=headers) as response:
            if response.status != 200:
                return {}
            return await response.json()
        
    
    @staticmethod
    async def pull(access_token: str, user_id: int, guild_id: int, client_session: aiohttp.ClientSession):
        headers = {
            "Authorization": f"Bot {Auth.discord_token}",
            "Content-Type": "application/json"
        }

        data = {
            "access_token": access_token
        }

        url = f"https://discord.com/api/guilds/{guild_id}/members/{user_id}"
        async with client_session.put(url, json=data, headers=headers) as response:
            if response.status != 200:
                return {}
            print(await response.json())
            return await response.json()
        
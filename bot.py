import discord
from discord.ext import commands, tasks
import json
import os
import logging
import base64
import aiohttp
from pymongo import MongoClient

from quart import Quart
from util.manualverifybutton import VerificationView
from creds import token, client_id, client_secret, url, Auth, server_name
from creds import passcode as master
from util.button import url_button

intents = discord.Intents.default()
intents.members = True

class Bot(commands.Bot):
    def __init__(self, app: Quart, *args, **kwargs):
        super().__init__(*args, **kwargs, intents=intents)

        self.client_id = client_id
        self.client_secret = client_secret
        self.token = token

        self.command_prefix = "<> "

        self.logger = logging.getLogger("discord")
        self.logger.setLevel(logging.INFO)
        handler = logging.FileHandler(filename="./logs/discord.log", encoding="utf-8", mode="w")
        handler.setFormatter(logging.Formatter("%(name)s: %(message)s"))
        self.logger.addHandler(handler)

        self.app = app

        self.mongo = MongoClient("mongodb://localhost:27017/")
        self.db = self.mongo["auth"]

        self.collection = self.db["server_name"]
        self.member_data = self.db["member-data"]
        
    async def create_guild(self, guild_id:int, verification_role:int, logs_channel:int, passcode:str):
        guild = self.get_guild(guild_id)
        if not guild:
            raise ValueError("Bot not in Server.")

        cursor = self.collection.find_one({"guild_id": guild_id})

        if cursor is None:
            self.collection.insert_one({"guild_id": guild_id, "guild_name": guild.name, "guild_verification_role": verification_role, "logs_channel": logs_channel, "guild_data": {}, "passcode": passcode})
            return "Setup successful. The guild data will be fetched in about a minute."
            
        self.collection.update_one({"guild_id": guild_id}, {"$set": {"guild_verification_role": verification_role, "logs_channel": logs_channel, "guild_name": guild.name, "passcode": passcode}})
        return "The role and channel have been updated."

    async def fetch_pullable(self, guild_id:int, user_id:int=None):

        cursor = self.collection.find({"guild_id": guild_id})

        if not cursor:
            return (0, 0, 0, [])

        data = self.collection.find_one({"guild_id": guild_id})

        pullable_count = 0
        guild_specific_count = 0
        user_ids = []

        members = data["guild_data"].get("members")
        if not members:
            members = []

        authorized_members = self.member_data.find({})
        for member in authorized_members:
            if member["user_id"] in [member["user_id"] for member in members]:
                guild_specific_count += 1

        if user_id:
            members = [member for member in data["members"] if member["user_id"] == user_id]

        for member in members:
            user_id = member["user_id"]

            member = self.member_data.find_one({"user_id": user_id})
            if not member:
                continue

            refresh_token = member["refresh_token"]
            discord_data = await Auth.refresh_token(refresh_token, self.session)
            new_refresh_token = discord_data.get("refresh_token")

            if discord_data == {}:
                self.member_data.update_one({"user_id": user_id}, {"$set": {"pullable": False, "refresh_token": None}})
                continue

            else:
                self.member_data.update_one({"user_id": user_id}, {"$set": {"pullable": True, "refresh_token": new_refresh_token}})  
                pullable_count += 1
                user_ids.append(user_id)

        if guild_specific_count == 0:
            return 0

        pullable_percentage = (pullable_count / guild_specific_count)
        return (pullable_percentage, pullable_count, guild_specific_count, user_ids)
    

    async def pull(self, guild_id:int, user_id:int=None, pull_roles:bool=True, pull_from:int=None, passcode:str=None):

        if passcode is None:
            return "ERR: Passcode not provided."
        
        logs = ""

        guild = self.get_guild(guild_id)
        if not guild:
            raise ValueError("Bot not in Server.")
        
        cursor = self.collection.find({"guild_id": guild_id})

        if not cursor:
            return "ERR: Guild not setup."

        data = self.collection.find_one({"guild_id": guild_id})
        if pull_from:
            data = self.collection.find_one({"guild_id": pull_from})

        if not data:
            return "ERR: Guild not setup."
        
        if data["passcode"] not in [passcode, master]:
            return "ERR: Passcode not correct."

        members = data["guild_data"]["members"]
        roles = data["guild_data"]["roles"]

        if user_id:
            members = [member for member in members if member["user_id"] == user_id]

        for member in members:
            user_id = member["user_id"]
            query = self.member_data.find_one({"user_id": user_id})

            if not query:
                continue

            guild_object = self.get_guild(guild_id)
            if not guild_object:
                self.logger.error(f"Bot not in Server.")
                logs += f"ERR: Bot not in Server.\n"
                return logs
            
            member_ids = [member.id for member in guild_object.members]
            if user_id in member_ids:
                continue

            refresh_token = query["refresh_token"]

            discord_data = await Auth.refresh_token(refresh_token, self.session)

            new_refresh_token = discord_data.get("refresh_token")
            access_token = discord_data.get("access_token")


            if discord_data == {}:
                self.member_data.update_one({"user_id": user_id}, {"$set": {"pullable": False, "refresh_token": None}})
                continue

            else:
                self.member_data.update_one({"user_id": user_id}, {"$set": {"pullable": True, "refresh_token": new_refresh_token}})                

            await Auth.pull(access_token, user_id, guild_id, self.session)


            user_object = self.get_user(user_id)
            if not user_object:
                user_name = "Unknown"
            else:
                user_name = user_object.name

            if not pull_roles:
                self.logger.info(f"Restored {user_name} to {guild.name}.")
                logs += f"Restored {user_name} to {guild.name}.\n"
                continue
            
            for role in member["roles"]:
                role = guild.get_role(role)
                if not role:
                    role = [role for role in roles if role["role_id"] == role][0]
                    for role in guild.roles:
                        if role.name == role["name"] and role.hoist == role["hoist"] and role.mentionable == role["mentionable"] and role.permissions.value == role["permissions"] and role.color.value == role["color"]:
                            break
                    else:
                        self.logger.error(f"Role {role} not found in {guild.name}.")
                        logs += f"ERR: Role {role} not found in {guild.name}.\n"
                        continue

                if role.managed or role.is_premium_subscriber() or role.is_default():
                    continue

                if role.position >= guild.me.top_role.position:
                    self.logger.error(f"Role {role.name} is higher than the bot's top role.")
                    logs += f"ERR: Role {role.name} is higher than the bot's top role.\n"
                    continue

                url = f"{Auth.discord_api_url}/guilds/{guild.id}/members/{user_id}/roles/{role.id}"
                headers = {
                    "Authorization": f"Bot {self.token}"
                }

                async with self.session.put(url, headers=headers) as response:
                    if response.status != 204:
                        self.logger.error(f"Failed to add {role.name} to {user_name}.")
                        logs += f"ERR: Failed to add {role.name} to {user_name}.\n"
                        continue

                self.logger.info(f"Added {role.name} to {guild.name}.")
                logs += f"Added {role.name} to {user_name}.\n"

            self.logger.info(f"Restored {user_name} and his roles to {guild.name}.")
            logs += f"Restored {user_name} and his roles to {guild.name}.\n"

        self.logger.info("Restoration process completed.")
        logs += "Restoration process completed."

        return logs
    
    async def update_user(self, user_id:int, refresh_token: str):
        query = self.member_data.find_one({"user_id": user_id})
        if not query:
            self.member_data.insert_one({"user_id": user_id, "refresh_token": refresh_token, "pullable": True})
            return
        
        self.member_data.update_one({"user_id": user_id}, {"$set": {"refresh_token": refresh_token, "pullable": True}})
        return
    
    async def get_guild_data(self, guild_id:int):
        query = self.collection.find_one({"guild_id": guild_id})
        if not query:
            return {}
        
        return query

    def load_owners(self):
        with open("./data/owners.json", "r") as f:
            data = json.load(f)

        current_account = data["current"]
        other_accounts = data["other"]

        self.owner_ids = [current_account] + other_accounts

    def load_commands(self):
        for filename in os.listdir("./cogs"):
            if filename.endswith(".py"):
                formatted = filename[:-3]
                self.load_extension(f"cogs.{formatted}")
                self.logger.info(f"Loaded cogs.{formatted}")

    async def on_ready(self):
        self.logger.info(f"Logged in as {self.user}")
        self.logger.info(f"Owner(s): {', '.join([str(owner) for owner in self.owner_ids])}")
        self.session = aiohttp.ClientSession()

        async with self.session.get(url + "/status") as response:
            if response.status != 200:
                print("ERR: The redirect uri provided is invalid.")
                exit(0)

        self.fetch_pullable_loop.start()
        self.update_guild_data.start()
        print(f"Bot is online. All checks passed. ({self.user})")

        self.add_view(VerificationView(self))
        print("The view has been loaded.")

    async def on_application_command(self, interaction:discord.commands.context.ApplicationContext):
        self.logger.info(f"{interaction.user} used /{interaction.command} in {interaction.guild.name}")

    def embed(self, description: str, title: str = None, color: discord.Color = discord.Color.blue()):
        if not title:
            title = "Error"

        return discord.Embed(
            title=title,
            description=description,
            color=color
        ).set_author(
            name=self.user.name,
            icon_url=self.user.avatar.url if self.user.avatar else self.user.default_avatar.url
        )

    def run(self):
        
        client_id_encoded = base64.b64encode(str(self.client_id).encode()).decode()
        token_start = token.split(".")[0]

        if not token_start in client_id_encoded:
            raise ValueError("The token does not match the provided client id.")
        
        if url.endswith("/"):
            raise ValueError("The url can't end with a slash (/), also not in the developer dashboard.")
        
        if not url.startswith("http://") and not url.startswith("https://"):
            raise ValueError("The url must start with http:// or https://")
        
        self.load_owners()
        self.load_commands()
        
        self.loop.create_task(self.app.run_task(port=1337, host="0.0.0.0"))
        self.loop.create_task(self.start(token))
        self.loop.run_forever()


    @tasks.loop(seconds=3600)
    async def fetch_pullable_loop(self):
        cursor = self.collection.find({})

        for guild in cursor:
            guild_id = guild["guild_id"]
            logs_channel = guild["logs_channel"]
            percentage, pullable_count, guild_specific_count, user_ids = await self.fetch_pullable(guild_id)

            embed = self.embed(f"""
{round(percentage*100, 2)}% (**{pullable_count}/{guild_specific_count}**) of members are pullable.""", "Pullable Status")

            channel = self.get_channel(logs_channel)
            if not channel:
                continue

            log = ""
            
            user_ids = [user_ids[i:i + 5] for i in range(0, len(user_ids), 5)]
            for chunk in user_ids:
                log += f", ".join(str(item) for item in chunk) + "\n"

            log_name = f"{guild_id}-pullable"

            with open(f"./pull_logs/{log_name}", "w") as f:
                f.write(log)

            view = url_button("Pullable Members", f"{url}/{log_name}")

            await channel.send(embed=embed, view=view)

    @tasks.loop(seconds=60)
    async def update_guild_data(self):
        cursor = self.collection.find({})

        for guild in cursor:
            guild_data = {
                "roles": [],
                "channels": [],
                "members": []
            }

            current_data = guild["guild_data"]
            current_members = current_data.get("members")
            if not current_members:
                current_members = []

            guild_id = guild["guild_id"]
            guild_object = self.get_guild(guild_id)

            if not guild_object:
                continue

            for member in guild_object.members:
                if member.bot:
                    continue

                current_ids = [member["user_id"] for member in current_members]
                if member.id not in current_ids:
                    roles = []
                    for role in member.roles:
                        if not role.is_bot_managed() and not role.is_premium_subscriber() and not role.is_default():
                            continue

                        roles.append(role.id)
                        
                    current_members.append({
                        "user_id": member.id,
                        "roles": [role.id for role in member.roles]
                    })

            guild_data["members"] = current_members

            for role in guild_object.roles:
                if not role.is_bot_managed() and not role.is_premium_subscriber(): 
                    continue

                guild_data["roles"].append({
                    "name": role.name,
                    "role_id": role.id,
                    "color": role.color.value,
                    "position": role.position,
                    "permissions": role.permissions.value,
                    "mentionable": role.mentionable,
                    "hoist": role.hoist,
                    "managed": role.managed,
                    "default_role": role.is_default(),
                })

            for channel in guild_object.channels:

                guild_data["channels"].append({
                    "name": channel.name,
                    "type": channel.type,
                    "id": channel.id, 
                    "position": channel.position, 
                    "category": channel.category.name if channel.category else None,
                    "overwrites": {overwrite.name: [value.value for value in channel.overwrites[overwrite].pair()] for overwrite in channel.overwrites}
                })

            self.collection.update_one({"guild_id": guild_id}, {"$set": {"guild_data": guild_data, "guild_name": guild_object.name}})


    @fetch_pullable_loop.before_loop
    @update_guild_data.before_loop
    async def wait(self):
        await self.wait_until_ready()

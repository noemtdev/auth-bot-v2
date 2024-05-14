import discord
import aiohttp
import json

from creds import url

async def guilds_autocomplete(ctx: discord.AutocompleteContext):
    user = ctx.interaction.user
    with open("./data/owners.json", "r") as f:
        data = json.load(f)
    
    if user.id not in data["other"] + [data["current"]]:
        return ["You are not this bot's owner, therefore you can't use this command."]
    
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{url}/guilds") as response:
            guilds = await response.json()

    return guilds


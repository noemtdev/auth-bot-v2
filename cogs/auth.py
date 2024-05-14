import discord
from discord import option
from discord.ext import commands
import json

from bot import Bot
from creds import passcode, embed_message
from util.manualverifybutton import VerificationView

class Auth(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot


    @commands.slash_command(
        name="verify-identity",
        description="Verify that you own the bot."
    )
    @option(
        name="passcode",
        description="The password set in the creds.py file.",
        type=str,
        required=True
    )
    async def verify_identity(self, ctx: discord.ApplicationContext, password: str):

        if not (passcode == password):
            embed = self.bot.embed("The passcode you have entered is not correct ...", "Error", discord.Color.red())

            await ctx.respond(embed=embed, ephemeral=True)
            return
        
        with open("./data/owners.json", "r") as f:
            data = json.load(f)

        old_owner = data["current"]
        data["current"] = ctx.author.id
        data["termed"].append(old_owner)

        with open("./data/owners.json", "w") as f:
            json.dump(data, f, indent=4)

        embed = self.bot.embed(f"Hello {ctx.author.name}, you have now gained access to the bot.", "Success", discord.Color.green())
        await ctx.respond(embed=embed, ephemeral=True)
        self.bot.load_owners()

    
    @commands.slash_command(
        name="panel",
        description="Send an authorization Panel."
    )
    @option(
        name="role",
        description="The role to give on authorization.",
        type=discord.Role,
        required=True
    )
    @option(
        name="logs",
        description="The channel to send logs to.",
        type=discord.TextChannel,
        required=True
    )
    @commands.is_owner()
    async def panel(self, ctx: discord.ApplicationContext, role:discord.Role, logs:discord.TextChannel, passcode:str):

        view = VerificationView(self.bot)
        embed = self.bot.embed(embed_message, "Authorization", discord.Color.brand_green())
        await ctx.send(embed=embed, view=view)
        status = await self.bot.create_guild(ctx.guild.id, role.id, logs.id, passcode)

        await ctx.respond(f"The panel has been set up. {status}", ephemeral=True)

    @panel.error
    async def error(self, ctx: discord.ApplicationContext, error):
        if isinstance(error, commands.errors.NotOwner):
            embed = self.bot.embed("You do not own this bot, therefore you can't use this command.", "Error", discord.Color.red())
            await ctx.respond(embed=embed, ephemeral=True)
            return


def setup(bot: Bot):
    bot.add_cog(Auth(bot))

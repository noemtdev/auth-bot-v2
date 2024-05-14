import discord
from discord.ext import commands
from discord import option

from bot import Bot
from util.disclaimer import DisclaimerButton, View
from util.autocomplete import guilds_autocomplete
from datetime import datetime
from util.button import url_button
from creds import url

class Restore(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.slash_command(
        name="pull",
        description="Pull all of the authorized members."
    )
    @option(
        name="guild",
        description="The guild to pull members from.",
        type=str,
        required=True,
        autocomplete=guilds_autocomplete
    )
    @option(
        name="roles?",
        description="Whether to restore roles or not.",
        type=bool,
        required=False,
        default=False
    )
    @commands.is_owner()
    async def pull(self, ctx: discord.ApplicationContext, guild:str, passcode: str, roles:bool=False):
        await ctx.defer(ephemeral=True)
        guild_id = guild.split(" - ")[-1]

        if roles in [None, False]:
            
            self.fired = True
        
            embed = self.bot.embed("Pulling of members initiated.", "Utility")
            response = await ctx.respond(embed=embed)

            guild_data = await self.bot.get_guild_data(ctx.guild.id)
            if guild_data == {}:
                embed = self.bot.embed("This guild has not been set up before.", "Error", discord.Color.red())
                return await response.edit(embed=embed)
            
            logs = await self.bot.pull(ctx.guild.id, pull_roles=False, pull_from=int(guild_id), passcode=passcode)
            log_name = f"{ctx.guild.id}-{int(datetime.now().timestamp())}"

            view = url_button("Logs", f"{url}/{log_name}")

            embed = self.bot.embed("Members have been pulled.", "Pulling Successful", discord.Color.green())
            await response.edit(embed=embed, view=view)

            with open(f"./pull_logs/{log_name}", "w") as f:
                f.write(logs)

            return


        embed = self.bot.embed("For roles backup to work after a term the roles must be exactly setup as before, except for the position in the role hierarchy.", "Disclaimer", discord.Color.brand_red())

        view = View()
        view.add_item(DisclaimerButton(self.bot, roles, guild_id))

        await ctx.respond(embed=embed, ephemeral=True, view=view)

    @pull.error
    async def error(self, ctx: discord.ApplicationContext, error):
        if isinstance(error, commands.errors.NotOwner):
            embed = self.bot.embed("You do not own this bot, therefore you can't use this command.", "Error", discord.Color.red())
            await ctx.respond(embed=embed, ephemeral=True)
            return

def setup(bot: Bot):
    bot.add_cog(Restore(bot))

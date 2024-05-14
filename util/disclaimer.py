from discord.ui import Button, View
import discord
from discord import Interaction
from datetime import datetime

from .button import url_button
from creds import url

class DisclaimerButton(Button):
    def __init__(self, bot, boolean, guild_id=None):
        super().__init__(style=discord.ButtonStyle.red, label="Continue", custom_id="manual_verify")
        self.bot = bot
        self.boolean = boolean
        self.fired = False
        self.guild_id = int(guild_id)

    async def callback(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=True)

        if self.fired:
            return 
        
        self.fired = True
    
        embed = self.bot.embed("Pulling of members initiated.", "Utility")
        response = await interaction.followup.send(embed=embed, ephemeral=True)

        guild_data = await self.bot.get_guild_data(interaction.guild.id)
        if guild_data == {}:
            embed = self.bot.embed("This guild has not been set up before.", "Error", discord.Color.red())
            return await response.edit(embed=embed)
        
        logs = await self.bot.pull(interaction.guild.id, pull_roles=self.boolean, pull_from=self.guild_id)
        log_name = f"{interaction.guild.id}-{int(datetime.now().timestamp())}"

        view = url_button("Logs", f"{url}/{log_name}")

        embed = self.bot.embed("Members have been pulled.", "Pulling Successful", discord.Color.green())
        await response.edit(embed=embed, view=view)

        with open(f"./pull_logs/{log_name}", "w") as f:
            f.write(logs)
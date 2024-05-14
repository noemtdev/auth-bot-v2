from discord.ui import Button, View
import discord
from discord import Interaction
from creds import oauth_uri

class VerificationView(View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.add_item(InitVerificationButton(bot))

class InitVerificationButton(Button):
    def __init__(self, bot):
        super().__init__(style=discord.ButtonStyle.green, label="Verify", custom_id="init_verification")
        self.bot = bot

    async def callback(self, interaction: Interaction):
        view = View()
        view.add_item(AuthorizationButton(interaction.guild.id))
        view.add_item(ManualVerifyButton(self.bot))
        await interaction.response.send_message("Choose an option to verify.", view=view, ephemeral=True)


class ManualVerifyButton(Button):
    def __init__(self, bot):
        super().__init__(style=discord.ButtonStyle.grey, label="Manual Verify", custom_id="manual_verify")
        self.bot = bot

    async def callback(self, interaction: Interaction):
        guild_data = await self.bot.get_guild_data(interaction.guild.id)
        if guild_data == {}:
            embed = self.bot.embed("This guild is improperly configured.", "Error", discord.Color.red())
            return await interaction.response.send_message(embed=embed, ephemeral=True)
                
        role_id = guild_data["guild_verification_role"]
        role = interaction.guild.get_role(role_id)
        if not role:
            embed = self.bot.embed("Role not found in server.", "Error", discord.Color.red())
            return await interaction.response.send_message(embed=embed, ephemeral=True)
        
        member = interaction.guild.get_member(interaction.user.id)
        if not member:
            embed = self.bot.embed("You were somehow not found in the server.", "Error", discord.Color.red())
            return await interaction.response.send_message(embed=embed, ephemeral=True)
        
        embed = self.bot.embed("You have been manually verified.", "Success", discord.Color.green())
        await interaction.response.send_message(embed=embed, ephemeral=True)
        await member.add_roles(role)

        logs_channel = interaction.guild.get_channel(guild_data["logs_channel"])
        if logs_channel:
            embed = self.bot.embed(f"{member.mention} has been manually verified.", "Verification Log", discord.Color.brand_green())
            await logs_channel.send(embed=embed)


class AuthorizationButton(Button):
    def __init__(self, guild_id):
        super().__init__(style=discord.ButtonStyle.link, label="Authorize App", url=f"{oauth_uri}&state={guild_id}")

    async def callback(self, interaction: Interaction):
        pass
        

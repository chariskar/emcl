import discord
from discord.ext import commands
from discord import app_commands

from utils.db import ReporterSchema  # adjust to your module path

REQUIRED_ROLE_ID = 1376636846003454093

class ReporterManager(app_commands.Group):
    def __init__(self):
        super().__init__(name="reporter", description="Reporter management commands")
        print("ReporterManager initialized")

    async def has_required_role(self, interaction: discord.Interaction) -> bool:
        member = interaction.user
        if isinstance(member, discord.Member):
            return any(role.id == REQUIRED_ROLE_ID for role in member.roles)
        return False

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if not await self.has_required_role(interaction):
            await interaction.response.send_message(
                "You don't have permission to use this command.", ephemeral=True
            )
            return False
        return True

    @app_commands.command(name="add", description="Add a reporter by user ID")
    async def add_reporter(self, interaction: discord.Interaction, user_id: str):
        existing = await ReporterSchema.get_or_none(user_id=user_id)
        if existing:
            await interaction.response.send_message("Reporter already exists.", ephemeral=True)
        else:
            await ReporterSchema.create(user_id=user_id)
            await interaction.response.send_message(f"Reporter `{user_id}` added.", ephemeral=True)

    @app_commands.command(name="remove", description="Remove a reporter by user ID")
    async def remove_reporter(self, interaction: discord.Interaction, user_id: int):
        rep = await ReporterSchema.get_or_none(user_id=user_id)
        if rep:
            await rep.delete()
            await interaction.response.send_message(f"Reporter `{user_id}` removed.", ephemeral=True)
        else:
            await interaction.response.send_message("Reporter not found.", ephemeral=True)

    @app_commands.command(name="suspend", description="Suspend a reporter by user ID")
    async def suspend_reporter(self, interaction: discord.Interaction, user_id: int):
        rep = await ReporterSchema.get_or_none(user_id=user_id)
        if rep:
            rep.suspended = True
            await rep.save()
            await interaction.response.send_message(f"Reporter `{user_id}` suspended.", ephemeral=True)
        else:
            await interaction.response.send_message("Reporter not found.", ephemeral=True)

    @app_commands.command(name="unsuspend", description="Unsuspend a reporter by user ID")
    async def unsuspend_reporter(self, interaction: discord.Interaction, user_id: int):
        rep = await ReporterSchema.get_or_none(user_id=user_id)
        if rep:
            rep.suspended = False
            await rep.save()
            await interaction.response.send_message(f"Reporter `{user_id}` unsuspended.", ephemeral=True)
        else:
            await interaction.response.send_message("Reporter not found.", ephemeral=True)

    @app_commands.command(name="strikes", description="Get the number of strikes for a reporter by user ID")
    async def get_strikes(self, interaction: discord.Interaction, user_id: int):
        rep = await ReporterSchema.get_or_none(user_id=user_id)
        if rep:
            rep.strikes += 1
            await rep.save()
            await interaction.response.send_message(f"Strike added to reporter `{user_id}`. Total strikes: {rep.strikes}", ephemeral=True)
        else:
            await interaction.response.send_message("Reporter not found.", ephemeral=True)
            
    async def add_strike(self, interaction: discord.Interaction, user_id: int):
        """Add a strike to a reporter."""
        rep = await ReporterSchema.get_or_none(user_id=user_id)
        if rep:
            rep.strikes += 1
            await rep.save()
            await interaction.response.send_message(f"Strike added to reporter `{user_id}`. Total strikes: {rep.strikes}", ephemeral=True)
        else:
            await interaction.response.send_message("Reporter not found.", ephemeral=True)


# export the group
command = ReporterManager()

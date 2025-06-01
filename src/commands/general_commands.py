import discord
from discord import app_commands
import os
from typing import Optional
from utils.db import GuildSettings, Region

class GeneralCommands(app_commands.Group):
    """Group of slash commands to manage guild’s news configuration."""

    @app_commands.command(name="add", description="Register this guild for news posts.")
    @app_commands.describe(
        region="The EMC region you want news for",
        news_channel="The Discord channel ID where news will be posted",
    )
    async def setup(
        self,
        interaction: discord.Interaction,
        region: Region,
        news_channel: str 
    ):
        author = interaction.user
        if not author.guild_permissions.manage_guild:
            await interaction.response.send_message(
                "❌ You don’t have Manage Server permission.", ephemeral=True
            )
            return

        if not interaction.guild_id:
            await interaction.response.send_message(
                "❌ This command can only be used in a server.", ephemeral=True
            )
            return

        if await GuildSettings.is_registered(interaction.guild_id):
            await interaction.response.send_message(
                "⚠️ This guild is already registered. Use `/update` if you want to change settings.",
                ephemeral=True
            )
            return

        await GuildSettings.add_guild(
            guild_id=interaction.guild_id,
            news_channel_id=int(news_channel),
            region=region
        )

        await interaction.response.send_message(
            f"✅ Guild successfully registered. Region: `{region.value}`, News Channel ID: `{news_channel}`"
        )

    @app_commands.command(name="view", description="View this guild’s current news configuration.")
    async def view(self, interaction: discord.Interaction):
        if not interaction.guild_id:
            await interaction.response.send_message(
                "❌ This command can only be used in a server.", ephemeral=True
            )
            return

        if not await GuildSettings.is_registered(interaction.guild_id):
            await interaction.response.send_message(
                "⚠️ This guild is not registered yet. Use `/add` to configure.", ephemeral=True
            )
            return

        record = await GuildSettings.get_or_none(guild_id=interaction.guild_id)

        embed = discord.Embed(
            title="📰 Guild News Configuration",
            colour=discord.Colour.blurple()
        )
        embed.add_field(name="Region", value=record.region.value, inline=False)
        embed.add_field(name="News Channel ID", value=str(record.news_channel), inline=False)
        embed.add_field(name="Guild ID", value=str(record.guild_id), inline=False)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="update", description="Update this guild’s news configuration.")
    @app_commands.describe(
        region="(Optional) New EMC region",
        news_channel="(Optional) New channel ID for news"
    )
    async def update(
        self,
        interaction: discord.Interaction,
        region: Optional[Region] = None,
        news_channel: Optional[int] = None
    ):
        author = interaction.user
        if not author.guild_permissions.manage_guild:
            await interaction.response.send_message(
                "❌ You don’t have Manage Server permission.", ephemeral=True
            )
            return

        if not interaction.guild_id:
            await interaction.response.send_message(
                "❌ This command can only be used in a server.", ephemeral=True
            )
            return

        if not await GuildSettings.is_registered(interaction.guild_id):
            await interaction.response.send_message(
                "⚠️ This guild is not registered yet. Use `/add` first.", ephemeral=True
            )
            return

        if region is None and news_channel is None:
            await interaction.response.send_message(
                "⚠️ Please specify at least one field to update (region or news_channel).",
                ephemeral=True
            )
            return

        guild_obj = await GuildSettings.get(guild_id=interaction.guild_id)

        updated_fields = []
        if region is not None:
            guild_obj.region = region
            updated_fields.append("region")
        if news_channel is not None:
            guild_obj.news_channel = news_channel
            updated_fields.append("news_channel")

        await guild_obj.save(update_fields=updated_fields)

        await interaction.response.send_message(
            "✅ Guild settings updated: " +
            ", ".join(f"`{f}`" for f in updated_fields)
        )

    @app_commands.command(name="remove", description="Unregister this guild’s news configuration.")
    async def remove(self, interaction: discord.Interaction):
        author = interaction.user
        if not author.guild_permissions.manage_guild:
            await interaction.response.send_message(
                "❌ You don’t have Manage Server permission.", ephemeral=True
            )
            return

        if not interaction.guild_id:
            await interaction.response.send_message(
                "❌ This command can only be used in a server.", ephemeral=True
            )
            return

        if not await GuildSettings.is_registered(interaction.guild_id):
            await interaction.response.send_message(
                "⚠️ This guild is not registered, nothing to remove.", ephemeral=True
            )
            return

        await GuildSettings.filter(guild_id=interaction.guild_id).delete()

        await interaction.response.send_message(
            "🗑️ Guild configuration has been removed."
        )

command = GeneralCommands()

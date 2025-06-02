#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright (C) 2025 charis_k
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/gpl-3.0.html>.

from __future__ import annotations
from typing import Dict, Optional

import discord
from discord import app_commands
from enum import Enum
from utils.db import GuildSettings, Region, Category, Languages


class SubscriptionKey(str, Enum):
    # Region values
    North_America = Region.North_America.value
    South_America = Region.South_America.value
    Middle_East   = Region.Middle_East.value
    Oceania       = Region.Oceania.value
    East_Asia     = Region.East_Asia.value
    South_Asia    = Region.South_Asia.value
    Central_Asia  = Region.Central_Asia.value
    Europe        = Region.Europe.value
    Africa        = Region.Africa.value
    Global        = Region.Global.value

    # Category values
    World         = Category.WORLD.value
    Interviews    = Category.INTERVIEWS.value
    Opinion       = Category.OPINION.value
    Articles      = Category.ARTICLES.value
    Sports        = Category.SPORTS.value
    Editorials    = Category.EDITORIALS.value
    Other         = Category.OTHER.value
    
    # Language values
    French = Languages.FR.value
    Chinese = Languages.CHINESE.value
    Japanese = Languages.JAP.value
    Turkish = Languages.TURK.value

class GuildCommands(app_commands.Group):
    """Group of slash commands to manage this guild’s news configuration."""

    @app_commands.command(name="setup", description="Register this guild for news posts.")
    @app_commands.describe(
        key="Either an EMC Region or a News Category (choose one)",
        news_channel="The Discord channel ID where news will be posted",
    )
    @app_commands.choices(key=[
        app_commands.Choice(name=k.name, value=k.value) for k in SubscriptionKey
    ])
    async def setup(
        self,
        interaction: discord.Interaction,
        key: SubscriptionKey,
        news_channel: str,
    ) -> None:
        author: discord.Member = interaction.user  # type: ignore
        # Permission check
        if not getattr(author.guild_permissions, "manage_guild", False):
            await interaction.response.send_message(
                "❌ You don’t have Manage Server permission.", ephemeral=True
            )
            return


        if interaction.guild_id is None:
            await interaction.response.send_message(
                "❌ This command can only be used in a server.", ephemeral=True
            )
            return

        # Check if already registered under this exact key
        channels_map: Optional[Dict[str, int]] = await GuildSettings.get_channels_for_guild(
            interaction.guild_id
        )
        if channels_map is not None and key.value in channels_map:
            await interaction.response.send_message(
                f"⚠️ This guild is already subscribed to `{key.value}`. Use `/update` if you want to change the channel.",
                ephemeral=True
            )
            return

        # Store key→channel mapping in JSON
        await GuildSettings.add_or_update_channel(
            guild_id=interaction.guild_id,
            key=key.value,
            channel_id=int(news_channel)
        )

        await interaction.response.send_message(
            f"✅ Guild successfully subscribed.\n• Key: `{key.value}`\n• News Channel ID: `{news_channel}`"
        )

    @app_commands.command(name="view", description="View this guild’s current news configuration.")
    async def view(self, interaction: discord.Interaction) -> None:
        if interaction.guild_id is None:
            await interaction.response.send_message(
                "❌ This command can only be used in a server.", ephemeral=True
            )
            return

        channels_map: Optional[Dict[str, int]] = await GuildSettings.get_channels_for_guild(
            interaction.guild_id
        )
        if channels_map is None:
            await interaction.response.send_message(
                "⚠️ This guild is not subscribed to anything yet. Use `/add` to subscribe.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="📰 Guild News Subscriptions",
            colour=discord.Colour.blurple()
        )

        # Show each Region or Category → channel ID
        for key_name, chan_id in channels_map.items():
            embed.add_field(name=key_name, value=str(chan_id), inline=False)

        embed.set_footer(text=f"Guild ID: {interaction.guild_id}")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="update", description="Update this guild’s subscription.")
    @app_commands.describe(
        key="(Optional) New key (Region or Category). Leave blank to only change channel.",
        news_channel="(Optional) New channel ID for that key."
    )
    @app_commands.choices(key=[
        app_commands.Choice(name=k.name, value=k.value) for k in SubscriptionKey
    ])
    async def update(
        self,
        interaction: discord.Interaction,
        key: Optional[SubscriptionKey] = None,
        news_channel: Optional[int] = None,
    ) -> None:
        author: discord.Member = interaction.user  # type: ignore

        # Permission check
        if not getattr(author.guild_permissions, "manage_guild", False):
            await interaction.response.send_message(
                "❌ You don’t have Manage Server permission.", ephemeral=True
            )
            return

        if interaction.guild_id is None:
            await interaction.response.send_message(
                "❌ This command can only be used in a server.", ephemeral=True
            )
            return

        channels_map: Optional[Dict[str, int]] = await GuildSettings.get_channels_for_guild(
            interaction.guild_id
        )
        if channels_map is None:
            await interaction.response.send_message(
                "⚠️ This guild is not subscribed to anything yet. Use `/add` first.",
                ephemeral=True
            )
            return

        if key is None and news_channel is None:
            await interaction.response.send_message(
                "⚠️ Please specify at least one field to update (either `key` or `news_channel`).",
                ephemeral=True
            )
            return

        updated_fields: list[str] = []

        # If key changed, remove old key and later (if channel provided) create the new mapping
        if key is not None:
            # If the guild was subscribed to this same key already, skip removal
            if key.value not in channels_map:
                # Otherwise remove every existing Region/Category key
                for existing_key in list(channels_map.keys()):
                    if existing_key in {r.value for r in Region} or existing_key in {c.value for c in Category}:
                        await GuildSettings.remove_channel(interaction.guild_id, existing_key)
                        updated_fields.append(f"removed key `{existing_key}`")

            # If news_channel provided, immediately re-add under new key
            if news_channel is not None:
                await GuildSettings.add_or_update_channel(
                    guild_id=interaction.guild_id,
                    key=key.value,
                    channel_id=news_channel
                )
                updated_fields.append(f"added key `{key.value}` → `{news_channel}`")
            else:
                await interaction.response.send_message(
                    f"ℹ️ Key updated to `{key.value}`. Please also specify `news_channel` with `/update` to set channel ID.",
                    ephemeral=True
                )
                return

        # If only channel changed (and key was None), find existing key to update
        if news_channel is not None and key is None:
            existing_key: Optional[str] = None
            for k in channels_map.keys():
                if k in {r.value for r in Region} or k in {c.value for c in Category}:
                    existing_key = k
                    break

            if existing_key is not None:
                await GuildSettings.add_or_update_channel(
                    guild_id=interaction.guild_id,
                    key=existing_key,
                    channel_id=news_channel
                )
                updated_fields.append(f"updated channel for `{existing_key}` → `{news_channel}`")
            else:
                await interaction.response.send_message(
                    "⚠️ No existing key found to update channel. Use `/add` first.", ephemeral=True
                )
                return

        await interaction.response.send_message(
            f"✅ Subscription updated: " + ", ".join(updated_fields)
        )

    @app_commands.command(name="remove", description="Unsubscribe this guild from all news.")
    async def remove(self, interaction: discord.Interaction) -> None:
        author: discord.Member = interaction.user  # type: ignore

        # Permission check
        if not getattr(author.guild_permissions, "manage_guild", False):
            await interaction.response.send_message(
                "❌ You don’t have Manage Server permission.", ephemeral=True
            )
            return

        if interaction.guild_id is None:
            await interaction.response.send_message(
                "❌ This command can only be used in a server.", ephemeral=True
            )
            return

        if await GuildSettings.get_channels_for_guild(interaction.guild_id) is None:
            await interaction.response.send_message(
                "⚠️ This guild is not subscribed to anything, nothing to remove.", ephemeral=True
            )
            return

        # Delete entire JSON mapping for this guild
        await GuildSettings.filter(guild_id=interaction.guild_id).delete()

        await interaction.response.send_message(
            "🗑️ All subscriptions removed for this guild."
        )


command = GuildCommands()

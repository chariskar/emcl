# news_commands.py

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
from typing import Dict, Sequence, Optional, Any, List

import discord
from discord import app_commands
import os

from utils.db import NewsSchema, ReporterSchema, Region, Category, GuildSettings, Languages

# Load environment variables (use os.environ[...] to ensure non-None)
GUILD_ID = discord.Object(id=int(os.environ["GUILD_ID"]))
NEWS_CHANNEL_ID = int(os.environ["NEWS_CHANNEL_ID"])
ADMIN_ID = [
    s.strip()
    for s in str(os.environ.get("ADMIN_ID", "")).split(",")
    if s.strip()
]


class NewsCommands(app_commands.Group):
    def __init__(self):
        super().__init__(name="news", description="Manage and post news")

    @app_commands.command(name="add", description="Add and post a news item")
    @app_commands.describe(
        title="The title of the news item",
        description="A short description",
        image_url="Image URL to include in the embed",
        credit="Credit for the news item (e.g., source or author)",
        category="Category of this news item (choose from EMC categories)",
        region="The region this news item is about (defaults to 'Global')",
        language="The language code (e.g., en, fr, es)",
    )
    async def add(
        self,
        interaction: discord.Interaction,
        title: str,
        description: str,
        image_url: str,
        credit: str,
        category: Category  = Category.WORLD,
        region: Region = Region.Global,
        language: Languages = Languages.EN,
    ) -> None:
        # 1) Permission check: must be a registered reporter
        reporter = await ReporterSchema.get_or_none(user_id=interaction.user.id)
        if reporter is None:
            await interaction.response.send_message(
                "🚫 You are not registered as a reporter.", ephemeral=True
            )
            return
        try:
            _f = int(credit)
        except Exception:
            await interaction.response.send_message("Use a fucking user id")
            return

        # 2) Create & save the NewsSchema row
        news = await NewsSchema.create_safe(
            title=title,
            description=description,
            image_url=image_url,
            credit=credit,
            reporter=str(interaction.user.id),
            editor=reporter,
            region=region,
            category=category.value,
            language=language.value,
        )
        if news is None:
            await interaction.response.send_message("⚠️ Failed to create news item.", ephemeral=True)
            return

        embed = news.to_embed()

        # 3) Send to the main guild's news channel
        main_guild = interaction.client.get_guild(GUILD_ID.id)
        if main_guild is None:
            await interaction.response.send_message("⚠️ News saved but main guild not found.", ephemeral=True)
            return

        main_channel = main_guild.get_channel(NEWS_CHANNEL_ID)
        if not isinstance(main_channel, discord.TextChannel):
            await interaction.response.send_message("⚠️ News saved but main news channel is invalid.", ephemeral=True)
            return

        main_msg = await main_channel.send(embed=embed)
        news.message_ids = [{
            "guild_id": main_guild.id,
            "channel_id": NEWS_CHANNEL_ID,
            "message_id": main_msg.id,
        }]
        await news.save()

        reporter.posts += 1
        await reporter.save()

        # 4) Fetch all subscriptions
        all_mappings = await GuildSettings.all_by_key()

        # 6) Collect subscribers
        subscribers = []

        def extend_subscribers(key: str, label: str):
            if key in all_mappings:
                subscribers.extend(all_mappings[key])

        extend_subscribers(region.value, "region")
        extend_subscribers(category.value, "category")
        extend_subscribers(language.value, "language")

        # 7) Deduplicate by (guild_id, channel_id)
        seen = set()
        unique_subscribers = []
        for entry in subscribers:
            key = (entry["guild_id"], entry["channel_id"])
            if key not in seen:
                seen.add(key)
                unique_subscribers.append(entry)

        # 8) Send the embed to each unique subscriber
        for sub in unique_subscribers:
            guild_id, channel_id = sub["guild_id"], sub["channel_id"]

            # Only skip posting to the main news channel itself
            if guild_id == GUILD_ID.id and channel_id == NEWS_CHANNEL_ID:
                continue

            guild = interaction.client.get_guild(guild_id)
            if guild is None:
                print(f"⚠️ Guild {guild_id} not found.")
                continue

            channel = guild.get_channel(channel_id)
            if not isinstance(channel, discord.TextChannel):
                print(f"⚠️ Channel {channel_id} in guild {guild_id} is not a valid TextChannel.")
                continue

            try:
                msg = await channel.send(embed=embed)
                news.message_ids.append({
                    "guild_id": guild_id,
                    "channel_id": channel_id,
                    "message_id": msg.id,
                })
            except Exception as e:
                print(f"❌ Failed to send to {guild_id}/{channel_id}: {e}")

        await news.save()

        await interaction.response.send_message(
            "✅ News created and broadcasted to all subscribers!", ephemeral=True
        )

    @app_commands.command(
        name="edit",
        description="Edit an existing news item (and update all previous embeds)."
    )
    @app_commands.describe(
        news_id="The ID of the news item to edit",
        title="(Optional) New title",
        description="(Optional) New description",
        image_url="(Optional) New image URL",
        credit="(Optional) New credit/source",
        category="(Optional) New category",
        region="(Optional) New region",
        language="(Optional) New language"
    )
    async def edit(
        self,
        interaction: discord.Interaction,
        news_id: int,
        title: Optional[str] = None,
        description: Optional[str] = None,
        image_url: Optional[str] = None,
        credit: Optional[str] = None,
        category: Optional[Category] = None,
        region: Optional[Region] = None,
        language: Optional[Languages] = None,
    ) -> None:
        # 1) Fetch and permission check
        news = await NewsSchema.get_or_none(id=news_id)
        if news is None:
            await interaction.response.send_message(
                "❌ News ID not found.", ephemeral=True
            )
            return

        is_reporter = (int(news.reporter) == interaction.user.id)
        is_admin = (str(interaction.user.id) in ADMIN_ID)
        if not (is_reporter or is_admin):
            await interaction.response.send_message(
                "❌ You are not allowed to edit this item.", ephemeral=True
            )
            return

        # 2) Apply any provided changes to the model
        updated_fields = []
        if title is not None:
            news.title = title
            updated_fields.append("title")
        if description is not None:
            news.description = description
            updated_fields.append("description")
        if image_url is not None:
            news.image_url = image_url
            updated_fields.append("image_url")
        if credit is not None:
            news.credit = credit
            updated_fields.append("credit")
        if category is not None:
            news.category = category.value
            updated_fields.append("category")
        if region is not None:
            news.region = region
            updated_fields.append("region")
        if language is not None:
            news.language = language.value
            updated_fields.append("language")

        if not updated_fields:
            await interaction.response.send_message(
                "⚠️ No changes specified. Provide at least one field to edit.", ephemeral=True
            )
            return

        # Save updated fields to the database
        await news.save(update_fields=updated_fields)

        # 3) Build the new embed from updated values
        new_embed = news.to_embed()

        # 4) Iterate over every recorded message_id and edit
        failed = 0
        for entry in news.message_ids or []:
            guild_id = entry.get("guild_id")
            channel_id = entry.get("channel_id")
            message_id = entry.get("message_id")

            if not (isinstance(guild_id, int) and isinstance(channel_id, int) and isinstance(message_id, int)):
                continue

            target_guild = interaction.client.get_guild(guild_id)
            if target_guild is None:
                failed += 1
                continue

            target_channel = target_guild.get_channel(channel_id)
            if not isinstance(target_channel, discord.TextChannel):
                failed += 1
                continue

            try:
                msg = await target_channel.fetch_message(message_id)
                await msg.edit(embed=new_embed)
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                failed += 1
                continue

        # 5) Acknowledge outcome to the user
        success_count = len(news.message_ids or []) - failed
        await interaction.response.send_message(
            f"✅ Edited news `{news_id}` and updated {success_count} embeds "
            f"(failed to edit {failed} if any).", ephemeral=True
        )

    @app_commands.command(name="delete", description="Delete a news item by ID")
    @app_commands.describe(news_id="The ID of the news item to delete")
    async def delete(self, interaction: discord.Interaction, news_id: int) -> None:
        news: Optional[NewsSchema] = await NewsSchema.get_or_none(id=news_id)
        if news is None:
            await interaction.response.send_message("❌ Not found.", ephemeral=True)
            return

        # Allow deletion if reporter OR admin
        is_reporter: bool = (int(news.reporter) == interaction.user.id)
        is_admin: bool = (str(interaction.user.id) in ADMIN_ID)
        if not (is_reporter or is_admin):
            await interaction.response.send_message(
                "❌ You are not allowed to delete this", ephemeral=True
            )
            return

        # Iterate through all saved message postings and delete them
        for entry in news.message_ids:  # type: ignore
            guild_id: int = entry.get("guild_id")
            channel_id: int = entry.get("channel_id")
            message_id: int = entry.get("message_id")

            target_guild: Optional[discord.Guild] = interaction.client.get_guild(guild_id)
            if target_guild is None:
                continue

            target_channel = target_guild.get_channel(channel_id)
            if not isinstance(target_channel, discord.TextChannel):
                continue

            try:
                msg: discord.Message = await target_channel.fetch_message(message_id)
                await msg.delete()
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                continue
            
        # Finally, delete the DB row
        await news.delete()
        await news.reset_sqlite_autoincrement("newsschema")
        await interaction.response.send_message(
            f"🗑️ Deleted news `{news_id}` from all subscribers.", ephemeral=True
        )

    @app_commands.command(name="lookup", description="Lookup news by filters")
    @app_commands.describe(
        topic="Topic to search for",
        nation="Nation to search for",
        author="Author to search for",
        language="Language code (default: any)",
    )
    async def lookup(
        self,
        interaction: discord.Interaction,
        topic: str = "",
        nation: str = "",
        author: str = "",
        language: str = "",
    ) -> None:
        await interaction.response.defer(ephemeral=True)
        results: Sequence[NewsSchema] = await NewsSchema.search(
            topic=topic or None,
            nation=nation or None,
            author=author or None,
            lang=language or None,
        )
        if not results:
            await interaction.followup.send("🔍 No matching news.", ephemeral=True)
            return

        for n in results[:5]:
            await interaction.followup.send(embed=n.to_embed(), ephemeral=True)

    @app_commands.command(name="recent", description="Show recent news in a language")
    @app_commands.describe(
        language="Language code (e.g., en, fr, es)",
        limit="How many items to show (max 10)",
    )
    async def recent(
        self,
        interaction: discord.Interaction,
        language: str = "en",
        limit: int = 5,
    ) -> None:
        limit = min(limit, 10)
        items: Sequence[NewsSchema] = await NewsSchema.get_recent_by_language(language, limit)
        if not items:
            await interaction.response.send_message("No recent news found.", ephemeral=True)
            return

        for n in items:
            await interaction.response.send_message(embed=n.to_embed(), ephemeral=True)


command = NewsCommands()

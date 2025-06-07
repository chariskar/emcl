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

# TODO: use aerich to make auto updating db schemas

from __future__ import annotations
from typing import Dict, List, Optional, Any, Type, Sequence
from tortoise import fields, models
from tortoise.exceptions import DoesNotExist
from tortoise.fields.relational import ForeignKeyNullableRelation
from tortoise.expressions import Q
from tortoise import Tortoise
import discord
from discord.ext import commands
import asyncio, os
from datetime import datetime, timezone
from enum import Enum
import difflib
from difflib import SequenceMatcher
from .reverse_lookup import *

class Region(Enum):
    North_America   = "North America"
    South_America   = "South America"
    Middle_East     = "Middle East"
    Oceania         = "Oceania"
    East_Asia       = "East Asia"
    South_Asia      = "South Asia"
    Central_Asia    = "Central Asia"
    Europe          = "Europe"
    Africa          = "Africa"
    Global          = "Global"


class Category(str, Enum):
    WORLD       = "World"
    INTERVIEWS  = "Interviews"
    WAR_CONFLICTS = "War & conflicts"
    OPINION     = "Opinion"
    ARTICLES    = "Articles"
    SPORTS      = "Sports"
    EDITORIALS  = "Editorials"
    OTHER       = "Other"

class Languages(Enum):
    FR = "FR"
    EN = "EN"
    JAP = "JAP"
    TURK = "TURK"
    CHINESE = "CHINESE"

class ReporterSchema(models.Model):
    id        = fields.IntField(pk=True)
    user_id   = fields.BigIntField(unique=True)
    posts     = fields.IntField(default=0)
    suspended = fields.BooleanField(default=False)
    strikes   = fields.IntField(default=0)

    def __str__(self) -> str:
        return f"Reporter(user_id={self.user_id}), posts={self.posts}, suspended={self.suspended})"


class NewsSchema(models.Model):
    """
    Each news item now tracks _all_ message postings across all guilds.
    The `message_ids` JSON field stores a list of dicts:
      [
        { "guild_id": 1234, "channel_id": 5678, "message_id": 9012 },
        { "guild_id": 2345, "channel_id": 6789, "message_id": 0123 },
        ...
      ]
    """

    id            = fields.IntField(pk=True)
    title         = fields.CharField(max_length=255)
    description   = fields.TextField()
    image_url     = fields.CharField(max_length=500)
    credit        = fields.CharField(max_length=100, null=False)
    reporter      = fields.CharField(max_length=100, null=False)
    language      = fields.CharField(max_length=10)
    region        = fields.CharEnumField(Region, max_length=10, null=True)
    category      = fields.TextField()
    date          = fields.DatetimeField(auto_now_add=False, auto_now=True)
    # Replace single `message_id` field with a JSON list of all postings
    message_ids   = fields.JSONField(default=list)

    editor: ForeignKeyNullableRelation[ReporterSchema] = fields.ForeignKeyField(
        "models.ReporterSchema", related_name="news_items", on_delete=fields.SET_NULL, null=True
    )



    def to_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title=self.title,
            description=self.description,
            color=discord.Color.blurple()
        )

        embed.set_thumbnail(url=os.environ.get("LOGO_URL"))
        embed.set_image(url=self.image_url)

        reporter = f"<@{self.reporter}>" if self.reporter else "Unknown"
        region_str = self.region.value if self.region else "Unknown"
        credit   = f"<@{self.credit}>" if self.credit else "Unknown"

        embed.add_field(
            name="Reporter / Region / Credit",
            value=f"{reporter} | {region_str} | {credit}",
            inline=False
        )
        return embed

    def is_similar_to(self, other: "NewsSchema", threshold: float = 0.85) -> bool:
        title_ratio = difflib.SequenceMatcher(
            None, self.title.lower(), other.title.lower()
        ).ratio()
        desc_ratio  = difflib.SequenceMatcher(
            None, self.description.lower(), other.description.lower()
        ).ratio()
        return title_ratio > threshold and desc_ratio > threshold
    
    async def to_dict(self, bot: commands.Bot) -> dict[str, int | str | None]:
        # Fetch credit user name or fallback
        try:
            credit_user = await bot.fetch_user(int(self.credit))
            credit_username = credit_user.name
        except discord.NotFound:
            credit_username = f"<Unknown:{self.credit}>"
        except Exception as e:
            credit_username = f"<Error:{self.credit}>"

        reporter_user = bot.get_user(int(self.reporter))
        if reporter_user is None:
            try:
                reporter_user = await bot.fetch_user(int(self.reporter))
                reporter_username = reporter_user.name
            except discord.NotFound:
                reporter_username = f"<Unknown:{self.reporter}>"
            except Exception:
                reporter_username = f"<Error:{self.reporter}>"
        else:
            reporter_username = reporter_user.name

        # Normalize date to UTC string
        utc_now = discord.utils.utcnow()
        if self.date.tzinfo is None:
            date_utc = self.date.replace(tzinfo=utc_now.tzinfo)
        else:
            date_utc = self.date.astimezone(utc_now.tzinfo)

        formatted_date = date_utc.strftime("%Y-%m-%d %H:%M:%S UTC")

        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "image_url": self.image_url,
            "credit": credit_username,
            "reporter": reporter_username,
            "language": self.language,
            "region": self.region.value if self.region else "global",
            "date": formatted_date,
            "category": self.category
        }

    @classmethod
    def set_bot(cls, bot_instance: commands.Bot) -> None:
        cls.bot = bot_instance

    @classmethod
    async def filter_by_language(cls, lang: str) -> Sequence["NewsSchema"]:
        return await cls.filter(language=lang).order_by("-date")

    @classmethod
    async def get_recent_by_language(cls, lang: str, limit: int = 10) -> Sequence["NewsSchema"]:
        return await cls.filter(language=lang).order_by("-date").limit(limit)

    @classmethod
    async def search(
        cls,
        topic:   Optional[str] = None,
        nation:  Optional[str] = None,
        author:  Optional[str] = None,
        lang:    Optional[str] = None,
        category: Optional[str] = None
    ) -> Sequence["NewsSchema"]:
        filters = Q()
        if topic:
            filters &= Q(title__icontains=topic)
        if nation:
            filters &= Q(description__icontains=nation)
        if author:
            filters &= Q(reporter__icontains=author)
        if lang:
            filters &= Q(language=lang)
        if category:
            filters &= Q(category=category)

        return await cls.filter(filters).order_by("-date").limit(10)

    @classmethod
    async def create_safe(
        cls,
        title:       str,
        description: str,
        image_url:   str,
        credit:      str,
        reporter:    str,
        language:    str,
        category:    str,
        editor:      Optional[ReporterSchema] = None,
        region:      Optional[Region]        = None, 
    ) -> Optional["NewsSchema"]:
        return await cls.create(
            title=title,
            description=description,
            image_url=image_url,
            credit=credit,
            reporter=reporter,
            language=language,
            editor=editor,
            region=region,
            category=category,
            date=datetime.now(timezone.utc),
            message_id=0
        )

    @classmethod
    async def search_all(
        cls,
        term: str,
        limit: int = 10
    ) -> Sequence["NewsSchema"]:
        term_lower = term.lower()

        candidates = await cls.filter(
            Q(title__icontains=term_lower) |
            Q(description__icontains=term_lower) |
            Q(category__icontains=term_lower)
        ).all()

        scored: list[tuple[float, NewsSchema]] = []

        for item in candidates:
            title_text = item.title.lower()
            desc_text = item.description.lower()
            cat_text = item.category.lower()

            title_ratio = SequenceMatcher(None, term_lower, title_text).ratio()
            desc_ratio = SequenceMatcher(None, term_lower, desc_text).ratio()
            cat_ratio  = SequenceMatcher(None, term_lower, cat_text).ratio()

            bonus = 0.0
            if term_lower in title_text:
                bonus += 0.10
            if term_lower in desc_text:
                bonus += 0.05
            if term_lower in cat_text:
                bonus += 0.03

            combined_score = (
                0.50 * title_ratio +
                0.30 * desc_ratio +
                0.20 * cat_ratio +
                bonus
            )

            if combined_score > 0.10:
                scored.append((combined_score, item))

        scored.sort(key=lambda pair: pair[0], reverse=True)
        top_items = [itm for (_score, itm) in scored[:limit]]
        return top_items
    


    async def reset_sqlite_autoincrement(self,table_name: str):
        conn = Tortoise.get_connection("default")
        row = await conn.execute_query_dict(f"SELECT MAX(id) AS maxid FROM {table_name}")
        max_row = row[0]
        max_id = max_row["maxid"] or 0
        await conn.execute_script(f"UPDATE sqlite_sequence SET seq = {max_id} WHERE name = '{table_name}'")
        
    @classmethod
    async def search_with_index(
        cls,
        query: str,
        limit: int = 10,
        language: Optional[str] = None
    ):
        if not news_index.is_initialized:
            return await cls.search_all(query, limit)
        
        candidate_ids = await search_news_fast(query, limit * 2)  # Get more candidates for filtering
        
        if not candidate_ids:
            return []
        
        news_items = await cls.filter(id__in=candidate_ids).all()
        
        if language:
            news_items = [item for item in news_items if item.language.upper() == language.upper()]
        
        id_to_item = {item.id: item for item in news_items}
        ordered_results = [id_to_item[news_id] for news_id in candidate_ids if news_id in id_to_item]
        
        return ordered_results[:limit]
    
    @classmethod
    async def create_with_index(cls, **kwargs):
        """Create a news item and add it to the search index"""
        news_item = await cls.create(**kwargs)
        add_news_to_index(news_item)
        return news_item
    
    async def delete_with_index(self):
        """Delete a news item and remove it from the search index"""
        remove_news_from_index(self.id)
        await self.delete()


class GuildSettings(models.Model):

    id       = fields.IntField(pk=True)
    guild_id = fields.BigIntField(unique=True)
    channels = fields.JSONField(default=dict)

    @classmethod
    async def add_or_update_channel(
        cls: Type[GuildSettings],
        guild_id: int,
        key: str,
        channel_id: int
    ) -> None:
        obj, _created = await cls.get_or_create(
            guild_id=guild_id,
            defaults={"channels": {}}
        )

        if not isinstance(obj.channels, dict):
            obj.channels = {}

        obj.channels[key] = channel_id
        await obj.save()

    @classmethod
    async def remove_channel(
        cls: Type[GuildSettings],
        guild_id: int,
        key: str
    ) -> None:
        try:
            obj = await cls.get(guild_id=guild_id)
        except DoesNotExist:
            return

        if not isinstance(obj.channels, dict):
            return

        if key in obj.channels:
            del obj.channels[key]
            await obj.save()

    @classmethod
    async def get_channels_for_guild(
        cls: Type[GuildSettings],
        guild_id: int
    ) -> Optional[Dict[str, int]]:
        try:
            obj = await cls.get(guild_id=guild_id)
        except DoesNotExist:
            return None

        if isinstance(obj.channels, dict):
            return dict(obj.channels)
        return {}

    @classmethod
    async def all_by_key(
        cls: Type[GuildSettings]
    ) -> Dict[str, List[Dict[str, int]]]:
        records: List[GuildSettings] = await cls.all()
        out: Dict[str, List[Dict[str, int]]] = {}

        for rec in records:
            mapping: Any = rec.channels or {}
            if not isinstance(mapping, dict):
                continue

            for key_name, ch_id in mapping.items():
                if isinstance(ch_id, int):
                    entry: Dict[str, int] = {
                        "guild_id": rec.guild_id,
                        "channel_id": ch_id
                    }
                    out.setdefault(key_name, []).append(entry)

        return out

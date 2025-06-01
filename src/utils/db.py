# src/utils/db.py

import discord
from tortoise.models import Model
from tortoise import fields
from tortoise.fields.relational import ForeignKeyNullableRelation
import difflib, os
from typing import Sequence, Optional
from tortoise.expressions import Q
from discord.ext import commands
from datetime import datetime, timezone
from difflib import SequenceMatcher
from enum import Enum


class Region(Enum):
    Europe = "Europe"
    Asia = "Asia"
    Oceania = "Oceania"
    Africa = "Africa"
    America = "America"
    Global = "Global"

class ReporterSchema(Model):
    id        = fields.IntField(pk=True)
    user_id   = fields.BigIntField(unique=True)
    posts     = fields.IntField(default=0)
    suspended = fields.BooleanField(default=False)
    strikes   = fields.IntField(default=0)

    def __str__(self) -> str:
        return f"Reporter(user_id={self.user_id}), posts={self.posts}, suspended={self.suspended})"


class NewsSchema(Model):
    id          = fields.IntField(pk=True)
    title       = fields.CharField(max_length=255)
    description = fields.TextField()
    image_url   = fields.CharField(max_length=500)
    credit      = fields.CharField(max_length=100, null=False)
    reporter    = fields.CharField(max_length=100, null=False)
    language    = fields.CharField(max_length=10)
    region      = fields.CharEnumField(Region, max_length=10, null=True)  # switched to Enum
    category    = fields.TextField()
    date        = fields.DatetimeField(auto_now_add=False, auto_now=True)
    message_id   = fields.IntField(required=False)
    
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
        credit_user = bot.get_user(int(self.credit))
        if credit_user is None:
            try:
                credit_user = await bot.fetch_user(int(self.credit))
            except discord.NotFound:
                credit_username = f"<Unknown:{self.credit}>"
            else:
                credit_username = credit_user.name
        else:
            credit_username = credit_user.name

        reporter_user = bot.get_user(int(self.reporter))
        if reporter_user is None:
            try:
                reporter_user = await bot.fetch_user(int(self.reporter))
            except discord.NotFound:
                reporter_username = f"<Unknown:{self.reporter}>"
            else:
                reporter_username = reporter_user.name
        else:
            reporter_username = reporter_user.name

        if self.date.tzinfo is None:
            date_utc = self.date.replace(tzinfo=discord.utils.utcnow().tzinfo)
        else:
            date_utc = self.date.astimezone(discord.utils.utcnow().tzinfo)

        formatted_date = date_utc.strftime("%Y-%m-%d %H:%M:%S UTC")

        return {
            "id":          self.id,
            "title":       self.title,
            "description": self.description,
            "image_url":   self.image_url,
            "credit":      credit_username,
            "reporter":    reporter_username,
            "language":    self.language,
            "region":      (self.region.value if self.region else "global"),
            "date":        formatted_date,
            "category":    self.category
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
        region:      Optional[Region]        = None,  # now expects Region enum
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


class GuildSettings(Model):
    id           = fields.IntField(pk=True)
    region       = fields.CharEnumField(Region, max_length=10)  # switched to Enum
    news_channel = fields.IntField()
    guild_id     = fields.IntField(unique=True)

    @classmethod
    async def add_guild(cls, guild_id: int, news_channel_id: int, region: Region):
        """
        Create a new GuildSettings row. 'region' should be a Region enum member.
        """
        await cls.create(
            guild_id=guild_id,
            news_channel=news_channel_id,
            region=region
        )

    @classmethod
    async def is_registered(cls, guild_id: int) -> bool:
        return await cls.exists(guild_id=guild_id)

    @classmethod
    async def all_by_region(cls) ->  dict[str, list[dict[int, int]]]:
        records = await cls.all()
        grouped: dict[str, list[dict[int, int]]] = {}
        for rec in records:
            region_str = rec.region.value  # e.g. "Asia", "Europe", etc.
            entry = {rec.guild_id: rec.news_channel}
            grouped.setdefault(region_str, []).append(entry)
        return grouped


class Alliances(Model):
    id = fields.IntField(pk=True)
    nations = fields.TextField() 
import discord
from tortoise.models import Model
from tortoise import fields
from tortoise.fields.relational import ForeignKeyNullableRelation
import difflib
from typing import Sequence, Optional
from tortoise.expressions import Q

class ReporterSchema(Model):
    id = fields.IntField(pk=True)
    user_id = fields.BigIntField(unique=True)
    posts = fields.IntField(default=0)
    suspended = fields.BooleanField(default=False)
    strikes = fields.IntField(default=0)
    def __str__(self) -> str:
        return f"Reporter(user_id={self.user_id}), posts={self.posts}, suspended={self.suspended})"


class NewsSchema(Model):
    id = fields.IntField(pk=True)
    title = fields.CharField(max_length=255, unique=True)
    description = fields.TextField(unique=True)
    image_url = fields.CharField(max_length=500)
    credit = fields.CharField(max_length=100, null=False)
    reporter  = fields.CharField(max_length=100, null=False)
    language = fields.CharField(max_length=10)
    region = fields.CharField(maxlength=50)
    
    editor: ForeignKeyNullableRelation[ReporterSchema] = fields.ForeignKeyField(
        "models.ReporterSchema", related_name="news_items", on_delete=fields.SET_NULL, null=True
    )

    def to_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title=self.title,
            description=self.description,
            color=discord.Color.blurple()
        )
        embed.set_image(url=self.image_url)
        # Show credit
        embed.add_field(name="Credit", value=self.credit, inline=True)
        try:
            reporter_mention = f"@<{self.reporter}>"
        except Exception:
            reporter_mention = str(self.reporter)
            
        embed.add_field(name="Reporter", value=reporter_mention, inline=True)
        embed.add_field(name="region", value=self.region, inline=True)
        return embed
    
    def is_similar_to(self, other: "NewsSchema", threshold: float = 0.85) -> bool:
        title_ratio = difflib.SequenceMatcher(None, self.title.lower(), other.title.lower()).ratio()
        desc_ratio = difflib.SequenceMatcher(None, self.description.lower(), other.description.lower()).ratio()
        return title_ratio > threshold and desc_ratio > threshold

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "image_url": self.image_url,
            "credit": self.credit,
            "reporter": self.reporter,
            "language": self.language,
            "editor": self.editor.user_id if self.editor else None,
            "region": self.region if self.region else "global"
        }

    @classmethod
    async def find_similar(
        cls,
        title: str,
        description: str,
        language: str,
        threshold: float = 0.85
    ) -> Optional["NewsSchema"]:
        recent_news = await cls.filter(language=language).order_by("-id").limit(50)
        for news in recent_news:
            title_ratio = difflib.SequenceMatcher(None, title.lower(), news.title.lower()).ratio()
            desc_ratio = difflib.SequenceMatcher(None, description.lower(), news.description.lower()).ratio()
            if title_ratio > threshold and desc_ratio > threshold:
                return news
        return None
    
    @classmethod
    async def filter_by_language(cls, lang: str) -> Sequence["NewsSchema"]:
        """
        Return all news items in the given language,
        ordered by newest first.
        """
        return await cls.filter(language=lang).order_by("-date")

    @classmethod
    async def get_recent_by_language(cls, lang: str, limit: int = 10) -> Sequence["NewsSchema"]:
        """
        Return the most recent `limit` items in the given language.
        """
        return await cls.filter(language=lang).order_by("-date").limit(limit)
    
    @classmethod
    async def search(
        cls,
        topic: Optional[str] = None,
        nation: Optional[str] = None,
        author: Optional[str] = None,
        lang: Optional[str] = None
    ) -> Sequence["NewsSchema"]:
        """
        Flexible search, with optional language filter.
        """
        filters = Q()
        if topic:
            filters &= Q(title__icontains=topic)
        if nation:
            filters &= Q(description__icontains=nation)
        if author:
            filters &= Q(reporter__icontains=author)
        if lang:
            filters &= Q(language=lang)

        return await cls.filter(filters).order_by("-date").limit(10)
    
    @classmethod
    async def create_safe(
        cls,
        title: str,
        description: str,
        image_url: str,
        credit: str,
        reporter: str,
        language: str,
        editor: Optional[ReporterSchema] = None,
        region: Optional[str] = None,
        similarity_threshold: float = 0.85
    ) -> Optional["NewsSchema"]:
        existing_news = await cls.find_similar(title, description, language, similarity_threshold)
        if existing_news:
            return None

        return await cls.create(
            title=title,
            description=description,
            image_url=image_url,
            credit=credit,
            reporter=reporter,
            language=language,
            editor=editor,
            region=region
        )

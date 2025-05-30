import discord
from discord.ext import commands
from discord import app_commands

from tortoise.exceptions import IntegrityError
from utils.db import NewsSchema, ReporterSchema  # adjust imports

GUILD_ID = discord.Object(id=1376636845965705226)
NEWS_CHANNEL_ID = 1376957360727134308


class NewsCommands(app_commands.Group):
    def __init__(self):
        super().__init__(name="news", description="Manage and post news")

    @app_commands.command(name="add", description="Add and post a news item")
    @app_commands.describe(
        title="The title of the news item",
        description="A short description",
        image_url="Image URL to include in the embed",
        credit="Credit for the news item (e.g., source or author)",
        region="The region this news item is about (optional, defaults to 'Global')",
        language="The language code (e.g., en, fr, es)"
    )
    async def add(
        self,
        interaction: discord.Interaction,
        title: str,
        description: str,
        image_url: str,
        credit: str,
        region: str = "Global",
        language: str = "en"
    ):
        # permission check
        reporter = await ReporterSchema.get_or_none(user_id=interaction.user.id)
        if not reporter:
            return await interaction.response.send_message(
                "🚫 You are not registered as a reporter.", ephemeral=True
            )

        # attempt safe create (returns None on similar duplicate)
        news = await NewsSchema.create_safe(
            title=title,
            description=description,
            image_url=image_url,
            credit=credit,
            reporter=str(interaction.user.id),
            language=language,
            editor=reporter,
            region=region
        )
        if not news:
            return await interaction.response.send_message(
                "⚠️ A similar news item already exists in that language.", ephemeral=True
            )

        # post to channel
        guild = interaction.client.get_guild(GUILD_ID.id)
        if not guild:
            return await interaction.response.send_message(
                "⚠️ News saved but guild not found.", ephemeral=True
            )
        channel = guild.get_channel(NEWS_CHANNEL_ID)
        if not isinstance(channel, discord.TextChannel):
            return await interaction.response.send_message(
                "⚠️ News saved but target channel invalid.", ephemeral=True
            )

        await channel.send(embed=news.to_embed())
        await interaction.response.send_message(
            "✅ News created and posted!", ephemeral=True
        )

        # bump reporter post count
        reporter.posts += 1
        await reporter.save()

    @app_commands.command(name="delete", description="Delete a news item by ID")
    @app_commands.describe(news_id="The ID of the news item to delete")
    async def delete(self, interaction: discord.Interaction, news_id: int):
        news = await NewsSchema.get_or_none(id=news_id)
        if not news:
            return await interaction.response.send_message("Not found.", ephemeral=True)
        await news.delete()
        await interaction.response.send_message(f"🗑️ Deleted news `{news_id}`.", ephemeral=True)

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
        language: str = ""
    ):
        await interaction.response.defer(ephemeral=True)
        # run the unified search helper
        results = await NewsSchema.search(
            topic=topic or None,
            nation=nation or None,
            author=author or None,
            lang=language or None
        )
        if not results:
            return await interaction.followup.send("🔍 No matching news.", ephemeral=True)

        for embed in [n.to_embed() for n in results[:5]]:
            await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="recent", description="Show recent news in a language")
    @app_commands.describe(
        language="Language code (e.g., en, fr, es)",
        limit="How many items to show (max 10)"
    )
    async def recent(
        self,
        interaction: discord.Interaction,
        language: str = "en",
        limit: int = 5
    ):
        limit = min(limit, 10)
        items = await NewsSchema.get_recent_by_language(language, limit)
        if not items:
            return await interaction.response.send_message("No recent news found.", ephemeral=True)

        for embed in [n.to_embed() for n in items]:
            await interaction.response.send_message(embed=embed, ephemeral=True)

command = NewsCommands()

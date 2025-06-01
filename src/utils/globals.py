from discord.ext import commands
import discord, asyncio
from .db import GuildSettings
intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix="/", intents=intents)

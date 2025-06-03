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

from tortoise import Tortoise
import discord
from discord.ext import commands
import uvicorn
import importlib
import pkgutil
from discord import app_commands
import dotenv, os, asyncio, threading
from utils.db import ReporterSchema
dotenv.load_dotenv()
from utils.globals import *

def load_app_command_modules(tree: app_commands.CommandTree, package: str):
    """
    Recursively scan `package` (e.g. "commands") for any sub-modules,
    import them, look for a `command` export, and register it if valid.
    """
    pkg = importlib.import_module(package)

    for _finder, module_name, _is_pkg in pkgutil.walk_packages(pkg.__path__, prefix=package + "."):
        print(f"[LOAD] Trying module {module_name}")
        try:
            module = importlib.import_module(module_name)
        except Exception as e:
            print(f"[ERROR] Failed to import {module_name}: {e}")
            continue

        cmd = getattr(module, "command", None)
        if cmd is None:
            print(f"[SKIP] No `command` export in {module_name}")
            continue

        if not isinstance(cmd, (app_commands.Command, app_commands.Group)):
            print(f"[SKIP] `command` in {module_name} is not a Command or Group")
            continue

        # Try to add it
        try:
            tree.add_command(cmd)
            print(f"[OK] Registered `{cmd.name}` from {module_name}")
        except Exception as e:
            print(f"[ERROR] Could not register `{cmd.name}` from {module_name}: {e}")


seted_up = False
async def setup(seted_up: bool):
    if seted_up: return
    seted_up = True
     
    reporter_role = 1376639373721866240
    
    guild = bot.get_guild(1376636845965705226)
    if not guild: return
    role = guild.get_role(reporter_role)
    if not role: return
    members = role.members
    for member in members:
        user_id = member.id
        existing = await ReporterSchema.get_or_none(user_id=user_id)
        if not existing:
            await ReporterSchema.create(user_id=user_id)


def start_api():

    uvicorn.run("utils.api:router", host="0.0.0.0", port=3000)  # No reload

async def start_db():
    await Tortoise.init(
        db_url="sqlite://db.db",
        modules={"models": ["utils.db"]},
    )
    await Tortoise.generate_schemas()
    print("Schema generated!")

@bot.event
async def on_ready():
  

    print(f"Logged in as {bot.user} ({bot.user.id})")

    load_app_command_modules(bot.tree, "commands")
    await bot.tree.sync()
    print("Commands synced")
    await setup(seted_up)

    
if __name__ == "__main__":
    asyncio.run(start_db())
    api_thread = threading.Thread(target=start_api, daemon=True)
    api_thread.start()
    api_thread.join()
    bot.run(str(os.environ.get("TOKEN")))

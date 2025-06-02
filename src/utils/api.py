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
from fastapi import APIRouter, Query
from typing import Optional
from .db import NewsSchema  # assuming this is where your model is
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from .globals import bot
from fastapi import HTTPException
import os
router = APIRouter(prefix="", tags=["News"],)

@router.get("/api/get/{title}")
async def get_news_by_title(title: str, q: Optional[str] = None):
    news_items = await NewsSchema.search(topic=title)
    return {"news": [await item.to_dict(bot) for item in news_items], "q": q}

@router.get("/api/filter-by-language/{lang}")
async def get_by_language(lang: str):
    news_items = await NewsSchema.filter_by_language(lang)
    return [item.to_dict(bot) for item in news_items]

@router.get("/api/recent/{lang}")
async def get_recent(lang: str, limit: int = 10):
    news_items = await NewsSchema.get_recent_by_language(lang, limit)
    return [await item.to_dict(bot) for item in news_items]

@router.get("/api/search")
async def search_news(
    topic: Optional[str] = Query(None),
    nation: Optional[str] = Query(None),
    author: Optional[str] = Query(None),
    lang: Optional[str] = Query(None)
):
    news_items = await NewsSchema.search(topic=topic, nation=nation, author=author, lang=lang)
    return [await item.to_dict(bot) for item in news_items]

@router.get('/api/search/all/{query}')
async def search_all_news(query: str):
    news_items = await NewsSchema.search_all(query)
    return [await item.to_dict(bot) for item in news_items]

@router.get("/", response_class=HTMLResponse)
async def homepage():
    file_path = os.path.join("src","static", "index.html")
    return FileResponse(file_path, media_type="text/html")

@router.get("/assets/{filename}")
async def serve_asset(filename: str):
    # Make sure this matches the exact path on disk
    file_path = os.path.join("src","static","assets", filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Not found")

    if filename.endswith(".css"):
        return FileResponse(file_path, media_type="text/css")
    elif filename.endswith(".js"):
        return FileResponse(file_path, media_type="application/javascript")
    else:
        return FileResponse(file_path)  # fallback

@router.get("/logo")
async def get_logo():
    file_path = os.path.join("src","static","assets", "favicon.ico")
    return FileResponse(file_path, media_type="image/jpeg")
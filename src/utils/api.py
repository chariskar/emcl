from fastapi import APIRouter, Query
from typing import Optional
from .db import NewsSchema  # assuming this is where your model is
from fastapi.responses import JSONResponse, FileResponse
from .globals import bot
router = APIRouter(prefix="/api", tags=["News"],)

@router.get("/get/{title}")
async def get_news_by_title(title: str, q: Optional[str] = None):
    news_items = await NewsSchema.search(topic=title)
    return {"news": [await item.to_dict(bot) for item in news_items], "q": q}

@router.get("/filter-by-language/{lang}")
async def get_by_language(lang: str):
    news_items = await NewsSchema.filter_by_language(lang)
    return [item.to_dict(bot) for item in news_items]

@router.get("/recent/{lang}")
async def get_recent(lang: str, limit: int = 10):
    news_items = await NewsSchema.get_recent_by_language(lang, limit)
    return [await item.to_dict(bot) for item in news_items]

@router.get("/search")
async def search_news(
    topic: Optional[str] = Query(None),
    nation: Optional[str] = Query(None),
    author: Optional[str] = Query(None),
    lang: Optional[str] = Query(None)
):
    news_items = await NewsSchema.search(topic=topic, nation=nation, author=author, lang=lang)
    return [await item.to_dict(bot) for item in news_items]

@router.get('/search/all/{query}')
async def search_all_news(query: str):
    news_items = await NewsSchema.search_all(query)
    return [await item.to_dict(bot) for item in news_items]

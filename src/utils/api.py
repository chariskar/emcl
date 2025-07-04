#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Updated FastAPI routes with reverse index integration
#

from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from .db import NewsSchema, Category
from fastapi.responses import FileResponse, HTMLResponse
from .globals import bot
from .reverse_lookup import (
    initialize_search_index, 
    search_news_fast, 
    add_news_to_index, 
    news_index
)
import os, logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="", tags=["News"])

@router.on_event("startup")
async def startup_event():
    try:
        await initialize_search_index(NewsSchema)
        logger.info("Search index initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize search index: {e}")

@router.get("/api/get/{title}")
async def get_news_by_title(title: str, q: Optional[str] = None):
    try:
        candidate_ids = await search_news_fast(title, limit=20)
        
        if candidate_ids:
            news_items = await NewsSchema.filter(id__in=candidate_ids).all()
            id_to_item = {item.id: item for item in news_items}
            ordered_items = [id_to_item[news_id] for news_id in candidate_ids if news_id in id_to_item]
        else:
            ordered_items = await NewsSchema.search(topic=title)
        
        return {
            "news": [await item.to_dict(bot) for item in ordered_items], 
            "q": q,
            "indexed": news_index.is_initialized
        }
    except Exception as e:
        logger.error(f"Error in get_news_by_title: {e}")
        news_items = await NewsSchema.search(topic=title)
        return {"news": [await item.to_dict(bot) for item in news_items], "q": q}

@router.get("/api/filter-by-language/{lang}")
async def get_by_language(lang: str):
    news_items = await NewsSchema.filter_by_language(lang.upper())
    return [await item.to_dict(bot) for item in news_items]

@router.get("/api/recent/{lang}")
async def get_recent(lang: str, limit: int = 10):
    news_items = await NewsSchema.get_recent_by_language(lang.upper(), limit)
    return [await item.to_dict(bot) for item in news_items]

@router.get("/api/search")
async def search_news(
    topic: Optional[str] = Query(None),
    nation: Optional[str] = Query(None),
    author: Optional[str] = Query(None),
    lang: Optional[str] = Query(None)
):
    if topic and not any([nation, author, lang]):
        try:
            candidate_ids = await search_news_fast(topic, limit=20)
            if candidate_ids:
                news_items = await NewsSchema.filter(id__in=candidate_ids).all()
                id_to_item = {item.id: item for item in news_items}
                ordered_items = [id_to_item[news_id] for news_id in candidate_ids if news_id in id_to_item]
                return [await item.to_dict(bot) for item in ordered_items]
        except Exception as e:
            logger.error(f"Index search failed, falling back to database: {e}")
    
    
    news_items = await NewsSchema.search(topic=topic, nation=nation, author=author, lang=lang)
    return [await item.to_dict(bot) for item in news_items]

@router.get('/api/search/all/{query}')
async def search_all_news(query: str, limit: int = 10):
    try:
        if news_index.is_initialized:
            candidate_ids = await search_news_fast(query, limit=limit)
            
            if candidate_ids:
                news_items = await NewsSchema.filter(id__in=candidate_ids).all()
                
                id_to_item = {item.id: item for item in news_items}
                ordered_items = [id_to_item[news_id] for news_id in candidate_ids if news_id in id_to_item]
                
                return [await item.to_dict(bot) for item in ordered_items]
        
        logger.warning("Using fallback search - index not available")
        news_items = await NewsSchema.search_all(query.upper(), limit)
        return [await item.to_dict(bot) for item in news_items]
        
    except Exception as e:
        logger.error(f"Error in search_all_news: {e}")
        news_items = await NewsSchema.search_all(query.upper(), limit)
        return [await item.to_dict(bot) for item in news_items]

@router.get("/api/search/stats")
async def get_search_stats():
    if not news_index.is_initialized:
        return {"error": "Search index not initialized"}
    
    stats = news_index.get_stats()
    stats['initialized'] = news_index.is_initialized
    return stats

@router.get("/", response_class=HTMLResponse)
async def homepage():
    file_path = os.path.join("src", "static", "index.html")
    return FileResponse(file_path, media_type="text/html")

@router.get("/assets/{filename}")
async def serve_asset(filename: str):
    file_path = os.path.join("src", "static", "assets", filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Not found")
    
    if filename.endswith(".css"):
        return FileResponse(file_path, media_type="text/css")
    elif filename.endswith(".js"):
        return FileResponse(file_path, media_type="application/javascript")
    else:
        return FileResponse(file_path)

@router.get("/logo")
async def get_logo():
    file_path = os.path.join("src", "static", "favicon.ico")
    return FileResponse(file_path, media_type="image/jpeg")

@router.get("/api/categories")
async def categories():
    l = []
    for key in Category:
        l.append(key.value)
    return {"categories": l}


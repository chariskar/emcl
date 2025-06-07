#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Reverse Index Search Implementation for News System
#

import re
import asyncio
from typing import Dict, Set, List, Optional, Tuple
from collections import defaultdict
import string
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class IndexEntry:
    """Represents a document in the index with its relevance scores"""
    news_id: int
    title_matches: int = 0
    description_matches: int = 0
    category_matches: int = 0
    total_score: float = 0.0

class ReverseIndex:
    """
    High-performance reverse index for news search.
    Maintains an in-memory inverted index that maps terms to document IDs.
    """
    
    def __init__(self):
        # Core index: term -> set of news IDs that contain this term
        self.title_index: Dict[str, Set[int]] = defaultdict(set)
        self.description_index: Dict[str, Set[int]] = defaultdict(set)
        self.category_index: Dict[str, Set[int]] = defaultdict(set)
        
        # Document storage for scoring
        self.documents: Dict[int, Dict[str, str]] = {}
        
        # Stop words to ignore
        self.stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'up', 'about', 'into', 'through', 'during',
            'before', 'after', 'above', 'below', 'between', 'among', 'through',
            'during', 'before', 'after', 'above', 'below', 'up', 'down', 'out',
            'off', 'over', 'under', 'again', 'further', 'then', 'once', 'here',
            'there', 'when', 'where', 'why', 'how', 'all', 'any', 'both', 'each',
            'few', 'more', 'most', 'other', 'some', 'such', 'no', 'nor', 'not',
            'only', 'own', 'same', 'so', 'than', 'too', 'very', 'can', 'will',
            'just', 'should', 'now'
        }
        
        self.is_initialized = False
    
    def _normalize_text(self, text: str) -> List[str]:
        """
        Normalize text into searchable terms.
        Removes punctuation, converts to lowercase, filters stop words.
        """
        if not text:
            return []
        
        # Convert to lowercase and remove punctuation
        text = text.lower()
        text = re.sub(r'[^\w\s]', ' ', text)
        
        # Split into words and filter
        words = text.split()
        
        # Filter out stop words and short words
        filtered_words = [
            word for word in words 
            if len(word) > 2 and word not in self.stop_words
        ]
        
        return filtered_words
    
    def add_document(self, news_item) -> None:
        """Add a news item to the reverse index"""
        news_id = news_item.id
        
        # Store document for later retrieval
        self.documents[news_id] = {
            'title': news_item.title,
            'description': news_item.description,
            'category': news_item.category,
            'language': news_item.language,
            'region': news_item.region.value if news_item.region else 'global'
        }
        
        # Index title terms
        title_terms = self._normalize_text(news_item.title)
        for term in title_terms:
            self.title_index[term].add(news_id)
        
        # Index description terms
        desc_terms = self._normalize_text(news_item.description)
        for term in desc_terms:
            self.description_index[term].add(news_id)
        
        # Index category terms
        category_terms = self._normalize_text(news_item.category)
        for term in category_terms:
            self.category_index[term].add(news_id)
    
    def remove_document(self, news_id: int) -> None:
        """Remove a news item from the reverse index"""
        if news_id not in self.documents:
            return
        
        doc = self.documents[news_id]
        
        # Remove from title index
        title_terms = self._normalize_text(doc['title'])
        for term in title_terms:
            self.title_index[term].discard(news_id)
            if not self.title_index[term]:
                del self.title_index[term]
        
        # Remove from description index
        desc_terms = self._normalize_text(doc['description'])
        for term in desc_terms:
            self.description_index[term].discard(news_id)
            if not self.description_index[term]:
                del self.description_index[term]
        
        # Remove from category index
        category_terms = self._normalize_text(doc['category'])
        for term in category_terms:
            self.category_index[term].discard(news_id)
            if not self.category_index[term]:
                del self.category_index[term]
        
        # Remove document
        del self.documents[news_id]
    
    def search(self, query: str, limit: int = 10) -> List[Tuple[int, float]]:
        """
        Search the index for documents matching the query.
        Returns list of (news_id, score) tuples sorted by relevance.
        """
        if not query.strip():
            return []
        
        query_terms = self._normalize_text(query)
        if not query_terms:
            return []
        
        # Collect all matching documents with their match counts
        matches: Dict[int, IndexEntry] = {}
        
        for term in query_terms:
            # Title matches (highest weight)
            for news_id in self.title_index.get(term, set()):
                if news_id not in matches:
                    matches[news_id] = IndexEntry(news_id)
                matches[news_id].title_matches += 1
            
            # Description matches (medium weight)
            for news_id in self.description_index.get(term, set()):
                if news_id not in matches:
                    matches[news_id] = IndexEntry(news_id)
                matches[news_id].description_matches += 1
            
            # Category matches (lower weight)
            for news_id in self.category_index.get(term, set()):
                if news_id not in matches:
                    matches[news_id] = IndexEntry(news_id)
                matches[news_id].category_matches += 1
        
        # Calculate relevance scores
        for entry in matches.values():
            # Weighted scoring: title > description > category
            entry.total_score = (
                entry.title_matches * 3.0 +
                entry.description_matches * 1.0 +
                entry.category_matches * 0.5
            )
            
            # Bonus for exact query match
            if news_id in self.documents:
                doc = self.documents[news_id]
                query_lower = query.lower()
                
                if query_lower in doc['title'].lower():
                    entry.total_score += 2.0
                elif query_lower in doc['description'].lower():
                    entry.total_score += 1.0
                elif query_lower in doc['category'].lower():
                    entry.total_score += 0.5
        
        # Sort by score and return top results
        sorted_matches = sorted(
            matches.values(),
            key=lambda x: x.total_score,
            reverse=True
        )
        
        return [(entry.news_id, entry.total_score) for entry in sorted_matches[:limit]]
    
    async def initialize_from_database(self, NewsSchema) -> None:
        """Initialize the index by loading all existing news items"""
        logger.info("Initializing reverse index from database...")
        
        try:
            # Load all news items
            all_news = await NewsSchema.all()
            
            for news_item in all_news:
                self.add_document(news_item)
            
            self.is_initialized = True
            logger.info(f"Reverse index initialized with {len(self.documents)} documents")
            
        except Exception as e:
            logger.error(f"Failed to initialize reverse index: {e}")
            raise
    
    def get_stats(self) -> Dict[str, int]:
        """Get index statistics"""
        return {
            'total_documents': len(self.documents),
            'title_terms': len(self.title_index),
            'description_terms': len(self.description_index),
            'category_terms': len(self.category_index),
            'total_terms': len(self.title_index) + len(self.description_index) + len(self.category_index)
        }

# Global index instance
news_index = ReverseIndex()

async def initialize_search_index(NewsSchema):
    """Initialize the search index on startup"""
    await news_index.initialize_from_database(NewsSchema)

def add_news_to_index(news_item):
    """Add a new news item to the index (call this when creating news)"""
    news_index.add_document(news_item)

def remove_news_from_index(news_id: int):
    """Remove a news item from the index (call this when deleting news)"""
    news_index.remove_document(news_id)

async def search_news_fast(query: str, limit: int = 10) -> List[int]:
    """
    Fast search using the reverse index.
    Returns list of news IDs sorted by relevance.
    """
    if not news_index.is_initialized:
        logger.warning("Search index not initialized, falling back to database search")
        return []
    
    results = news_index.search(query, limit)
    return [news_id for news_id, score in results]

# Integration with your existing NewsSchema

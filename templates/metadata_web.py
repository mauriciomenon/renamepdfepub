from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import List, Optional, Dict
import sqlite3
import pandas as pd
from pathlib import Path

app = FastAPI(title="Metadata Cache Explorer")
templates = Jinja2Templates(directory="templates")

def dict_factory(cursor, row):
    """Converte resultado do SQLite em dicionário."""
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    try:
        with sqlite3.connect('../metadata_cache.db') as conn:
            total = conn.execute("SELECT COUNT(*) FROM metadata_cache").fetchone()[0]
            sources = conn.execute(
                "SELECT GROUP_CONCAT(DISTINCT source) FROM metadata_cache"
            ).fetchone()[0]
    except Exception as e:
        print(f"Erro ao acessar banco: {e}")
        total = 0
        sources = ""

    return templates.TemplateResponse(
        "home.html", 
        {
            "request": request,
            "total_records": total,
            "sources": sources
        }
    )

@app.get("/search", response_class=HTMLResponse)
async def search(request: Request, q: Optional[str] = None):
    try:
        with sqlite3.connect('../metadata_cache.db') as conn:
            conn.row_factory = dict_factory
            cur = conn.cursor()
            
            if q:
                pattern = f"%{q}%"
                results = cur.execute("""
                    SELECT isbn_10, isbn_13, title, authors, publisher, source, confidence_score
                    FROM metadata_cache
                    WHERE title LIKE ? 
                       OR authors LIKE ? 
                       OR isbn_13 LIKE ? 
                       OR isbn_10 LIKE ?
                    ORDER BY confidence_score DESC
                """, (pattern, pattern, pattern, pattern)).fetchall()
            else:
                results = cur.execute("""
                    SELECT isbn_10, isbn_13, title, authors, publisher, source, confidence_score
                    FROM metadata_cache
                    ORDER BY confidence_score DESC
                    LIMIT 100
                """).fetchall()
            
            # Formata os resultados
            for result in results:
                if 'confidence_score' in result:
                    result['confidence_score'] = f"{float(result['confidence_score']):.2f}"
                if 'authors' in result and isinstance(result['authors'], str):
                    result['authors'] = result['authors'].split(', ')
                    
    except Exception as e:
        print(f"Erro na busca: {e}")
        results = []

    return templates.TemplateResponse(
        "search.html", 
        {
            "request": request,
            "results": results,
            "query": q or ""
        }
    )
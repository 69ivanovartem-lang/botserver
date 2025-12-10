from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import sqlite3
import networkx as nx
from datetime import datetime
import tempfile
import os
import io
import html
import random
import time
from pyvis.network import Network
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import logging

app = FastAPI(title="Zettelkasten API")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Модели данных
class NoteCreate(BaseModel):
    user_id: int
    title: str
    content: str
    tags: Optional[str] = None

class NoteResponse(BaseModel):
    id: int
    user_id: int
    title: str
    content: str
    tags: Optional[str]
    created_at: str

class LinkCreate(BaseModel):
    from_note_id: int
    to_note_id: int
    user_id: int

# База данных
class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    tags TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS note_links (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    from_note_id INTEGER NOT NULL,
                    to_note_id INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (from_note_id) REFERENCES notes (id),
                    FOREIGN KEY (to_note_id) REFERENCES notes (id)
                )
            ''')
            conn.commit()
    
    def add_note(self, note: NoteCreate) -> int:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO notes (user_id, title, content, tags)
                VALUES (?, ?, ?, ?)
            ''', (note.user_id, note.title, note.content, note.tags))
            conn.commit()
            return cursor.lastrowid
    
    def get_user_notes(self, user_id: int) -> List[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, user_id, title, content, tags, created_at 
                FROM notes 
                WHERE user_id = ? 
                ORDER BY created_at DESC
            ''', (user_id,))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_note(self, note_id: int, user_id: int) -> Optional[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM notes 
                WHERE id = ? AND user_id = ?
            ''', (note_id, user_id))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def search_notes(self, user_id: int, query: str) -> List[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            search_pattern = f'%{query}%'
            cursor.execute('''
                SELECT id, title, content, tags 
                FROM notes 
                WHERE user_id = ? 
                AND (title LIKE ? OR content LIKE ? OR tags LIKE ?)
                ORDER BY created_at DESC
            ''', (user_id, search_pattern, search_pattern, search_pattern))
            return [dict(row) for row in cursor.fetchall()]
    
    def add_link(self, link: LinkCreate) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # Проверяем, что обе заметки принадлежат пользователю
            cursor.execute('''
                SELECT 1 FROM notes 
                WHERE id = ? AND user_id = ?
            ''', (link.from_note_id, link.user_id))
            if not cursor.fetchone():
                return False
            
            cursor.execute('''
                SELECT 1 FROM notes 
                WHERE id = ? AND user_id = ?
            ''', (link.to_note_id, link.user_id))
            if not cursor.fetchone():
                return False
            
            cursor.execute('''
                INSERT INTO note_links (from_note_id, to_note_id)
                VALUES (?, ?)
            ''', (link.from_note_id, link.to_note_id))
            conn.commit()
            return True
    
    def delete_note(self, note_id: int, user_id: int) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                DELETE FROM note_links 
                WHERE from_note_id = ? OR to_note_id = ?
            ''', (note_id, note_id))
            cursor.execute('''
                DELETE FROM notes 
                WHERE id = ? AND user_id = ?
            ''', (note_id, user_id))
            conn.commit()
            return cursor.rowcount > 0
    
    def get_all_notes_graph(self, user_id: int):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, title FROM notes WHERE user_id = ?
            ''', (user_id,))
            notes = {row[0]: row[1] for row in cursor.fetchall()}
            
            cursor.execute('''
                SELECT from_note_id, to_note_id FROM note_links
                WHERE from_note_id IN (SELECT id FROM notes WHERE user_id = ?)
                AND to_note_id IN (SELECT id FROM notes WHERE user_id = ?)
            ''', (user_id, user_id))
            
            graph = {}
            for from_id, to_id in cursor.fetchall():
                if from_id not in graph:
                    graph[from_id] = []
                if to_id not in graph:
                    graph[to_id] = []
                graph[from_id].append(to_id)
                graph[to_id].append(from_id)
            
            return notes, graph

# Инициализация базы данных
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///data/zettelkasten.db")
if DATABASE_URL.startswith("sqlite:///"):
    db_path = DATABASE_URL.replace("sqlite:///", "")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
else:
    db_path = "zettelkasten.db"

db = Database(db_path)

# Инициализация Selenium драйвера
driver = None

def init_selenium():
    global driver
    try:
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1200,800")
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        return True
    except Exception as e:
        logging.error(f"Selenium init failed: {e}")
        return False

# API endpoints
@app.get("/")
def read_root():
    return {"message": "Zettelkasten API", "status": "running"}

@app.post("/api/notes", response_model=Dict[str, Any])
def create_note(note: NoteCreate):
    note_id = db.add_note(note)
    return {"id": note_id, "message": "Note created", "status": "success"}

@app.get("/api/notes/{user_id}", response_model=List[NoteResponse])
def get_notes(user_id: int):
    notes = db.get_user_notes(user_id)
    return notes

@app.get("/api/notes/{user_id}/search")
def search_notes(user_id: int, q: str):
    notes = db.search_notes(user_id, q)
    return notes

@app.get("/api/notes/{user_id}/graph")
def get_notes_graph(user_id: int):
    notes, graph = db.get_all_notes_graph(user_id)
    return {"notes": notes, "graph": graph}

@app.post("/api/links")
def create_link(link: LinkCreate):
    success = db.add_link(link)
    if success:
        return {"message": "Link created", "status": "success"}
    raise HTTPException(status_code=400, detail="Cannot create link")

@app.delete("/api/notes/{note_id}")
def delete_note(note_id: int, user_id: int):
    success = db.delete_note(note_id, user_id)
    if success:
        return {"message": "Note deleted", "status": "success"}
    raise HTTPException(status_code=404, detail="Note not found")

@app.get("/api/notes/{user_id}/visualize")
def visualize_graph(user_id: int):
    """Создание визуализации графа (HTML + изображение)"""
    notes, graph = db.get_all_notes_graph(user_id)
    if not notes:
        raise HTTPException(status_code=404, detail="No notes found")
    
    # Здесь должна быть логика создания графа как в вашем оригинальном коде
    # (функция create_enhanced_graph_visualization)
    
    return {"message": "Visualization endpoint", "notes_count": len(notes)}

# Инициализация при старте
init_selenium()

@app.on_event("shutdown")
def shutdown_event():
    global driver
    if driver:
        driver.quit()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
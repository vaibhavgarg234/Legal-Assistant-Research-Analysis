import sqlite3
import os
from typing import List, Dict, Any
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), 'chat_history.db')

def init_db():
    """Initialize the database and create tables if they don't exist."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Create threads table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS threads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            thread_id TEXT UNIQUE NOT NULL,
            user_id TEXT NOT NULL,
            title TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Create messages table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            thread_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (thread_id) REFERENCES threads (thread_id) ON DELETE CASCADE
        )
    ''')

    conn.commit()
    conn.close()

def save_thread(user_id: str, thread_id: str, title: str = None):
    """Save or update a thread, preserving meaningful title if not specified."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('SELECT title FROM threads WHERE thread_id = ?', (thread_id,))
    row = cursor.fetchone()
    if row:
        existing_title = row[0]
        # Keep existing title if new title is not explicitly provided or is default
        new_title = title if (title and not title.startswith("Chat 20")) else existing_title
        cursor.execute('''
            UPDATE threads SET user_id = ?, title = ?, updated_at = ?
            WHERE thread_id = ?
        ''', (user_id or "default_user", new_title, datetime.now(), thread_id))
    else:
        cursor.execute('''
            INSERT INTO threads (thread_id, user_id, title, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (thread_id, user_id or "default_user", title or f"Chat {datetime.now().strftime('%Y-%m-%d %H:%M')}", datetime.now(), datetime.now()))

    conn.commit()
    conn.close()

def save_message(thread_id: str, role: str, content: str):
    """Save a message to the database and ensure thread exists."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Ensure thread exists in threads table
    cursor.execute('SELECT 1 FROM threads WHERE thread_id = ?', (thread_id,))
    if not cursor.fetchone():
        title = content[:50].strip() + ("..." if len(content) > 50 else "") if role == "user" else f"Chat {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        cursor.execute('''
            INSERT INTO threads (thread_id, user_id, title, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (thread_id, "default_user", title, datetime.now(), datetime.now()))
    else:
        cursor.execute('''
            UPDATE threads SET updated_at = ? WHERE thread_id = ?
        ''', (datetime.now(), thread_id))

    cursor.execute('''
        INSERT INTO messages (thread_id, role, content)
        VALUES (?, ?, ?)
    ''', (thread_id, role, content))

    conn.commit()
    conn.close()

def get_user_threads(user_id: str = None) -> List[Dict[str, Any]]:
    """Get all threads for a user, or all threads if default/none."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    if user_id and user_id not in ("default_user", "anonymous", ""):
        cursor.execute('''
            SELECT thread_id, title, created_at, updated_at
            FROM threads
            WHERE user_id = ? OR user_id = 'default_user'
            ORDER BY updated_at DESC
        ''', (user_id,))
    else:
        cursor.execute('''
            SELECT thread_id, title, created_at, updated_at
            FROM threads
            ORDER BY updated_at DESC
        ''')

    threads = []
    for row in cursor.fetchall():
        threads.append({
            'thread_id': row[0],
            'title': row[1],
            'created_at': row[2],
            'updated_at': row[3]
        })

    conn.close()
    return threads

def get_thread_messages(thread_id: str) -> List[Dict[str, Any]]:
    """Get all messages for a thread."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT role, content, timestamp
        FROM messages
        WHERE thread_id = ?
        ORDER BY timestamp ASC
    ''', (thread_id,))

    messages = []
    for row in cursor.fetchall():
        messages.append({
            'role': row[0],
            'content': row[1],
            'timestamp': row[2]
        })

    conn.close()
    return messages

def delete_thread(thread_id: str):
    """Delete a thread and its messages."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('DELETE FROM threads WHERE thread_id = ?', (thread_id,))
    cursor.execute('DELETE FROM messages WHERE thread_id = ?', (thread_id,))

    conn.commit()
    conn.close()

# Initialize DB on import
init_db()

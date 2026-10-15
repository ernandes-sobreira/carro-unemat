"""Banco compartilhado SQLite; use volume persistente em produção."""
from __future__ import annotations
import os, sqlite3, json, hashlib, secrets, base64
from datetime import datetime, timezone
from pathlib import Path
BASE=Path(__file__).resolve().parent
DB=Path(os.getenv('PPGCA_DATABASE',str(BASE/'data'/'ppgca.sqlite3')))

def connect():
    DB.parent.mkdir(parents=True,exist_ok=True)
    c=sqlite3.connect(str(DB), timeout=15)
    c.row_factory=sqlite3.Row
    c.execute('PRAGMA foreign_keys=ON')
    c.execute('PRAGMA busy_timeout=15000')
    c.execute('PRAGMA journal_mode=WAL')
    return c

def init():
    with connect() as c:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, username TEXT UNIQUE NOT NULL, display_name TEXT NOT NULL, password_hash TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'editor', active INTEGER DEFAULT 1);
        CREATE TABLE IF NOT EXISTS requests(id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'rascunho', data TEXT NOT NULL, created_by INTEGER NOT NULL REFERENCES users(id), updated_by INTEGER NOT NULL REFERENCES users(id), created_at TEXT NOT NULL, updated_at TEXT NOT NULL, archived INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY AUTOINCREMENT, request_id INTEGER NOT NULL REFERENCES requests(id), user_id INTEGER NOT NULL REFERENCES users(id), action TEXT NOT NULL, at TEXT NOT NULL, detail TEXT NOT NULL DEFAULT '');
        CREATE INDEX IF NOT EXISTS idx_requests_updated ON requests(updated_at DESC);
        CREATE TABLE IF NOT EXISTS contacts(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE COLLATE NOCASE NOT NULL, phone TEXT NOT NULL DEFAULT '', bond TEXT NOT NULL DEFAULT '', updated_by INTEGER REFERENCES users(id), updated_at TEXT NOT NULL);
        ''')
        # Create only missing accounts from secure deployment environment hashes.
        for username, display, role, env in (
            ('ernandes','Ernandes Sobreira Oliveira Junior','admin','PPGCA_ER_PASSWORD_HASH'),
            ('maria','Maria Ribeiro','editor','PPGCA_MARIA_PASSWORD_HASH'),
        ):
            hashed=os.getenv(env,'')
            if hashed.startswith('scrypt$'):
                c.execute('INSERT OR IGNORE INTO users(username,display_name,password_hash,role) VALUES (?,?,?,?)',
                          (username,display,hashed,role))

def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')

def hash_password(password):
    salt=os.urandom(16); digest=hashlib.scrypt(password.encode(),salt=salt,n=16384,r=8,p=1,dklen=32)
    return 'scrypt$'+base64.urlsafe_b64encode(salt).decode()+'$'+base64.urlsafe_b64encode(digest).decode()

def check_password(password, stored):
    try:
        alg,salt,digest=stored.split('$')
        if alg!='scrypt':return False
        actual=hashlib.scrypt(password.encode(),salt=base64.urlsafe_b64decode(salt),n=16384,r=8,p=1,dklen=32)
        return secrets.compare_digest(actual,base64.urlsafe_b64decode(digest))
    except Exception:return False

def get_secret():
    val=os.getenv('PPGCA_SESSION_SECRET','').strip()
    if val and len(val)>=32:return val
    path=DB.parent/'.session_secret'
    if not path.exists():
        fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,'w') as f:f.write(secrets.token_urlsafe(48))
    return path.read_text().strip()

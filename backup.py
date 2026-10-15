"""Cópia consistente do banco, com UTC no nome; execute periodicamente."""
from pathlib import Path
from datetime import datetime,timezone
import sqlite3
from db import connect,DB

if __name__=='__main__':
    out=DB.parent/'backups';out.mkdir(parents=True,exist_ok=True)
    dest=out/('PPGCA-veiculos-'+datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')+'.sqlite3')
    with connect() as src, sqlite3.connect(dest) as dst:src.backup(dst)
    print('Backup salvo em:',dest)

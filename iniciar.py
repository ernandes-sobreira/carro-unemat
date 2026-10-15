"""Inicializador simples para Windows/macOS/Linux.
No primeiro acesso cria as contas. Depois abre o navegador."""
import subprocess,sys,webbrowser,threading
from pathlib import Path
from db import connect,init
import uvicorn

ROOT=Path(__file__).resolve().parent
if __name__=='__main__':
    init()
    with connect() as c:
        existing={r[0] for r in c.execute('SELECT username FROM users')}
    if not {'ernandes','maria'}.issubset(existing):
        print('\nPRIMEIRA EXECUÇÃO — defina senhas para Ernandes e Maria.\n')
        r=subprocess.call([sys.executable,str(ROOT/'setup.py')])
        if r:raise SystemExit('Configuração incompleta. Execute novamente.')
    print('\nAbra: http://127.0.0.1:8000\nAperte CTRL+C nesta janela para encerrar.\n')
    threading.Timer(2,lambda:webbrowser.open('http://127.0.0.1:8000')).start()
    uvicorn.run('app:app',host='127.0.0.1',port=8000,log_level='warning')

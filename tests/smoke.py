"""Teste de integração isolado; não toca no banco real."""
import os,tempfile,sys,asyncio
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
TMP=tempfile.TemporaryDirectory(prefix='ppgca_testdb_')
os.environ['PPGCA_DATABASE']=str(Path(TMP.name)/'test.sqlite3')
from db import connect,hash_password
from app import app
from documents import EXAMPLE
from httpx import AsyncClient,ASGITransport
from docx import Document
import io,fitz

async def run():
    with connect() as c:
        c.execute('INSERT INTO users(username,display_name,password_hash,role) VALUES(?,?,?,?)',('ernandes','Ernandes Sobreira Oliveira Junior',hash_password('SenhaSeguraDeTeste2026'),'admin'))
        c.execute('INSERT INTO users(username,display_name,password_hash,role) VALUES(?,?,?,?)',('maria','Maria Ribeiro',hash_password('SenhaSeguraDeTeste2027'),'editor'))
    async with AsyncClient(transport=ASGITransport(app=app),base_url='http://testserver',follow_redirects=False) as c:
        assert (await c.get('/')).status_code==303
        login=await c.get('/login');assert login.status_code==200
        from re import search
        token=search(r'name="token" value="([^"]+)"',login.text).group(1)
        bad=await c.post('/login',data={'username':'ernandes','password':'nao','token':token});assert bad.status_code==401
        ok=await c.post('/login',data={'username':'ernandes','password':'SenhaSeguraDeTeste2026','token':token})
        assert ok.status_code==303
        root=await c.get('/');assert root.status_code==200
        token=search(r'"csrf":\s*"([^"]+)"',root.text).group(1)
        h={'X-CSRF-Token':token}
        no=await c.post('/api/requests',json={'data':EXAMPLE});assert no.status_code==403
        created=await c.post('/api/requests',headers=h,json={'title':'Workshop de carbono','data':EXAMPLE,'submit':True})
        assert created.status_code==200,created.text
        rid=created.json()['id'];assert created.json()['status']=='enviada'
        d=await c.get(f'/api/requests/{rid}');assert d.status_code==200
        word=await c.get(f'/requests/{rid}/docx');assert word.status_code==200
        doc=Document(io.BytesIO(word.content));assert 'atividade acadêmica' in doc.tables[0].cell(1,1).text
        pdf=await c.get(f'/requests/{rid}/pdf');assert pdf.status_code==200
        assert len(fitz.open(stream=pdf.content,filetype='pdf'))==1
        audit=await c.get(f'/api/requests/{rid}/audit');assert len(audit.json())==1
        status=await c.post(f'/api/requests/{rid}/status',headers=h,json={'status':'aprovada'});assert status.status_code==200
        copy=await c.post(f'/api/requests/{rid}/duplicate',headers=h);assert copy.status_code==200
        idx=await c.get('/api/requests');assert len(idx.json())==2
        cr=await c.post('/api/contacts',headers=h,json={'name':'Pessoa para teste','phone':'(65) 99999-9999','bond':'Docente'})
        assert cr.status_code==200
        # Troca usuário na mesma instalação; vê os registros do outro.
        logout=await c.post('/logout',data={'token':token});assert logout.status_code==303
        login=await c.get('/login');token=search(r'name="token" value="([^"]+)"',login.text).group(1)
        ok=await c.post('/login',data={'username':'maria','password':'SenhaSeguraDeTeste2027','token':token});assert ok.status_code==303
        idx=await c.get('/api/requests');assert len(idx.json())==2
        ct=await c.get('/api/contacts');assert ct.status_code==200 and len(ct.json())==1
        root=await c.get('/');token=search(r'"csrf":\s*"([^"]+)"',root.text).group(1)
        # Só rascunhos/pendências podem ser alterados.
        edit=await c.put(f'/api/requests/{rid}',headers={'X-CSRF-Token':token},json={'data':EXAMPLE})
        assert edit.status_code==200
    print('SMOKE PASS — duas contas, CSRF, CRUD, cadastro compartilhado, status, DOCX, PDF 1 página e histórico')

asyncio.run(run())

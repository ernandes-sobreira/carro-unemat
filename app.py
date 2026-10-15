"""PPGCA • Solicitações de Veículos — formulário oficial preservado."""
from __future__ import annotations
import os, json, io, re, secrets, tempfile, subprocess, shutil
from pathlib import Path
from fastapi import FastAPI, Request, Form, Depends, HTTPException, Response
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from db import connect,init,now,get_secret,check_password,hash_password
from documents import create_docx
from pdf_template import main_pdf

BASE=Path(__file__).resolve().parent
init()
app=FastAPI(title='PPGCA | Solicitação de Veículos',docs_url=None,redoc_url=None,openapi_url=None)
app.add_middleware(SessionMiddleware, secret_key=get_secret(),session_cookie='ppgca_session',same_site='strict',max_age=60*60*12,https_only=os.getenv('PPGCA_HTTPS','').lower()=='true')
app.mount('/static',StaticFiles(directory=BASE/'static'),name='static')
templates=Jinja2Templates(directory=BASE/'templates')
FAIL={}
STATUS={'rascunho','enviada','em_analise','ajustes','aprovada','concluida','cancelada'}
ACTIVITY={'aula','estagio','coleta','eventos','visita','outros'}
VEHICLE={'carro','caminhonete','doblo','van','onibus36','onibus44'}
DRIVER={'ambos','partida','retorno'}

@app.middleware('http')
async def add_headers(req,call_next):
    resp=await call_next(req)
    resp.headers['X-Content-Type-Options']='nosniff'
    resp.headers['X-Frame-Options']='SAMEORIGIN'
    resp.headers['Referrer-Policy']='no-referrer'
    resp.headers['Cache-Control']='no-store'
    resp.headers['Content-Security-Policy']="default-src 'self'; style-src 'self'; script-src 'self'; img-src 'self' data:; frame-src 'self'; object-src 'self'; base-uri 'none'; form-action 'self'"
    return resp

def user(req:Request):
    uid=req.session.get('uid')
    if not uid:raise HTTPException(401,'Faça login para continuar.')
    with connect() as c:
        row=c.execute('SELECT id,username,display_name,role FROM users WHERE id=? AND active=1',(uid,)).fetchone()
    if not row:raise HTTPException(401,'Sua sessão expirou.')
    return dict(row)

def csrf(req):
    token=req.session.get('csrf')
    if not token:
        token=secrets.token_urlsafe(24)
        req.session['csrf']=token
    return token

def require_csrf(req:Request):
    val=req.headers.get('x-csrf-token','')
    if not val or not secrets.compare_digest(val,req.session.get('csrf','')):
        raise HTTPException(403,'Token de segurança inválido. Atualize a página.')

@app.get('/login',response_class=HTMLResponse)
def login_page(req:Request):
    if req.session.get('uid'):
        return RedirectResponse('/',303)
    return templates.TemplateResponse(req,'login.html',{'csrf':csrf(req),'error':None})

@app.post('/login',response_class=HTMLResponse)
def login(req:Request,username:str=Form(...),password:str=Form(...),token:str=Form(...)):
    if not secrets.compare_digest(token,req.session.get('csrf','')):
        return templates.TemplateResponse(req,'login.html',{'csrf':csrf(req),'error':'Sessão inválida; atualize a página.'},status_code=403)
    username=username.lower().strip()[:80]
    key=(req.client.host if req.client else '',username)
    from time import monotonic
    count,last=FAIL.get(key,(0,0))
    if count>=8 and monotonic()-last<300:
        return templates.TemplateResponse(req,'login.html',{'csrf':csrf(req),'error':'Muitas tentativas. Aguarde cinco minutos.'},status_code=429)
    with connect() as c:
        row=c.execute('SELECT id,password_hash FROM users WHERE username=? AND active=1',(username,)).fetchone()
    if not row or not check_password(password,row['password_hash']):
        FAIL[key]=(count+1 if monotonic()-last<300 else 1,monotonic())
        return templates.TemplateResponse(req,'login.html',{'csrf':csrf(req),'error':'Usuário ou senha incorretos.'},status_code=401)
    FAIL.pop(key,None)
    req.session.clear();req.session['uid']=row['id'];csrf(req)
    return RedirectResponse('/',303)

@app.post('/logout')
def logout(req:Request,token:str=Form(...),u=Depends(user)):
    if not secrets.compare_digest(token,req.session.get('csrf','')):raise HTTPException(403)
    req.session.clear();return RedirectResponse('/login',303)

@app.head('/')
def head_root():
    return Response(status_code=200)

@app.get('/',response_class=HTMLResponse)
def index(req:Request):
    try:
        u=user(req)
    except HTTPException:
        return RedirectResponse('/login',status_code=303)
    return templates.TemplateResponse(req,'index.html',{'csrf':csrf(req),'user':u})

def get_request(rid:int):
    with connect() as c:
        r=c.execute('SELECT r.*,u.display_name AS author FROM requests r JOIN users u ON r.created_by=u.id WHERE r.id=? AND r.archived=0',(rid,)).fetchone()
    if not r:raise HTTPException(404,'Solicitação não localizada.')
    out=dict(r);out['data']=json.loads(out['data']);return out

@app.get('/api/requests')
def request_list(u=Depends(user)):
    with connect() as c:
        rows=c.execute('SELECT r.id,r.title,r.status,r.updated_at,r.created_at,u.display_name AS author FROM requests r JOIN users u ON r.created_by=u.id WHERE r.archived=0 ORDER BY r.updated_at DESC LIMIT 400').fetchall()
    return [dict(r) for r in rows]

@app.get('/api/requests/{rid}')
def detail(rid:int,u=Depends(user)):
    return get_request(rid)

def validate(data:dict,strict:bool=False):
    if not isinstance(data,dict):raise HTTPException(422,'Os dados precisam ser um objeto.')
    out={}
    keys=['description','departure_date','departure_time','departure_from','departure_to','return_date','return_time','return_from','return_to']
    for k in keys:
        val=str(data.get(k) or '').strip()
        if len(val)>({ 'description':4200 }.get(k,300)):
            raise HTTPException(422,'Texto muito longo: '+k)
        out[k]=val
    for k,opts in [('activity',ACTIVITY),('vehicle',VEHICLE),('driver_trip',DRIVER)]:
        val=str(data.get(k) or '')
        if val and val not in opts:raise HTTPException(422,'Escolha inválida: '+k)
        out[k]=val
    out['driver_stays']=data.get('driver_stays') is True
    out['has_return']=data.get('has_return') is True
    people=data.get('passengers') or []
    if not isinstance(people,list) or len(people)>44:raise HTTPException(422,'O máximo é de 44 passageiros.')
    out['passengers']=[]
    for p in people:
        if not isinstance(p,dict):raise HTTPException(422,'Passageiro inválido.')
        obj={k:str(p.get(k) or '').strip() for k in ('name','phone','bond')}
        if any(len(v)>130 for v in obj.values()):raise HTTPException(422,'Dados do passageiro muito longos.')
        if any(obj.values()):out['passengers'].append(obj)
    if strict:
        needed={'activity':'atividade','description':'descrição','vehicle':'veículo','driver_trip':'atividade do motorista','departure_date':'data da partida','departure_time':'horário','departure_from':'local de saída','departure_to':'destino'}
        empty=[label for k,label in needed.items() if not out[k]]
        if not out['passengers'] or any(not p['name'] for p in out['passengers']):empty.append('nome dos passageiros')
        if out['has_return'] and any(not out[k] for k in ('return_date','return_time','return_from','return_to')):empty.append('itinerário de retorno')
        if empty:raise HTTPException(422,'Complete antes de enviar: '+', '.join(empty)+'.')
    return out

async def json_req(req):
    try:return await req.json()
    except Exception:raise HTTPException(400,'JSON inválido.')

@app.post('/api/requests')
async def create(req:Request,u=Depends(user)):
    require_csrf(req)
    body=await json_req(req)
    status='enviada' if body.get('submit') else 'rascunho'
    data=validate(body.get('data',{}),strict=status=='enviada')
    title=str(body.get('title') or ('Viagem para '+(data['departure_to'] or 'destino a definir'))).strip()[:140]
    stamp=now()
    with connect() as c:
        cursor=c.execute('INSERT INTO requests(title,status,data,created_by,updated_by,created_at,updated_at) VALUES(?,?,?,?,?,?,?)',(title,status,json.dumps(data,ensure_ascii=False),u['id'],u['id'],stamp,stamp))
        rid=cursor.lastrowid
        c.execute('INSERT INTO audit(request_id,user_id,action,at,detail) VALUES(?,?,?,?,?)',(rid,u['id'],'criada',stamp,status))
    return {'id':rid,'status':status}

@app.put('/api/requests/{rid}')
async def update(rid:int,req:Request,u=Depends(user)):
    require_csrf(req)
    old=get_request(rid)
    if old['status'] in ('concluida','cancelada'):
        raise HTTPException(409,'Solicitação encerrada; duplique-a para editar.')
    body=await json_req(req)
    data=validate(body.get('data',{}),strict=old['status'] not in ('rascunho','ajustes'))
    title=str(body.get('title') or old['title']).strip()[:140]
    stamp=now()
    with connect() as c:
        c.execute('UPDATE requests SET title=?,data=?,updated_by=?,updated_at=? WHERE id=?',(title,json.dumps(data,ensure_ascii=False),u['id'],stamp,rid))
        c.execute('INSERT INTO audit(request_id,user_id,action,at,detail) VALUES(?,?,?,?,?)',(rid,u['id'],'editada',stamp,''))
    return {'id':rid,'status':old['status']}

@app.post('/api/requests/{rid}/status')
async def change_status(rid:int,req:Request,u=Depends(user)):
    require_csrf(req);old=get_request(rid);body=await json_req(req)
    status=body.get('status','')
    if status not in STATUS:raise HTTPException(422,'Situação inválida.')
    if status not in ('rascunho','ajustes','cancelada'):
        validate(old['data'],strict=True)
    stamp=now()
    with connect() as c:
        c.execute('UPDATE requests SET status=?,updated_by=?,updated_at=? WHERE id=?',(status,u['id'],stamp,rid))
        c.execute('INSERT INTO audit(request_id,user_id,action,at,detail) VALUES(?,?,?,?,?)',(rid,u['id'],'situação alterada',stamp,old['status']+' → '+status))
    return {'id':rid,'status':status}

@app.post('/api/requests/{rid}/duplicate')
def duplicate(rid:int,req:Request,u=Depends(user)):
    require_csrf(req);old=get_request(rid);stamp=now()
    with connect() as c:
        cur=c.execute('INSERT INTO requests(title,status,data,created_by,updated_by,created_at,updated_at) VALUES(?,?,?,?,?,?,?)',(old['title']+' (cópia)','rascunho',json.dumps(old['data'],ensure_ascii=False),u['id'],u['id'],stamp,stamp))
        nid=cur.lastrowid
        c.execute('INSERT INTO audit(request_id,user_id,action,at,detail) VALUES(?,?,?,?,?)',(nid,u['id'],'duplicada',stamp,f'da solicitação #{rid}'))
    return {'id':nid}

@app.post('/api/requests/{rid}/archive')
def archive(rid:int,req:Request,u=Depends(user)):
    require_csrf(req);get_request(rid);stamp=now()
    with connect() as c:
        c.execute('UPDATE requests SET archived=1,updated_by=?,updated_at=? WHERE id=?',(u['id'],stamp,rid))
        c.execute('INSERT INTO audit(request_id,user_id,action,at,detail) VALUES(?,?,?,?,?)',(rid,u['id'],'arquivada',stamp,''))
    return {'ok':True}

@app.get('/api/requests/{rid}/audit')
def audit(rid:int,u=Depends(user)):
    get_request(rid)
    with connect() as c:
        rows=c.execute('SELECT a.action,a.at,a.detail,u.display_name AS person FROM audit a JOIN users u ON a.user_id=u.id WHERE a.request_id=? ORDER BY a.id DESC',(rid,)).fetchall()
    return [dict(r) for r in rows]


@app.get('/api/contacts')
def contacts_list(u=Depends(user)):
    with connect() as c:
        return [dict(x) for x in c.execute('SELECT id,name,phone,bond FROM contacts ORDER BY name COLLATE NOCASE').fetchall()]

@app.post('/api/contacts')
async def contacts_save(req:Request,u=Depends(user)):
    require_csrf(req);d=await json_req(req)
    name=str(d.get('name') or '').strip();phone=str(d.get('phone') or '').strip();bond=str(d.get('bond') or '').strip()
    if not name or any(len(v)>130 for v in (name,phone,bond)):raise HTTPException(422,'Preencha nome e confira o tamanho dos campos.')
    with connect() as c:
        c.execute('INSERT INTO contacts(name,phone,bond,updated_by,updated_at) VALUES(?,?,?,?,?) ON CONFLICT(name) DO UPDATE SET phone=excluded.phone,bond=excluded.bond,updated_by=excluded.updated_by,updated_at=excluded.updated_at',(name,phone,bond,u['id'],now()))
    return {'ok':True}

@app.post('/api/change-password')
async def password(req:Request,u=Depends(user)):
    require_csrf(req);d=await json_req(req)
    old=str(d.get('old') or '');new=str(d.get('new') or '')
    if len(new)<12:raise HTTPException(422,'Nova senha precisa ter pelo menos 12 caracteres.')
    with connect() as c:
        old_hash=c.execute('SELECT password_hash FROM users WHERE id=?',(u['id'],)).fetchone()['password_hash']
        if not check_password(old,old_hash):raise HTTPException(403,'Senha atual incorreta.')
        c.execute('UPDATE users SET password_hash=? WHERE id=?',(hash_password(new),u['id']))
    return {'ok':True}

@app.get('/requests/{rid}/docx')
def docx(rid:int,u=Depends(user)):
    data=get_request(rid)
    content=create_docx(data['data'])
    name=f'PPGCA_solicitacao_veiculo_{rid}.docx'
    return StreamingResponse(io.BytesIO(content),media_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',headers={'Content-Disposition':f'attachment; filename="{name}"'})

def convert_pdf(content:bytes) -> bytes:
    exe=shutil.which('libreoffice') or shutil.which('soffice')
    if not exe:raise HTTPException(503,'PDF indisponível no servidor: instale LibreOffice. O Word continua disponível.')
    with tempfile.TemporaryDirectory(prefix='ppgca_') as tmp:
        root=Path(tmp); inp=root/'solicitacao.docx';inp.write_bytes(content)
        profile=root/'lo-profile';profile.mkdir()
        try:
            p=subprocess.run([exe,f'-env:UserInstallation={profile.as_uri()}','--headless','--convert-to','pdf','--outdir',str(root),str(inp)],capture_output=True,text=True,timeout=45,check=False)
        except (OSError,subprocess.TimeoutExpired) as err:raise HTTPException(503,f'Falha de conversão PDF: {str(err)[:100]}')
        out=root/'solicitacao.pdf'
        if p.returncode or not out.exists() or out.stat().st_size<500:
            raise HTTPException(503,'A conversão para PDF falhou; baixe o Word.')
        return out.read_bytes()

@app.get('/requests/{rid}/pdf')
def pdf(rid:int,download:bool=False,u=Depends(user)):
    data=get_request(rid)
    try:
        content=main_pdf(data['data'])
    except (OverflowError, ValueError):
        content=None
    if content is None:
        content=convert_pdf(create_docx(data['data']))
    disp='attachment' if download else 'inline'
    return StreamingResponse(io.BytesIO(content),media_type='application/pdf',headers={'Content-Disposition':f'{disp}; filename="PPGCA_solicitacao_veiculo_{rid}.pdf"'})

@app.get('/health')
def health():
    with connect() as c:
        num=c.execute('SELECT COUNT(*) FROM users').fetchone()[0]
    return {'ok':True,'users_configured':num>0}

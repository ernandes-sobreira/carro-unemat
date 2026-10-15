"""PDF oficial: altera só campos dinâmicos do PDF de uma página fornecido.

Conserva tabela, dimensões, cores e legendas no exato arquivo de origem.
Se dados não couberem nesta página, sinaliza uso do DOCX dinâmico.
"""
from __future__ import annotations
import subprocess
from pathlib import Path
import fitz
from documents import date_br,s

SOURCE=Path(__file__).resolve().parent/'assets'/'formulario_oficial.pdf'
ACTS=['aula','estagio','coleta','eventos','visita','outros']
ORIGINAL_ACT_LABELS=['1. Aula Campo','2. Acompanhar estágio','2. Coleta','3. Participação em','4. Visita técnica','5. Outros']
ORIGINAL_VEHICLE_LABELS=['Carro de','', 'Doblô - 6','Van - 15','Ônibus','Ônibus - 44']
VEHICLES=['carro','caminhonete','doblo','van','onibus36','onibus44']
DRIVERS=['ambos','partida','retorno']
DRIVER_LABELS=['1. Partida e Retorno','2. Apenas partida (de Cáceres) - (levar)','3. Apenas retorno (para Cáceres) - (buscar)']


def main_pdf(payload:dict)->bytes|None:
    people=[x for x in payload.get('passengers',[]) if isinstance(x,dict) and any(s(x.get(k)) for k in ('name','phone','bond'))]
    if len(people)>4:return None
    pdf=fitz.open(SOURCE);page=pdf[0]
    try:
        path=subprocess.run(['fc-match','-f','%{file}','Liberation Sans'],capture_output=True,text=True,timeout=3).stdout.strip()
        if not path or not Path(path).exists():path=None
    except (OSError,subprocess.TimeoutExpired):path=None
    font=fitz.Font(fontfile=path) if path else fitz.Font('helv')
    name='PPGCALiberationSans' if path else 'helv'
    erasures=[];writes=[]
    def width(text,sz=10):return font.text_length(s(text),fontsize=sz)
    def draw(x,base,txt,maxw=None,rect=None,minsize=8.0):
        txt=s(txt)
        if rect:erasures.append(fitz.Rect(*rect))
        if not txt:return
        size=10.0
        if maxw:
            while width(txt,size)>maxw and size>=minsize+.19:size-=.2
            if width(txt,size)>maxw:raise OverflowError('Valor longo demais para o campo oficial')
        writes.append((x,base,txt,round(size,2)))
    def if_changed(x,base,new,old,limit,rect):
        if s(new)!=s(old):draw(x,base,new,limit,rect)
    # Atividade: altera o texto INTEIRO da primeira linha; assim o X não invade a legenda.
    for i,key in enumerate(ACTS):
        oldcheck=i==3; newcheck=payload.get('activity')==key
        if oldcheck==newcheck:continue
        base=[126.85,143.35,159.85,176.35,204.35,220.85][i]
        x=44.8; val=f'({" X " if newcheck else "   "}) {ORIGINAL_ACT_LABELS[i]}'
        draw(x,base,val,125,(44.65,base-10.3,173.7,base+2))
    # Descrição: cell com alinhamento vertical ao centro.
    description=s(payload.get('description'))
    if description:
        words=description.split();lines=[];cur=''
        for word in words:
            tentative=(cur+' '+word).strip()
            if width(tentative)<=369:cur=tentative
            else:
                if cur:lines.append(cur)
                cur=word
        if cur:lines.append(cur)
        if len(lines)>9 or any(width(x)>369 for x in lines):raise OverflowError('Descrição maior que o espaço disponível')
        erasures.append(fitz.Rect(179.8,115.8,555.8,224.1))
        baseline=173.8-(len(lines)-1)*5.75
        for i,v in enumerate(lines):draw(180.8,baseline+i*11.5,v)
    # Tabela de passageiros: quatro linhas como no formulário institucional.
    for i in range(4):
        p=people[i] if i<len(people) else {}
        old={'name':'','phone':'','bond':''}
        base=293.9+i*16.5
        fields=[(f'{i+1}. {s(p.get("name"))}' if s(p.get('name')) else '','',44.8,251,(44.55,base-10.1,299.5,base+2.1)),
                (s(p.get('phone')),old['phone'],305.5,107,(305.3,base-10.1,414.5,base+2.1)),
                (s(p.get('bond')),old['bond'],419.0,131,(418.8,base-10.1,552.8,base+2.1))]
        for new,oldval,x,maxw,rect in fields:if_changed(x,base,new,oldval,maxw,rect)
    # Veículos: em uma seleção diferente, substitui a linha de legenda inteira.
    vx=[44.8,129.8,214.85,291.45,367.95,461.45]
    vb=[421.6,421.6,427.35,427.35,421.6,409.1]
    end=[126.5,211.7,287.5,364.1,457.6,555.1]
    for i,key in enumerate(VEHICLES):
        oldcheck=i==0;newcheck=payload.get('vehicle')==key
        if oldcheck==newcheck:continue
        x=vx[i];base=vb[i]
        label=ORIGINAL_VEHICLE_LABELS[i]
        new=f'({" X " if newcheck else "   "})'+(' '+label if label else ' ')
        draw(x,base,new,end[i]-x-2,(x-.1,base-10.2,end[i],base+2))
    # Motorista: faz o mesmo para as três linhas, respeitando texto institucional.
    for i,key in enumerate(DRIVERS):
        oldcheck=i==1;newcheck=payload.get('driver_trip')==key
        if oldcheck==newcheck:continue
        base=518.7+i*16.5
        txt=f'({" X " if newcheck else "   "}) {DRIVER_LABELS[i]}'
        draw(44.8,base,txt,509,(44.5,base-10.1,555.5,base+2.1))
    stays=bool(payload.get('driver_stays'))
    if stays:
        txt='(   ) 4. O motorista precisa permanecer à disposição durante a viagem? ( X ) SIM ou (   ) NÃO'
        draw(44.8,568.25,txt,509,(44.5,558.2,555.1,571.7))
    # Itinerário: 4 colunas do mesmo desenho de origem.
    departure=[('PARTIDA: '+(date_br(payload.get('departure_date')) or '—'),'PARTIDA: —',44.8,128),
       ((s(payload.get('departure_time'))+' (MT)') if s(payload.get('departure_time')) else '—','—',183.6,69),
       (s(payload.get('departure_from')) or '—','—',257.4,143),
       (s(payload.get('departure_to')) or '—','—',407.6,145)]
    colbounds=[(44.1,178.3),(183.1,252.1),(257,402.6),(407.3,556)]
    for i,(val,old,x,maxw) in enumerate(departure):
        if val==old:continue
        words=val.split();parts=[];cur=''
        for w in words:
            t=(cur+' '+w).strip()
            if width(t)<=maxw:cur=t
            else:
                if cur:parts.append(cur)
                cur=w
        if cur:parts.append(cur)
        if len(parts)>2 or any(width(v)>maxw for v in parts):raise OverflowError('Local muito longo para o itinerário')
        erasures.append(fitz.Rect(colbounds[i][0],665.8,colbounds[i][1],690.6))
        first=682.1 if len(parts)==1 else 676.45
        for j,v in enumerate(parts):draw(x,first+j*11.5,v)
    if payload.get('has_return'):
        returned=[('RETORNO: '+(date_br(payload.get('return_date')) or '—'),44.8,128),
          (((s(payload.get('return_time'))+' (MT)') if s(payload.get('return_time')) else '—'),183.6,69),
          (s(payload.get('return_from')) or '—',257.4,143),
          (s(payload.get('return_to')) or '—',407.6,145)]
    else:returned=[('RETORNO: Não solicitado',44.8,128),('—',183.6,69),('—',257.4,143),('—',407.6,145)]
    oldreturn=['RETORNO: Não solicitado','—','—','—']
    for i,(val,x,maxw) in enumerate(returned):
        if_changed(x,704.4,val,oldreturn[i],maxw,(colbounds[i][0],693.8,colbounds[i][1],708.2))
    if not erasures:return SOURCE.read_bytes()
    for rect in erasures:page.add_redact_annot(rect,fill=False,cross_out=False)
    # graphics=0 mantém linhas e quadros intactos.
    page.apply_redactions(images=0,graphics=0,text=0)
    if path:page.insert_font(fontname=name,fontfile=path)
    for x,y,text,size in writes:page.insert_text((x,y),text,fontname=name,fontsize=size,color=(0,0,0),overlay=True)
    return pdf.tobytes(garbage=4,deflate=True)

"""Preenche o DOCX recebido do usuário sem recriar as tabelas originais."""
from __future__ import annotations
import io
import re
from copy import deepcopy
from pathlib import Path
from datetime import datetime
from docx import Document

TEMPLATE = Path(__file__).resolve().parent / 'assets' / 'formulario_oficial.docx'
ACTIVITIES = ['aula', 'estagio', 'coleta', 'eventos', 'visita', 'outros']
VEHICLES = ['carro', 'caminhonete', 'doblo', 'van', 'onibus36', 'onibus44']
DRIVER = ['ambos', 'partida', 'retorno']

def s(x):
    return str(x or '').strip()

def date_br(x):
    if not x:
        return ''
    try:
        return datetime.strptime(str(x)[:10], '%Y-%m-%d').strftime('%d/%m/%Y')
    except ValueError:
        return s(x)

def replace_cell(cell, value):
    """Conserva o layout e as propriedades de parágrafo e célula do Word."""
    value = s(value)
    p0 = cell.paragraphs[0]
    if not p0.runs:
        p0.add_run(value)
    else:
        p0.runs[0].text = value
        for run in p0.runs[1:]:
            run.text = ''
    for p in cell.paragraphs[1:]:
        for run in p.runs:
            run.text = ''

def replace_checkbox(cell, selected):
    """Altera apenas a marcação, sem tocar em formatação ou rótulos originais."""
    for p in cell.paragraphs[:1]:
        for run in p.runs:
            if re.search(r'\(\s*[Xx]?\s*\)', run.text):
                run.text = re.sub(r'\(\s*[Xx]?\s*\)', '( X )' if selected else '(   )', run.text, count=1)
                return
    raise ValueError('Opção de marcação não localizada no modelo')

def create_docx(payload: dict) -> bytes:
    d = Document(TEMPLATE)
    tables = d.tables
    activity = payload.get('activity', '')
    for i, name in enumerate(ACTIVITIES):
        replace_checkbox(tables[0].cell(i+1, 0), name == activity)
    replace_cell(tables[0].cell(1,1), payload.get('description', ''))
    passengers = payload.get('passengers', [])
    passengers = [x for x in passengers if isinstance(x,dict) and any(s(x.get(k)) for k in ('name','phone','bond'))]
    t = tables[1]
    # O modelo contém quatro linhas; podemos prolongá-lo sem reconstruir estilos.
    while len(t.rows)-1 < max(4,len(passengers)):
        t._tbl.append(deepcopy(t.rows[-1]._tr))
    while len(t.rows)-1 > max(4,len(passengers)):
        t._tbl.remove(t.rows[-1]._tr)
    for i in range(1,len(t.rows)):
        p=passengers[i-1] if i<=len(passengers) else {}
        replace_cell(t.cell(i,0), f'{i}. {s(p.get("name"))}' if s(p.get('name')) else '')
        replace_cell(t.cell(i,1), s(p.get('phone')))
        replace_cell(t.cell(i,2), s(p.get('bond')))
    for i, name in enumerate(VEHICLES):
        replace_checkbox(tables[2].cell(1,i), name == payload.get('vehicle'))
    for i,name in enumerate(DRIVER):
        replace_checkbox(tables[3].cell(i+1,0), name == payload.get('driver_trip'))
    keep = bool(payload.get('driver_stays'))
    replace_cell(tables[3].cell(4,0),
        '(   ) 4. O motorista precisa permanecer à disposição durante a viagem? '
        f'({" X " if keep else "   "}) SIM ou ({"   " if keep else " X "}) NÃO')
    t = tables[4]
    replace_cell(t.cell(1,0), 'PARTIDA: ' + (date_br(payload.get('departure_date')) or '—'))
    replace_cell(t.cell(1,1), (s(payload.get('departure_time')) + ' (MT)') if s(payload.get('departure_time')) else '—')
    replace_cell(t.cell(1,2), payload.get('departure_from') or '—')
    replace_cell(t.cell(1,3), payload.get('departure_to') or '—')
    if payload.get('has_return'):
        replace_cell(t.cell(2,0), 'RETORNO: ' + (date_br(payload.get('return_date')) or '—'))
        replace_cell(t.cell(2,1), (s(payload.get('return_time')) + ' (MT)') if s(payload.get('return_time')) else '—')
        replace_cell(t.cell(2,2), payload.get('return_from') or '—')
        replace_cell(t.cell(2,3), payload.get('return_to') or '—')
    else:
        for i,value in enumerate(['RETORNO: Não solicitado', '—', '—', '—']):
            replace_cell(t.cell(2,i), value)
    buf=io.BytesIO();d.save(buf);return buf.getvalue()

# Exemplo fictício, sem dados de passageiros reais.
EXAMPLE = {
 'activity':'eventos',
 'description':'Participação em atividade acadêmica do Programa de Pós-Graduação em Ciências Ambientais, para apresentação de resultados de pesquisa e intercâmbio científico.',
 'passengers':[{'name':'Passageiro Exemplo 1','phone':'(00) 00000-0000','bond':'Professor'}, {'name':'Passageiro Exemplo 2','phone':'(00) 00000-0000','bond':'Aluna'}],
 'vehicle':'carro', 'driver_trip':'partida','driver_stays':False,
 'departure_date':'2026-11-12','departure_time':'08:00','departure_from':'Campus Universitário, Cáceres/MT','departure_to':'Instituição de destino, Cuiabá/MT',
 'has_return':False,'return_date':'','return_time':'','return_from':'','return_to':''
}

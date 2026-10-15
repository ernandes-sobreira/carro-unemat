# Auditoria dos modelos e proteção de dados

- O DOCX e o PDF originais enviados pelo usuário foram utilizados como referência de layout.
- **Antes da publicação no GitHub público**, os dados preenchidos foram retirados: descrição da viagem, nomes, telefones, vínculos e itinerário.
- O desenho institucional permanece: cores, cabeçalhos, tabelas, opções de viagem, veículo, motorista e disposição dos campos.
- O preenchimento de dados reais ocorre **apenas no servidor autenticado**, não no repositório.
- Para até quatro passageiros e conteúdo curto, o PDF usa o modelo fixo de uma página. Conteúdo extenso recorre ao Word/LibreOffice, podendo ocupar mais páginas.
- Teste de integração disponível em `tests/smoke.py`.
- Antes do uso institucional, conferir visualmente uma exportação com dados de teste no Word da instituição.

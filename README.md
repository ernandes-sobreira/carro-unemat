# PPGCA — Solicitação de veículos

Sistema de preenchimento e gestão de solicitações de veículos do Programa de Pós-Graduação em Ciências Ambientais (PPGCA/UNEMAT), com duas contas: **Ernandes Sobreira Oliveira Junior** e **Maria Ribeiro** (nome de assinatura usado nas comunicações oficiais, não necessariamente o nome civil integral).

## O que funciona

- Login separado, com senhas individuais e armazenamento criptográfico (scrypt).
- Criação, edição, duplicação, arquivamento e busca de solicitações.
- Estados: rascunho, enviada, em análise, ajustes, aprovada, concluída e cancelada.
- Histórico de alterações, compartilhado entre as contas na mesma instalação.
- Campos equivalentes ao modelo original: atividade, objetivo, passageiros, veículo, motorista e itinerário.
- Cadastro compartilhado de passageiros, com seleção por nome e preenchimento automático de telefone/vínculo (como no fluxo simples do sistema de diárias PROFÁgua).
- **Word (.docx) gerado a partir de `assets/formulario_oficial.docx`, mantendo o formulário original sem os dados pessoais de exemplo.** Preserva tabelas, cores, margens, rótulos e elementos fixos.
- **PDF de uma página gerado sobre o PDF institucional limpo**, substituindo somente os campos editáveis para manter a diagramação exata. Se os dados ultrapassarem o espaço disponível, o sistema recorre à conversão do Word via LibreOffice e permite mais páginas. A prévia à direita utiliza exatamente este PDF.
- Botão para carregar um exemplo **fictício** (sem nomes ou telefones reais).

## Para executar em computador

Requisitos: Python 3.10+; LibreOffice (para PDF e prévia); conexão para instalar os requisitos uma vez.

**No Windows:** descompacte a pasta e clique duas vezes em `iniciar_windows.bat` (precisa de Python instalado). O assistente instala os pacotes, cria as senhas na primeira execução e abre o navegador.

**No macOS/Linux:** execute `./iniciar_linux_mac.sh`.

Ou execute manualmente:

```bash
cd ppgca_veiculos
python -m pip install -r requirements.txt
python iniciar.py
```

Abra **http://127.0.0.1:8000**. Na primeira execução, `setup.py` será chamado para que você defina as duas senhas. Não há senhas padrão ou acesso anônimo. Não compartilhe a pasta `data/` publicamente.

## Uso simultâneo por Ernandes e Maria

O sistema precisa estar **hospedado em um servidor único**, com Python, banco de dados persistente e HTTPS. O modo local em um computador não sincroniza automaticamente com outro computador pela internet. Quando hospedado, ambos usam a mesma URL, com logins separados. Existe um `Dockerfile` preparado para hospedagem com a fonte e o conversor de PDF instalados. Para manter dados após reiniciar o servidor, configure `PPGCA_DATABASE` apontando para armazenamento persistente (SQLite pode atender duas pessoas; em produção com múltiplos processos, planeje migração para Postgres).

Variáveis de ambiente recomendadas:

```
PPGCA_DATABASE=/seu-volume-persistente/ppgca.sqlite3
PPGCA_SESSION_SECRET=<segredo-aleatorio-com-mais-de-32-caracteres>
PPGCA_HTTPS=true
```

**Importante:** instalar em uma hospedagem de arquivos estáticos, como GitHub Pages, não é suficiente. O sistema utiliza backend FastAPI, geração oficial no servidor e banco de dados. Evite plataformas com armazenamento efêmero sem volume/backup. Faça backups periódicos: `python backup.py` grava cópias consistentes em `data/backups/`, que devem ser copiadas para local seguro.

## Fidelidade ao Word

A fonte de verdade é a **estrutura do documento enviado**, sem os dados pessoais da viagem de exemplo, porque este repositório é público. A exportação altera somente o texto dos campos preenchidos e as marcações das caixas, utilizando o mesmo arquivo DOCX como ponto de partida. O PDF compacto tem como base a versão **anonimizada** do arquivo PDF de uma página enviado pelo usuário. O programa troca os conteúdos variáveis e preserva o desenho original. Caso os dados não caibam, o PDF é gerado pelo LibreOffice, que pode apresentar pequenas diferenças de paginação em relação ao Word instalado no computador de origem. A quantidade de linhas varia com texto e número de passageiros; muitos dados podem aumentar o documento para mais de uma página. **Não alterar** o arquivo oficial original se a instituição não publicar um modelo novo.

## Segurança / operação

- O aplicativo exige login e senha; cookies de sessão assinados, `SameSite=strict`; requisições de alteração exigem token CSRF.
- Para mudar uma senha, use "Alterar senha" após login. Se perder acesso, o administrador do servidor pode rodar `python setup.py --user maria` ou `--user ernandes` e redefinir **somente** a conta escolhida.
- O botão "Arquivar" faz exclusão lógica e mantém registro no banco; não há autoexclusão de backups.
- Verifique a exigência institucional sobre autorização de viagens. O estado **"Aprovada" nesta ferramenta é administrativo interno, não substitui aprovação formal da UNEMAT**.
- Não armazena CPF nem dados sensíveis extras; armazena nomes/telefones fornecidos. Configure HTTPS e controle de acesso ao servidor. Revise LGPD/políticas antes de publicar na internet.

## Estrutura

- `app.py` — rotas web, autenticação e conversão PDF.
- `db.py` — banco, usuários, senhas.
- `setup.py` — criação das duas contas.
- `documents.py` — preenchimento do modelo DOCX.
- `assets/formulario_oficial.docx` e `assets/formulario_oficial.pdf` — modelos institucionais com a diagramação preservada e dados pessoais de exemplo removidos.
- `pdf_template.py` — edição dos campos sobre a página PDF original.
- `templates/`, `static/` — interface responsiva.

## Via Docker (mesma instalação para ambos, em servidor)

```bash
docker compose build
docker compose run --rm ppgca-veiculos python setup.py
docker compose up -d
```

O `compose.yaml` publica apenas na máquina local por segurança. Para acesso pela internet, use um proxy HTTPS e configure domínio, autenticação, disco persistente e backups.

## Repositório público e privacidade

Os modelos de `assets/` foram preparados a partir dos arquivos institucionais com nomes, telefones, roteiro e descrição da solicitação real **removidos antes da publicação**. Não coloque solicitações preenchidas, dados de passageiros, SQLite, backups, `.env` ou segredos de sessão no GitHub. O exemplo em "Carregar exemplo" é fictício. Guarde os originais com dados preenchidos em armazenamento interno com acesso controlado.

O GitHub mantém o **código**; ainda é necessário implantar o backend com HTTPS e um volume persistente em servidor para Ernandes e Maria usarem o mesmo endereço.

## Demonstração publicada em 15/10/2026

- URL: https://carro-unemat-ppgca.onrender.com/login
- Serviço: Render gratuito, Docker e publicação automática pela branch main.
- **Não utilizar com passageiros e solicitações reais**: a persistência ainda é SQLite em armazenamento efêmero, com risco de perda em reinícios e implantações. Há aviso visível no aplicativo.
- Contas de teste ernandes e maria; senhas armazenadas como hashes scrypt nas variáveis protegidas da hospedagem, não no GitHub.
- Alterações de senha realizadas nesta versão podem ser perdidas quando o armazenamento for recriado.
- O Postgres gratuito carro-unemat-ppgca-db foi provisionado, porém ainda não está conectado à aplicação; expira em 14/11/2026.
- É necessário migrar o banco para PostgreSQL e configurar a conexão antes de uso oficial.

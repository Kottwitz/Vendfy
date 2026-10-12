# Vendfy Backend

Estrutura inicial da API Vendfy, desenvolvida com Python 3.12+, FastAPI,
Pydantic Settings, SQLAlchemy 2 assíncrono, PostgreSQL e Alembic.

O backend oferece health check, autenticação por email/senha com Argon2/JWT e
CRUD autenticado de clientes e orçamentos com isolamento por empresa.

## Executar com Docker Compose

Requisitos: Docker com Docker Compose.

Na pasta `backend`, copie `.env.example` para `.env` e ajuste os valores locais:

```powershell
Copy-Item .env.example .env
docker compose up --build
```

A API estará disponível em `http://localhost:8000`. Para parar os serviços,
execute `docker compose down`. Os dados do PostgreSQL permanecem no volume
`postgres_data`.

## Deploy de demonstração na Vercel

A Vercel suporta FastAPI usando Python Functions. Este monorepo usa dois projetos
Vercel ligados ao mesmo repositório GitHub: um com Root Directory `backend`
(API) e outro com Root Directory `frontend` (Next.js). Importe o mesmo
repositório para cada projeto. A Vercel detecta FastAPI por
`backend/requirements.txt` e `backend/app/main.py`.

No projeto da API, configure estas variáveis em **Settings → Environment
Variables**, em Production e Preview:

- `DATABASE_URL`: URL do Neon com pooler habilitado para o runtime serverless,
  usando formato `postgresql+asyncpg://...` e `ssl=require`. Copie a URL com
  pooling habilitado na opção Connect do Neon; não publique nem comite a URL.
- `SECURITY__JWT_SECRET_KEY`: segredo aleatório longo, exclusivo para o
  ambiente.
- `SECURITY__CREDENTIAL_ENCRYPTION_KEY`: chave Fernet exclusiva. Faça backup
  seguro: credenciais comerciais criptografadas no banco só podem ser lidas
  usando essa mesma chave.

As migrations do branch `production` do Neon já foram aplicadas até a revisão
`20261012_06`. Não rode `alembic upgrade head` durante o build/deploy. Para
executar migrations futuras, use uma conexão direta (sem pooler) do Neon e rode
localmente, a partir desta pasta, com `DATABASE_URL` configurada apenas no `.env`
local:

```powershell
python -m alembic upgrade head
```

Depois do primeiro deploy, teste `https://SUA_API.vercel.app/health`. Guarde
essa URL base: ela será o valor de `BACKEND_API_URL` no projeto frontend.

A Vercel Hobby destina-se a uso pessoal e não comercial; use este deploy apenas
como demonstração com dados fictícios. Verifique os limites atuais de Python
Functions e do plano antes de usar o serviço. Teste a geração de PDF e os
provedores de email/WhatsApp após publicar, pois dependem dos limites e do acesso
de rede disponíveis às Functions.

## Executar localmente

Requisitos: Python 3.12+ e uma instância PostgreSQL acessível.

Na pasta `backend`, crie e ative um ambiente virtual, instale as dependências e
configure o `.env`:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Atualize `DATABASE_URL` no `.env` para apontar para seu PostgreSQL, defina
`SECURITY__JWT_SECRET_KEY` com um segredo aleatório de pelo menos 32 caracteres e
inicie a API:

```powershell
uvicorn app.main:app --reload
```

## Verificar saúde

Com a API em execução:

```powershell
Invoke-RestMethod http://localhost:8000/health
```

Resposta esperada:

```json
{"status":"ok"}
```

Documentação interativa disponível em `http://localhost:8000/docs`.

## Autenticação

O cadastro cria uma empresa e seu primeiro usuário (`role=owner`) em uma única
transação. `name` e `company_name` são opcionais; quando omitidos, ambos são
derivados da parte do email anterior a `@`.

```powershell
Invoke-RestMethod -Method Post -Uri http://localhost:8000/register `
  -ContentType "application/json" `
  -Body '{"email":"dono@example.com","password":"senha-segura"}'
```

O login OAuth2 usa `application/x-www-form-urlencoded`, com o email no campo
`username`:

```powershell
Invoke-RestMethod -Method Post -Uri http://localhost:8000/token `
  -ContentType "application/x-www-form-urlencoded" `
  -Body "username=dono%40example.com&password=senha-segura"
```

Envie o token retornado como `Authorization: Bearer <token>` para `GET /users/me`.
O email é globalmente único; a migration abaixo substitui a restrição anterior,
que permitia o mesmo email em empresas distintas.

## Clientes

Todas as rotas de clientes exigem `Authorization: Bearer <token>` e limitam
automaticamente a consulta à empresa do usuário autenticado:

- `GET /clients?offset=0&limit=100`: lista clientes da empresa (máximo 100 por página).
- `POST /clients`: cria cliente; `name` é obrigatório, os demais campos são opcionais.
- `GET /clients/{client_id}`: consulta um cliente da empresa.
- `PATCH /clients/{client_id}`: atualiza parcialmente os campos enviados.
- `DELETE /clients/{client_id}`: remove cliente sem orçamentos associados.

Um documento duplicado na mesma empresa retorna `409`; o mesmo cliente não é
visível a outras empresas e aparece como `404`. Clientes referenciados por
orçamentos não podem ser removidos (`409`).

## Orçamentos e itens

Todas as rotas exigem `Authorization: Bearer <token>` e operam somente na
empresa do usuário autenticado:

- `GET /quotes?offset=0&limit=100&status=DRAFT&client_id=<uuid>`: lista e filtra orçamentos.
- `POST /quotes`: cria orçamento para cliente da empresa autenticada; inclui
  `client_id`, `items` (opcional), `discount` (opcional), `description` e `valid_until`.
- `GET /quotes/{quote_id}` e `PATCH /quotes/{quote_id}`: consulta e atualiza
  rascunho. Se `items` for enviado na atualização, substitui a lista completa.
- `DELETE /quotes/{quote_id}`: exclui somente rascunhos.
- `POST /quotes/{quote_id}/status`: solicita transição de status válida.
- `POST /quotes/{quote_id}/cancel`: cancela rascunhos, enviados ou visualizados.
- `POST /quotes/{quote_id}/items`, `PATCH /quotes/{quote_id}/items/{item_id}` e
  `DELETE /quotes/{quote_id}/items/{item_id}`: altera itens de rascunhos.

O número é sequencial por empresa e alocado serializando criações pelo registro
da empresa. Quantidades devem ser positivas (até 3 casas decimais), preços e
descontos não negativos (até 2 casas). O backend calcula cada total de item,
subtotal e total final, arredondando valores monetários para centavos; desconto
maior que subtotal retorna `422`. Cliente inexistente ou de outra empresa retorna
`422`; orçamento fora da empresa autenticada retorna `404`.

As transições permitidas são `DRAFT → SENT/CANCELLED`,
`SENT → VIEWED/APPROVED/REJECTED/CANCELLED` e
`VIEWED → APPROVED/REJECTED/CANCELLED`. Os demais estados são terminais.
Somente rascunhos podem ser editados ou excluídos; após envio, itens e dados
financeiros ficam congelados.

## Banco de dados e migrations

A sessão assíncrona está disponível pela dependência `get_db_session`, e o
metadata das entidades é centralizado em `app.db.base.Base`. A migration inicial
cria `companies`, `users`, `clients`, `quotes` e `quote_items`; migrations
posteriores tornam o email do usuário globalmente único e adicionam o status
`CANCELLED` aos orçamentos. As rotas de clientes e orçamentos usam tabelas já
criadas. Se já houver emails repetidos
entre empresas, resolva essas duplicidades antes de aplicar a migration. Com PostgreSQL
disponível e `DATABASE_URL` configurada no `.env`, aplique-a com:

```powershell
alembic upgrade head
```

Para gerar uma migration futura após alterar modelos:

```powershell
alembic revision --autogenerate -m "descricao"
```

Para conferir a revisão aplicada:

```powershell
alembic current
```

Com Docker Compose, confirme que o PostgreSQL está pronto com:

```powershell
docker compose exec db pg_isready -U vendfy -d vendfy
```

## Testes

```powershell
python -m pytest
```

## Organização

- `app/core`: configurações da aplicação e parâmetros básicos de segurança.
- `app/db`: base declarativa SQLAlchemy, engine e sessões assíncronas.
- `app/models` e `app/schemas`: entidades do banco e contratos da API.
- `app/api`: composição do router e rotas HTTP.
- `app/services`: lógica de autenticação, clientes e orçamentos;
  `app/repositories` permanece como ponto de extensão para acesso a dados.
- `tests`: testes automatizados.
- `alembic`: configuração e ambiente das migrations.

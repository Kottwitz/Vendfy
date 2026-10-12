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

## Deploy de demonstração no Google Cloud Run

O container respeita a variável `PORT` fornecida pelo Cloud Run. Para uma demo
com dados fictícios, o backend pode usar Cloud Run e conectar a um PostgreSQL
gerenciado, como o plano gratuito do Neon. Não use o PostgreSQL local/Compose
como banco de produção: ele não estará acessível ao serviço na nuvem.

O Cloud Run tem cota mensal gratuita, mas exige uma conta de faturamento e cobra
o uso que ultrapassar a cota. Defina limites de instâncias, acompanhe o consumo
e não considere essa opção custo zero garantido. Use a região `us-central1` para
os limites gratuitos publicados com base nessa região.

Com o Google Cloud CLI instalado e autenticado, na pasta `backend`:

```powershell
gcloud auth login
gcloud config set project SEU_PROJECT_ID
gcloud run deploy vendfy-api --source . --region us-central1 --allow-unauthenticated --port 8080 --memory 512Mi --cpu 1 --min 0 --max 1
```

Configure as variáveis e credenciais do serviço no Google Cloud Console, sem
gravá-las no repositório:

- `DATABASE_URL`: URL async do PostgreSQL remoto (`postgresql+asyncpg://...`).
- `SECURITY__JWT_SECRET_KEY`: segredo aleatório longo e exclusivo para esse
  ambiente.
- `SECURITY__CREDENTIAL_ENCRYPTION_KEY`: chave Fernet exclusiva; faça backup
  seguro, pois os segredos comerciais salvos não podem ser lidos sem ela.

Após criar o PostgreSQL remoto e configurar `DATABASE_URL`, aplique as migrations
uma vez a esse banco usando o mesmo ambiente Python:

```powershell
python -m alembic upgrade head
```

Confirme a API em `https://SUA_API.run.app/health`. Em seguida, configure
`BACKEND_API_URL` no deploy do frontend com essa URL base e faça novo deploy.

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

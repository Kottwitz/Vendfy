# Vendfy

Plataforma web para pequenas empresas criarem e gerenciarem clientes e
orçamentos.

## Estrutura

- `backend/`: API FastAPI, PostgreSQL, SQLAlchemy 2 e migrations Alembic.
- `frontend/`: aplicação Next.js e TypeScript.

## Desenvolvimento local

Consulte [backend/README.md](backend/README.md) para instalar as dependências,
configurar o PostgreSQL e iniciar a API. No frontend, instale as dependências e
defina `BACKEND_API_URL` no arquivo `frontend/.env.local`:

```powershell
cd frontend
npm ci
npm run dev
```

O frontend usa o backend local em `http://127.0.0.1:8000` por padrão.

## Deploy de demonstração

Implante o backend FastAPI e o frontend Next.js como dois projetos Vercel a
partir do mesmo repositório. Consulte [backend/README.md](backend/README.md) e
[frontend/README.md](frontend/README.md) para os passos e variáveis necessárias.
Use dados fictícios: a Vercel Hobby é restrita a uso pessoal e não comercial.

Não envie arquivos `.env`, credenciais ou dados reais para o GitHub.

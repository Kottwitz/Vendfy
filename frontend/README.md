# Vendfy Frontend

Frontend do Vendfy com Next.js App Router, TypeScript, Tailwind CSS e ícones
Lucide. A interface está em português e usa uma camada BFF do Next.js para
encaminhar chamadas à API FastAPI e manter o JWT em cookie `HttpOnly`.

## Executar localmente

Requisitos: Node.js 20.9+ e a API Vendfy em execução na porta 8000.

```powershell
Copy-Item .env.example .env.local
npm install
npm run dev
```

Abra `http://localhost:3000`. Para usar outra URL da API, defina
`BACKEND_API_URL` em `.env.local`. Essa variável é apenas do servidor e não deve
usar o prefixo `NEXT_PUBLIC_`.

## Deploy de demonstração

Para uma demo com dados fictícios, o frontend pode ser implantado na Vercel
(Hobby) e a API no Google Cloud Run, com PostgreSQL remoto. Defina
`BACKEND_API_URL` nas variáveis de ambiente do projeto Vercel com a URL HTTPS do
serviço Cloud Run. Não use o endereço local `127.0.0.1` em produção. A Vercel
Hobby é restrita a uso pessoal/não comercial; não a use para atender clientes
ou operar o Vendfy comercialmente.

## Telas

- `/login`: login e cadastro da empresa/usuário inicial.
- `/`: dashboard com resumo de clientes e orçamentos.
- `/clients`: pesquisa, cadastro, edição e exclusão de clientes.
- `/quotes`: criação de orçamento com itens, ações de status e resumo/editabilidade
  dos itens enquanto o orçamento estiver em rascunho. Os detalhes permitem baixar
  ou visualizar um PDF gerado pela API com os valores persistidos do orçamento,
  além de enviá-lo por email (SMTP) ou WhatsApp Business Cloud API.
- `/settings`: perfil, informações de segurança e encerramento de sessão.

As páginas privadas chamam a API através de `/api/backend/*`; os Route Handlers
anexam o bearer token armazenado em cookie no servidor. O caminho de proxy é
limitado às rotas `users/me`, `companies/me`, `clients` e `quotes`. Não coloque tokens no
`localStorage` nem segredos em variáveis `NEXT_PUBLIC_*`.

## Configurar envio de orçamentos

Antes de cadastrar credenciais de integração, configure no ambiente do backend
`SECURITY__CREDENTIAL_ENCRYPTION_KEY` com uma chave Fernet nova e exclusiva para
o ambiente. Gere-a com:

```powershell
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Guarde a chave fora do banco e mantenha backup: sem ela, tokens e senhas SMTP
armazenados não poderão ser descriptografados. Execute também
`python -m alembic upgrade head` no backend para criar as colunas de integração.

Em `/settings`, informe o email remetente e SMTP autorizado pelo provedor e/ou o
telefone de envio e credenciais do WhatsApp Business Cloud API. Segredos já
salvos não são retornados à interface. Mensagens livres pela Cloud API dependem
da janela de atendimento de 24 horas do WhatsApp; fora dela, a Meta exige um
template aprovado.

## Verificações

```powershell
npm run lint
npm run build
```

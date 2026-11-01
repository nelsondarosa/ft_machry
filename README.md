# Machry

Sistema de operação para restaurante, com API Flask, frontend React com Vite e TypeScript e persistência SQLAlchemy. O ambiente padrão usa SQLite em volume local. A mesma camada de persistência aceita PostgreSQL quando a infraestrutura for migrada.

## Funcionalidades atuais

- Catálogo de insumos, produtos intermediários e produtos finais.
- Fichas técnicas com rendimento, fases ordenadas e componentes.
- Validações de domínio recuperadas do projeto anterior.
- Lotes, localizações, movimentações e sugestão de saída por FEFO.
- Estoque geral de insumos, produtos intermediários e produtos finais, com entradas, saídas e ajustes pela interface.
- Consulta das solicitações de produção.
- Interface responsiva para produtos e fichas técnicas.
- Login por sessão com perfis de proprietária, gestor e cozinha.
- Swagger em `/docs`.

## Executar na VM com Docker e SQLite

Crie o arquivo de ambiente e inicialize o banco uma única vez:

```bash
cp .env.example .env
docker compose build
docker compose run --rm api flask --app app init-db --seed
docker compose up -d
```

Acessos padrão:

- Interface: `http://IP_DA_VM:8080`
- API: `http://IP_DA_VM:5000`
- Swagger: `http://IP_DA_VM:5000/docs`
- Saúde da API: `http://IP_DA_VM:5000/health`

O SQLite é salvo em `./data/app.db` na VM. Faça backup dessa pasta antes de atualizar ou mover o serviço.

Para acompanhar os containers:

```bash
docker compose ps
docker compose logs -f api frontend
```

## Desenvolvimento local

### API Flask

Requer Python 3.12+.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements-dev.txt
flask --app app init-db --seed
flask --app app run
```

### Frontend React, Vite e TypeScript

Requer Node.js 22+ e pnpm.

```bash
cd frontend
pnpm install
pnpm dev
```

O servidor Vite abre em `http://localhost:5173` e encaminha `/api` para o Flask em `http://localhost:5000`.

### Acessos iniciais de desenvolvimento

Ao executar `flask --app app init-db`, o sistema cria ou atualiza as contas iniciais:

| Perfil | Usuário | Senha inicial |
|---|---|---|
| Proprietária | `dona` | `Dona@123` |
| Gestor | `gestor` | `Gestor@123` |
| Cozinha | `cozinha` | `Cozinha@123` |

Altere as credenciais e `SECRET_KEY` no arquivo `.env` antes de publicar. As senhas são armazenadas no banco somente como hash.

Para validar a compilação:

```bash
pnpm exec tsc --noEmit
pnpm build
```

## PostgreSQL

O container PostgreSQL já está preparado como um profile opcional. Ajuste o `.env`:

```dotenv
DB_CONNECTION=postgresql
DB_HOST=postgres
DB_PORT=5432
DB_DATABASE=ft_machry
DB_USERNAME=machry
DB_PASSWORD=uma-senha-forte
```

Depois inicialize com:

```bash
docker compose --profile postgres up -d postgres
docker compose --profile postgres run --rm api flask --app app init-db --seed
docker compose --profile postgres up -d
```

Também é possível fornecer uma `DATABASE_URL` completa. Essa variável tem prioridade sobre os campos separados.

## CI/CD no GitHub

O workflow `.github/workflows/ci-cd.yml` executa automaticamente:

1. Testes da API em Python 3.12.
2. Verificação TypeScript e build Vite.
3. Build das imagens Docker.
4. Deploy por SSH quando um commit chega à `main`.

Cadastre estes secrets no environment `production` do GitHub:

- `VM_HOST`: endereço da VM.
- `VM_USER`: usuário SSH.
- `VM_SSH_KEY`: chave privada usada pelo GitHub Actions.
- `VM_SSH_PORT`: porta SSH; use `22` quando não houver alteração.
- `VM_APP_PATH`: caminho absoluto do clone na VM.

A VM precisa ter Git, Docker e o plugin Docker Compose. O repositório deve estar previamente clonado no caminho indicado, na branch `main`, e o usuário do deploy precisa ter permissão para executar Docker.

O deploy usa `git pull --ff-only`, reconstrói os containers, inicializa um banco novo quando necessário e aplica `docker compose up -d`.

## API de fichas técnicas

Rotas principais:

- `GET/POST /api/fichas-tecnicas`
- `GET/PUT/DELETE /api/fichas-tecnicas/{id}`
- `GET /api/fichas-tecnicas/fases`

Regras aplicadas:

- Insumos não podem possuir ficha técnica.
- Um produto possui no máximo uma ficha.
- O produto resultante não pode ser componente de si mesmo.
- Componentes e fases precisam existir e estar ativos quando aplicável.
- Ordem de fase e componente não podem se repetir.
- Componentes só podem apontar para fases da própria ficha.
- A atualização de cabeçalho, fases e componentes ocorre na mesma transação.
- Fichas com histórico de produção não podem ser excluídas.

## Testes

```bash
pytest -q
```

Cada teste cria um SQLite temporário. O arquivo `data/app.db` não é alterado.

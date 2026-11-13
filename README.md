# Machry

Sistema de operação para restaurante, com API Flask, frontend React com Vite e TypeScript e persistência SQLAlchemy. O ambiente padrão usa SQLite em volume local. A mesma camada de persistência aceita PostgreSQL quando a infraestrutura for migrada.

## Funcionalidades atuais

- Catálogo de insumos, produtos intermediários e produtos finais, com importação em lote via CSV.
- Fichas técnicas com rendimento, fases ordenadas e componentes, com importação em lote via CSV.
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

### Limpar produtos e fichas para testar

Para recomeçar a importação dos CSVs de exemplo com o Docker rodando:

```bash
docker compose exec api flask --app app limpar-catalogo
```

O comando pede confirmação antes de apagar. Use `--sim` para pular a confirmação.

- **Apaga:** produtos, fichas técnicas e tudo que depende deles (lotes, movimentações de estoque e solicitações de produção).
- **Mantém:** usuários, fases de produção, grupos e localizações.
- **Bancos:** funciona com SQLite e PostgreSQL. Fora do Docker, rode `flask --app app limpar-catalogo` com o venv ativo.
- **Primeira vez:** se o container foi criado antes deste comando existir, reconstrua a API com `docker compose up -d --build api`.

## Importação de produtos via CSV

Na página **Produtos**, o botão **Importar CSV** cadastra vários produtos de uma vez. A tela mostra uma prévia com os erros de cada linha antes de enviar, e a importação é tudo ou nada (limite de 500 produtos por arquivo). Produtos com o mesmo nome de um produto já cadastrado, ou de uma linha anterior do arquivo, são ignorados, mesmo com outra conservação. Assim, reimportar um arquivo não duplica o catálogo, e cada nome continua único para as fichas técnicas. O mesmo recurso está disponível na API em `POST /api/produtos/lote`.

Colunas (separador `;` ou `,`, UTF-8):

| Coluna | Obrigatória | Valores |
|---|---|---|
| `nome` | sim | até 150 caracteres |
| `tipo` | sim | `INSUMO`, `INTERMEDIARIO` ou `FINAL` |
| `unidade_medida` | sim | ex.: `kg`, `g`, `L`, `ml`, `un`, `pct`, `cx` |
| `subdivisao` | não | categoria ou variação, usada no filtro da tela |
| `conservacao` | não | `SECO` (padrão), `RESFRIADO` ou `CONGELADO` |
| `validade_obrigatoria` | não | `1`/`sim` ou `0`/`não` (padrão) |
| `validade_padrao_dias` | não | número inteiro de dias |

Exemplo completo: [`docs/exemplos/produtos_machry.csv`](docs/exemplos/produtos_machry.csv), com os insumos do estoque do Machry (366 linhas; Bacalhau e Linguiça calabresa aparecem resfriados e congelados, e só a primeira linha de cada é importada) gerados a partir das planilhas de validade. Unidades e prazos de validade desse arquivo são estimativas por categoria; revise antes de usar em produção.

## Importação de fichas técnicas via CSV

Na página **Fichas técnicas**, o botão **Importar CSV** cadastra várias receitas de uma vez (limite de 200 fichas, tudo ou nada). API: `POST /api/fichas-tecnicas/lote`.

O arquivo tem **uma linha por componente**; as linhas com o mesmo valor em `ficha` formam uma receita.

| Coluna | Uso |
|---|---|
| `ficha` | nome do produto preparado; precisa existir no catálogo como `INTERMEDIARIO` ou `FINAL` |
| `rendimento` | na unidade do produto da ficha; basta informar na primeira linha |
| `observacao` | opcional; as observações das linhas são unidas em ordem (útil para o modo de preparo) |
| `fase_ordem`, `fase`, `tempo_min` | fase da linha; nome e tempo só precisam aparecer na primeira linha daquela ordem. Fases fora do catálogo são criadas |
| `componente` | nome do produto usado; vazio para uma fase sem insumos |
| `quantidade` | número (vírgula ou ponto); `q.b.` ou vazio vira "A gosto (q.b.)" na observação |
| `unidade` | opcional; `mg`/`g`/`kg` e `ml`/`L` são convertidos para a unidade do produto |

Produtos e fases são buscados pelo nome, sem diferenciar maiúsculas, acentos e espaços. Um nome que corresponda a mais de um produto (ex.: dois produtos de mesmo nome cadastrados à mão) gera erro. Produtos que já têm ficha técnica são ignorados (e listados no aviso final), então arquivos com receitas em comum podem ser importados em sequência; a mesma ficha repetida dentro de um arquivo gera erro.

Cada ficha de exemplo termina com linhas só de `observacao`: o código e a origem da receita, o modo de preparo e “Ajustes da importação: …”, que registra as diferenças em relação à ficha original (unidades convertidas, como 2 dentes de alho ≈ 10 g, e valores estimados, como rendimentos e tempos das fases). Uma linha com apenas `ficha` e `observacao` é válida para esse fim.

Exemplos, em ordem de importação (os de produtos pela página **Produtos**, os de fichas pela página **Fichas técnicas**):

1. [`produtos_machry.csv`](docs/exemplos/produtos_machry.csv): catálogo de insumos.
2. [`produtos_apostila_1.csv`](docs/exemplos/produtos_apostila_1.csv) e [`produtos_apostila_2.csv`](docs/exemplos/produtos_apostila_2.csv), depois [`fichas_apostila_1.csv`](docs/exemplos/fichas_apostila_1.csv), [`_2`](docs/exemplos/fichas_apostila_2.csv) e [`_3`](docs/exemplos/fichas_apostila_3.csv): todas as 405 receitas da Apostila Cozinheiro 2024, divididas em partes por causa do limite de 500 produtos e 200 fichas por importação. Os produtos trazem o hortifrúti, os insumos que faltam no catálogo e um produto intermediário ou final para cada receita.
3. [`produtos_aula4.csv`](docs/exemplos/produtos_aula4.csv) e [`fichas_aula4.csv`](docs/exemplos/fichas_aula4.csv): Aula 4 (batatas). Só acrescenta a batata parmentier; as demais fichas já vêm da apostila e são ignoradas.

Sobre as fichas da apostila:

- **FT 01 a FT 10** foram revisadas à mão. As demais foram convertidas automaticamente e merecem revisão antes do uso em produção.
- **Nomes:** os insumos usam os nomes do catálogo (ex.: “Manteiga” → Manteiga sem sal, “Sal” → Sal fino, “Batatas” → Batata asterix). Quando a receita tem o mesmo nome de um produto comprado, ganha “caseiro(a)” ou “cozido” (ex.: Ketchup caseiro, Arroz integral cozido).
- **Fases:** saem do modo de preparo, pelo verbo de cada passo. Rendimento e tempos não informados na apostila são estimados.
- **Unidades:** são convertidas (dentes, maços, colheres, fatias). Unidades erradas ou ausentes na apostila são corrigidas, como “110 un” de cebola lido como 110 g. Nata e creme de leite pesados em g são lançados em ml, porque estão cadastrados em L.
- **Fora dos componentes:** água, gelo e utensílios não são controlados no estoque.
- **Receitas repetidas:** são importadas uma vez. Ficam de fora a segunda e a terceira versão do molho bechamel e as versões repetidas de arroz, fundo bovino, molho demi-glace, polenta cremosa e salsa verde.
- **Observação de cada ficha:** “Ajustes da importação” registra cada conversão e estimativa.

## Identidade visual

A identidade (nome, logo, ícones e CSS) vem de uma pasta em `branding/`, escolhida pela variável `BRANDING`. O padrão é `machry`: nome e logo do site oficial (machry.com.br). Para trocar, defina no `.env` outra pasta (ou um caminho absoluto, fora do Docker):

```
BRANDING=cozinha_plus
```

Com `BRANDING=` vazio, nenhuma pasta é lida e o frontend usa os textos da pasta `machry` embutidos no código (sem logo, ícones nem CSS).

A pasta deve conter um `brand.json`; todos os campos são opcionais e os ausentes mantêm o padrão:

```json
{
  "nome": "Bistrô Aurora",
  "subtitulo": "OPERAÇÃO DE COZINHA",
  "sigla": "BA",
  "titulo": "Bistrô Aurora · Operação de cozinha",
  "logo": "logo.svg",
  "favicon": "favicon.png",
  "apple_touch_icon": "apple-touch-icon.png",
  "css": "custom.css"
}
```

- `sigla` aparece no lugar do logo quando `logo` não é informado.
- `css` é carregado depois do CSS padrão; sobrescreva as variáveis `--green`, `--lime`, `--cream`, `--line`, `--muted` ou qualquer classe.
- Arquivos são lidos da própria pasta. No Docker, `./branding` é montado na API: alterações em arquivos exigem apenas recarregar a página; alterar `BRANDING` exige `docker compose up -d api`.
- Veja `branding/machry/`, `branding/cozinha_plus/` e `branding/exemplo/`.

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

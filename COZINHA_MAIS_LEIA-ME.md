# Cozinha Mais — pacote completo de desenvolvimento

Esta pasta contém o projeto inteiro da branch `yuri` fornecida pelo usuário, com as alterações de frontend adicionadas. **Nenhum commit, push ou PR foi criado.**

## Executar localmente

Windows: execute `run.bat` (ou `run.bat --seed` apenas para dados demonstrativos em um banco novo). Requisitos: Python 3.12+, Node.js 22+ e npm. Aguarde as instalações e abra **http://localhost:8080**. O script abre uma janela para a API Flask (5000) e mantém o Vite na janela principal (8080). Para acesso na rede local, use `http://IP_DO_PC:8080` e libere a porta 8080 no firewall, se necessário. A API Flask fica em loopback; o proxy do Vite encaminha `/api`.

Linux/macOS: `./run.sh`. Não execute scripts de desenvolvimento diretamente na OCI de produção.

Docker/OCI: `docker-compose.yml`, `frontend/nginx.conf` e os Dockerfiles originais foram preservados. A conexão DBeaver ao PostgreSQL via `127.0.0.1:5432` só funciona no próprio host ou por túnel SSH. PostgreSQL exige o profile `postgres` e configuração do banco; a publicação da porta não significa que o serviço está rodando.

## Melhorias de frontend

- Nome Cozinha Mais em login, barra lateral, carregamento e título; monograma textual C+ provisório.
- Tela de usuários para OWNER (criar, editar, redefinir senha pelo proprietário, ativar/desativar; sem exclusão).
- Localizações: criar, editar e excluir, respeitando restrições do backend.
- Movimentações: consulta dos últimos 500 registros, com filtros de lote, produto, tipo, usuário e datas.
- Estoque: transferência entre lotes do mesmo produto, transformação entre produtos com rendimento e edição de datas/custo de lote.
- Ajustes de estoque já disponíveis no formulário de movimentação, com motivo obrigatório quando exigido pela API.
- Impressão simplificada da fila de produção.
- Correção no formulário de nova entrada: após criar lote, uma falha no movimento não cria outro lote em uma nova tentativa.
- Vite proxy para API, execução local integrada por `run.bat` e `run.sh`.

## Pendências que dependem de backend/DevOps

Planejamento com quantidade, prioridade e horários persistidos; baixa automática FEFO na conclusão de produção; geração de produto acabado; senha própria/primeiro login; rate limit/auditoria; alerta de estoque mínimo; migrações; backup; testes de implantação; TLS e segredos de produção. **Não são anunciados como implementados.** Transformação pela API exige lote de destino preexistente. O histórico está limitado aos 500 registros mais recentes retornados pela API.

## Importante para a equipe

O nome do repositório e variáveis históricas de banco (`ft_machry`, `machry`) foram preservados para não quebrar infraestrutura. O nome exibido ao usuário é Cozinha Mais. O script local força SQLite e não altera o banco PostgreSQL do Docker.

# CLAUDE.md — Industrial Data Platform

## Quem sou e como trabalhar comigo
- Lucas (GitHub: lucasnunesf), migrando de BI para Engenharia de Dados com foco em cloud. Objetivo: vaga de dados em Lisboa. Já estou em entrevistas.
- Responda em português, de forma direta e concisa. Código e docs do repo em inglês.
- Modo de trabalho até o MVP: você constrói, eu rodo e reviso. Explique em português o que cada comando faz.
- PARE antes de cada commit e me mostre o diff. Commits e PRs devem sair no meu nome.
- SQL com poucos comentários.
- Ao fim de cada marco: "banca" de 10 min com perguntas de entrevista; registrar as decisões em docs/decisions.md.
- Nunca invente justificativas: se eu não souber explicar algo, me ensine o porquê da decisão.

## Projeto
- Caso real AC Metais (corte a laser, serralheria, caldeiraria), com permissão do dono. Todos os dados são SINTÉTICOS.
- Fluxo: Pedido → Corte a laser → Serralheria/Caldeiraria → Acabamento → Expedição.
- Perguntas de negócio: gargalo, lead time por etapa, pedidos atrasados, sucata do laser, margem por pedido, entrega no prazo.

## Arquitetura do MVP (decidida)
Simulador Python (Faker + psycopg) → PostgreSQL 17 (Docker, ERP/OLTP) → extração incremental em Python (updated_at; eventos por event_id) gravando Parquet → ADLS Gen2 (bronze) → Azure Databricks / PySpark (silver, Delta) → dbt-databricks (gold, estrela, com testes) → Databricks SQL Warehouse → Power BI.
- Orquestração no MVP: script run_pipeline.ps1. Airflow só depois do MVP.
- Infra Azure via Terraform: Resource Group, ADLS (bronze/silver/gold), Azure Databricks, Access Connector, Key Vault.
- Custo: cluster single-node com auto-terminate de 15 min; SQL Warehouse no menor tamanho com auto-stop. Verificar cota de vCPU da conta trial.
- Depois do MVP: streaming do laser (Event Hubs), Airflow, CI/CD (GitHub Actions), financeiro (PTAX), logística.
- NÃO usar: Snowflake, Fabric, Synapse, Databricks Workflows.

## Marcos até o MVP (prazo: 16/11/2026)
| Marco | Entrega | Até |
|---|---|---|
| M1 ✅ | ERP (14 tabelas + trigger + seed) e simulador no Docker | 03/11 |
| M2 | Conta Azure + Terraform + extração incremental em Parquet para a bronze | 09/11 |
| M3 | Silver em PySpark + gold em dbt (estrela, testes) | 13/11 |
| M4 | SQL Warehouse + Power BI (gargalo/lead time, entrega no prazo) + run_pipeline.ps1 + README | 16/11 |
Se atrasar, cortar primeiro: inspeções/expedições na análise, depois a 2ª página do Power BI.

## Ambiente
- Windows, PowerShell, teclado ABNT2. Projeto em C:\Users\Lucas\projects\industrial-data-platform.
- Downloads ficam em A:\Lucas\Downloads.
- Docker Desktop (instalado em %LOCALAPPDATA%\Programs\DockerDesktop) precisa estar aberto antes de usar docker.
- PostgreSQL 18 nativo na porta 5432 NÃO é do projeto. O do projeto é o container erp-db, porta 5433 → 5432, usuário erp_admin, banco erp (.env ignorado pelo Git).
- Python 3.14 no Windows; Python 3.12 para dbt/Databricks; uv; Azure CLI; Terraform; Databricks CLI; dbt-databricks; Azure Storage Explorer.
- No PowerShell, nomes como stash@{0} precisam de aspas simples.

## Repo
- erp/schema.sql (14 tabelas, trigger set_updated_at) e erp/seed.sql carregam sozinhos no primeiro start do container.
- production_stage_events é append-only (start/finish por etapa); quality_inspections também é imutável; shipments é mutável.
- simulator/: determinístico e incremental (rodar de novo só acrescenta e atualiza status). Roda com: docker compose run --rm --build simulator
- Banco do zero: docker compose down -v && docker compose up -d
- Git: GitHub Flow (branch tipo/nome → PR → merge → apagar branch). Commits: feat:, fix:, docs:, chore:.
- Pendente: proteger o main; atualizar o "About" do repo.

## Armadilhas conhecidas
- Arquivo montado no Docker que não existe vira pasta vazia; conferir com Get-Item antes do up.
- Scripts de init do Postgres só rodam com o volume vazio.
- IF NOT EXISTS não altera tabela existente; em banco de teste, recriar com down -v.
- Rodar git pull antes de qualquer trabalho.

# Análise RAD API

API backend para análise estatística de dados do RAD.

## 📁 Estrutura do projeto

- `main.py` - ponto de entrada da aplicação FastAPI.
- `routers.py` - roteamentos e endpoints do serviço.
- `controllers/` - classes que orquestram as regras de negócio para cada rota.
- `services/` - lógica de importação de dados e processamento analítico.
- `db/` - configuração do banco de dados, modelos e sessão assíncrona.
- `dataset/` - pasta onde os arquivos de entrada devem ser colocados para importação.

## ⚙️ Pré-requisitos

- Python 3.10+ (recomendado)
- Banco de dados compatível com SQLAlchemy Async (ex: PostgreSQL)
- arquivos `.xlsx` de entrada no diretório `dataset/`

## 🚀 Instalação

1. Abra o terminal na pasta do projeto:

```powershell
cd "c:\Users\Lipe Tomé\Documents\IF\Projeto de extensão\application\back-end"
```

2. Crie e ative o ambiente virtual (se ainda não tiver):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

3. Instale as dependências:

```powershell
pip install -r requirements.txt
```

## 🔧 Configuração

Crie um arquivo `.env` na raiz do projeto com a variável de conexão do banco de dados:

```env
DATABASE_URL=postgresql+asyncpg://usuario:senha@localhost:5432/nome_do_banco
```

> O código atual usa `DATABASE_URL` para instanciar o engine assíncrono do SQLAlchemy.

## ▶️ Executando a aplicação

Inicie o servidor FastAPI com uvicorn:

```powershell
uvicorn main:app --reload
```

A API estará disponível em:

- `http://localhost:8000`
- Documentação automática: `http://localhost:8000/docs`

## 📥 Importando os dados do RAD

A importação dos arquivos `.xlsx` não é executada automaticamente ao iniciar o servidor. Para popular o banco com os dados existentes, use o comando Python abaixo:

```powershell
python -c "import asyncio, main; asyncio.run(main.main())"
```

Isso irá:
- criar as tabelas do banco de dados
- ler os arquivos `.xlsx` dentro de `dataset/`
- importar os dados para as tabelas `servidor` e `rad`

## 🧩 Endpoints disponíveis

As rotas estão prefixadas com `/rad` e expostas pelo `routers.py`.

- `GET /rad/trend` - tendência de carga por período letivo
- `GET /rad/describe` - estatísticas descritivas de totais e atividades
- `GET /rad/describe_by_period` - descrição filtrada por campus e período
- `GET /rad/activities_distribution` - distribuição das atividades
- `GET /rad/activities_by_period` - atividades por período
- `GET /rad/docents_by_activity` - docentes por atividade
- `GET /rad/docents_by_activities_intersection` - docentes por interseção de atividades

### Parâmetros comuns

- `campus` - filtrar por nome de campus
- `start_period` - início do período letivo
- `end_period` - fim do período letivo
- `activities` - lista de atividades para interseção

## 💡 Observações

- O importador busca somente arquivos com extensão `.xlsx` em `dataset/`.
- Se não houver arquivos `.xlsx`, nenhum registro será importado.
- Caso queira automatizar a importação ao iniciar a aplicação, descomente a linha `asyncio.run(main())` em `main.py`.

---

Feito para facilitar o setup de desenvolvedores e permitir testes rápidos da API localmente.
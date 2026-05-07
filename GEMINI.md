# ArkLog - Relator de Progresso com IA

O ArkLog é um relator de progresso baseado em IA que transforma atividades técnicas (commits do GitHub) em relatórios organizacionais inteligentes. Ele posta automaticamente esses relatórios em plataformas de gestão de projetos como o ClickUp, fornecendo aos stakeholders atualizações claras e legíveis por humanos, sem intervenção manual.

## Visão Geral da Arquitetura

O ArkLog segue uma arquitetura modular e orientada a eventos usando um `EventBus` assíncrono interno.

### Camadas Principais
- **API (`app/api`):** Roteadores FastAPI para webhooks, projetos, relatórios e análises.
- **Serviços (`app/services`):** Orquestração de lógica de negócio e manipulação de eventos (ex: `CommitService`, `ReportService`).
- **Domínio (`app/domain`):** Entidades puras e definições de eventos, livres de dependências de framework.
- **Integrações (`app/integrations`):** Adaptadores para plataformas externas (GitHub, ClickUp). Novas plataformas são adicionadas implementando `BasePublisher`.
- **Motor de IA (`app/ai`):** Construtor de contexto e renderizador de prompts que faz interface com APIs compatíveis com OpenAI (padrão: OpenRouter/Gemini).
- **Modelos/Repositórios (`app/models`, `app/repositories`):** ORM SQLAlchemy (Async) e camada de acesso a dados.

### Fluxo de Eventos
1. **`github.push`**: Disparado por Webhooks do GitHub. Manipulado pelo `CommitService` para persistir novos commits.
2. **`commit.batch_ready`**: Disparado pelo `CommitService` (após um push) ou pelo `Scheduler` (diário/semanal).
3. **`report.generated`**: Disparado pelo `ReportService` após a IA gerar o conteúdo. Manipulado pelos `Publishers` (ex: `ClickUpPublisher`).

## Construção e Execução (Backend)

### Pré-requisitos
- Python 3.12+
- SQLite (padrão) ou PostgreSQL

### Configuração
```bash
# Instalar dependências
pip install -e ".[dev]"

# Configurar ambiente
cp .env.example .env
# Necessário: GITHUB_WEBHOOK_SECRET, AI_API_KEY, CLICKUP_API_TOKEN, CLICKUP_TEAM_ID

# Inicializar banco de dados
alembic upgrade head
```

### Executando a Aplicação
```bash
# Iniciar servidor FastAPI com auto-reload
uvicorn app.main:app --reload
```

### Executando Testes
```bash
# Executar suíte de testes completa
pytest

# Executar com cobertura
pytest --cov=app
```

## Construção e Execução (Frontend/Dashboard)

O frontend é uma aplicação Single Page (SPA) moderna construída com **React**, **Tailwind CSS** e **Lucide Icons**.

### Pré-requisitos
- Node.js 18+
- npm ou yarn

### Configuração e Execução
```bash
cd dashboard
npm install
npm run dev
```
A aplicação roda por padrão em `http://localhost:5173`. O Vite está configurado para fazer proxy das requisições `/api` para o backend na porta 8000.

### Executando Testes
O projeto utiliza **Vitest** para testes unitários e **Playwright** para testes de ponta a ponta (E2E).

```bash
# Testes Unitários (React Testing Library)
npm test

# Testes E2E (Navegador real)
npm run test:e2e
```

## Convenções de Desenvolvimento

### Padrões de Código (Frontend)
- **Componentes:** Funcionais com React Hooks.
- **Estilização:** Tailwind CSS utilitário. Use a classe `.glass-card` para o estilo padrão de cartões.
- **Ícones:** Lucide-React. Se um ícone de marca (como Github) falhar na exportação, use um SVG customizado no componente.
- **Estado Global:** Context API (`AuthContext`) para autenticação.
- **Chamadas de API:** Axios com interceptors para injeção automática de JWT.

### Padrões de Código
- **Type Hints:** Obrigatórios para todas as funções e membros de classe.
- **E/S Assíncrona:** Use `async/await` para todas as operações de E/S. Evite chamadas bloqueantes em funções assíncronas.
- **Logging Estruturado:** Use `structlog`. Prefira pares chave-valor em vez de formatação de string: `logger.info("nome_do_evento", chave=valor)`.
- **Datas/Horas:** Use datetimes **UTC ingênuos (naive)**. Utilize `app.utils.datetime_utils.naive_utcnow()`.
- **Tratamento de Erros:** Capture exceções específicas; evite `except:`.

### Estrutura do Projeto
- `app/ai/`: Os templates de prompt estão localizados em `prompts/` e são renderizados pelo `ContextBuilder`.
- `app/core/events.py`: Fonte única de verdade para a topologia de eventos. Registre novos assinantes em `_wire_event_handlers()`.
- `app/integrations/`: Cada plataforma tem seu próprio subdiretório com um `client.py` (wrapper de API) e `publisher.py` (assinante de evento).

### Adicionando um Novo Publisher
1. Crie `app/integrations/<plataforma>/`.
2. Implemente `BasePublisher` em `publisher.py`.
3. Instancie e assine em `app/core/events.py` -> `_wire_event_handlers()`.
4. Adicione as configurações necessárias em `app/core/config.py`.

## Arquivos Chave
- `app/main.py`: Ponto de entrada e fábrica FastAPI.
- `app/core/config.py`: Configurações centralizadas usando Pydantic.
- `app/core/events.py`: Gerenciamento de ciclo de vida e fiação do barramento de eventos.
- `app/ai/report_generator.py`: Lógica de IA e prompts do sistema.
- `app/models/tables.py`: Definições de esquema de banco de dados.
- `projects.yaml`: (Opcional/Legado) Configuração inicial do projeto.

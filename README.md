# SecurePass — Gerador de Senhas Seguras

Aplicação em Python que gera senhas aleatórias e **criptograficamente seguras** a partir de critérios configuráveis. Oferece três interfaces que compartilham **o mesmo núcleo de regras de negócio**:

- **Interface web** responsiva (FastAPI + Jinja2 + HTML/CSS/JS);
- **API REST** (`POST /api/v1/passwords/generate`);
- **CLI** (`python -m app.cli`).

> Projeto acadêmico de laboratório (Pós-graduação — UFG), focado em fundamentos de Engenharia de Software: Clean Code, TDD, separação de responsabilidades e segurança de aplicações.

---

## Sumário

1. [Problema](#1-problema)
2. [Objetivos](#2-objetivos)
3. [Funcionalidades](#3-funcionalidades)
4. [Tecnologias](#4-tecnologias)
5. [Decisões arquiteturais](#5-decisões-arquiteturais)
6. [Estrutura de diretórios](#6-estrutura-de-diretórios)
7. [Pré-requisitos](#7-pré-requisitos)
8. [Instalação](#8-instalação)
9. [Inicialização](#9-inicialização)
10. [Uso pela web](#10-uso-pela-web)
11. [Uso pela CLI](#11-uso-pela-cli)
12. [Uso da API](#12-uso-da-api)
13. [Testes](#13-testes)
14. [Comandos do Makefile](#14-comandos-do-makefile)
15. [Execução no VS Code](#15-execução-no-vs-code)
16. [Segurança das senhas](#16-segurança-das-senhas)
17. [Limitações](#17-limitações)
18. [Evolução](#18-evolução)
19. [Histórico de commits](#19-histórico-de-commits)
20. [Checklist de verificação](#20-checklist-de-verificação)
21. [Licença](#21-licença)
22. [Uso de IA Generativa](#22-uso-de-inteligência-artificial-generativa)

---

## 1. Problema

Senhas criadas por pessoas tendem a ser curtas, previsíveis e reutilizadas. Muitos geradores simples usam o módulo `random`, cujo gerador (Mersenne Twister) é **previsível**: observando saídas suficientes é possível reconstruir o estado interno e prever as próximas. O SecurePass resolve isso usando exclusivamente a fonte de aleatoriedade segura do sistema operacional (módulo `secrets`) e garantindo que a senha respeite exatamente as categorias escolhidas.

## 2. Objetivos

- Gerar senhas com aleatoriedade criptograficamente segura.
- Permitir configuração de comprimento, categorias de caracteres e quantidade.
- Garantir ao menos um caractere de cada categoria marcada e nenhum de categorias desmarcadas.
- Manter uma única implementação da regra de negócio, reutilizada por web, API e CLI.
- Demonstrar TDD, Clean Code, tipagem, documentação e uso responsável de IA.

## 3. Funcionalidades

| Requisito | Descrição | Onde |
|---|---|---|
| RF01 | Comprimento de 8 a 128 (padrão 16), com validação | `app/core/constants.py`, `password_generator.py` |
| RF02–RF05 | Maiúsculas, minúsculas, números e símbolos `!@#$%&*()-_=+` | `app/core/constants.py` |
| RF06 | Ao menos um caractere por categoria marcada; nenhum de desmarcadas | `generate_password` |
| RF07 | `secrets.choice` + Fisher–Yates com `secrets.randbelow` | `generate_password`, `secure_shuffle` |
| RF08 | 1 a 10 senhas por solicitação | `generate_passwords` |
| RF09 | Interface web responsiva, cópia, regeneração, validação e indicador de entropia | `app/templates`, `app/static` |
| RF10 | CLI com mensagens claras e códigos de saída | `app/cli.py` |
| RF11 | `POST /api/v1/passwords/generate` com validação Pydantic | `app/api/routes.py`, `app/schemas/password.py` |

## 4. Tecnologias

| Camada | Tecnologia | Versão fixada |
|---|---|---|
| Linguagem | Python | 3.12+ (validado em 3.13.5) |
| Backend web | FastAPI | 0.147.0 |
| Servidor ASGI | Uvicorn | 0.54.0 |
| Templates | Jinja2 | 3.1.6 |
| Frontend | HTML5, CSS3, JavaScript (sem frameworks) | — |
| Testes | Pytest / pytest-cov | 9.1.1 / 7.1.0 |
| Testes da API | HTTPX (via `TestClient`) | 0.28.1 |
| Formatação | Black | 26.10.1 |
| Análise estática | Ruff (inclui regras de segurança Bandit e docstrings) | 0.17.1 |
| Automação | GNU Make | — |

Nenhum banco de dados, autenticação ou serviço externo é utilizado.

## 5. Decisões arquiteturais

**Arquitetura em camadas simples**, sem abstrações artificiais:

```text
      Navegador (HTML/CSS/JS)          Terminal
              │ fetch POST JSON            │
              ▼                            ▼
   app/main.py + app/api/routes.py     app/cli.py         ← apresentação / interfaces
              │  (app/schemas: contrato Pydantic)
              └──────────────┬─────────────┘
                             ▼
              app/core/password_generator.py              ← domínio (regras de negócio)
                             │
              app/core/constants.py                       ← configuração única
```

- **Núcleo independente das interfaces.** `password_generator.py` não importa FastAPI, argparse nem nada de apresentação. Por isso é testado isoladamente e reutilizado sem duplicação (DRY, SRP).
- **Constantes como fonte única de verdade.** Limites e conjuntos de caracteres ficam em `constants.py`. O Pydantic, a CLI e o template HTML leem esses valores; o HTML recebe até os tamanhos dos conjuntos (`data-pool-size`) para o indicador de entropia, de modo que o JavaScript não redefine os caracteres. `CHARACTER_SETS` é um `MappingProxyType` (somente leitura), evitando estado global mutável.
- **Funções em vez de classes.** O gerador não tem estado; uma classe ou interface (ex.: `PasswordGeneratorProtocol`) não traria benefício concreto (YAGNI/KISS). SOLID aparece onde ajuda: responsabilidade única por módulo e dependência das interfaces em relação ao domínio, nunca o inverso.
- **Validação em duas camadas, sem duplicar regras.** O Pydantic valida *estrutura* (tipos em modo estrito, faixas, campos extras proibidos). O núcleo valida *regras de negócio* (categorias, comprimento ≥ nº de categorias) e é a autoridade final; a API apenas converte `PasswordGenerationError` em HTTP 422.
- **Exceções explícitas.** `PasswordGenerationError` (subclasse de `ValueError`) para valores inválidos; `TypeError` para tipos incorretos (incluindo `bool`, que em Python é subclasse de `int`).
- **O JavaScript não gera senhas.** Toda geração ocorre no backend com `secrets`; o JS apenas valida o formulário, calcula a estimativa de entropia e exibe resultados.
- **Adaptações da estrutura proposta** (com justificativa):
  - Os arquivos ficam na raiz do repositório (`GeradorSenhas/`) em vez de uma subpasta `securepass/`, pois o repositório já é o projeto.
  - `tests/test_web.py` foi adicionado para separar os testes da página/arquivos estáticos dos testes do contrato da API.
  - `.gitattributes` força finais de linha LF (o Makefile exige tabulações e LF; o Git no Windows convertia para CRLF).
  - `.vscode/` contém configurações para executar e depurar no VS Code.

## 6. Estrutura de diretórios

```text
GeradorSenhas/
├── app/
│   ├── __init__.py
│   ├── main.py                    # App FastAPI, página inicial, cabeçalhos de segurança
│   ├── cli.py                     # Interface de linha de comando
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py              # POST /api/v1/passwords/generate
│   ├── core/
│   │   ├── __init__.py
│   │   ├── constants.py           # Limites e conjuntos de caracteres
│   │   └── password_generator.py  # Regras de negócio e geração segura
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── password.py            # Modelos Pydantic (contrato da API)
│   ├── templates/
│   │   └── index.html
│   └── static/
│       ├── css/style.css
│       └── js/script.js
├── tests/
│   ├── conftest.py
│   ├── test_password_generator.py
│   ├── test_api.py
│   ├── test_web.py
│   └── test_cli.py
├── .vscode/ (settings.json, launch.json)
├── .gitattributes
├── .gitignore
├── LICENSE
├── Makefile
├── pyproject.toml
├── README.md
└── requirements.txt
```

## 7. Pré-requisitos

- Python **3.12 ou superior** (`python --version`).
- Git.
- Opcional: GNU Make (no Windows, os comandos manuais equivalentes estão na seção 14).
- Opcional: VS Code com as extensões *Python*, *Black Formatter* e *Ruff*.

## 8. Instalação

```bash
git clone <URL-DO-REPOSITORIO> GeradorSenhas
cd GeradorSenhas
python -m venv .venv
```

Ative o ambiente virtual:

| Sistema | Comando |
|---|---|
| Windows (PowerShell) | `.\.venv\Scripts\Activate.ps1` |
| Windows (cmd) | `.venv\Scripts\activate.bat` |
| Linux/macOS | `source .venv/bin/activate` |

> No PowerShell, se a ativação for bloqueada pela política de execução, rode antes (vale apenas para a sessão atual):
> `Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned`

Instale as dependências:

```bash
make install
# ou, sem Make:
python -m pip install -r requirements.txt
```

## 9. Inicialização

```bash
make run
# ou, sem Make:
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

- Interface web: <http://127.0.0.1:8000/>
- Documentação interativa (Swagger UI): <http://127.0.0.1:8000/docs>
- Esquema OpenAPI: <http://127.0.0.1:8000/openapi.json>

## 10. Uso pela web

1. Acesse <http://127.0.0.1:8000/>.
2. Ajuste o comprimento (controle deslizante ou campo numérico, 8–128).
3. Marque as categorias desejadas (pelo menos uma).
4. Defina a quantidade de senhas (1–10).
5. Observe o indicador de **entropia estimada**, atualizado em tempo real.
6. Clique em **Gerar senhas**. Cada senha tem um botão **Copiar**.
7. Use **Gerar novas senhas** para gerar outro lote com as mesmas opções.

Entradas inválidas (comprimento fora da faixa, quantidade inválida, nenhuma categoria) exibem mensagens claras antes do envio; o servidor valida novamente e suas mensagens de erro também são exibidas.

## 11. Uso pela CLI

```bash
python -m app.cli --length 20 --uppercase --lowercase --numbers --symbols --count 3
python -m app.cli -l 12 -L -D          # atalhos: -U -L -D -S
python -m app.cli --help
```

Cada senha é impressa em uma linha (stdout). Erros vão para stderr.

| Código de saída | Significado |
|---|---|
| `0` | Senhas geradas com sucesso (ou `--help`) |
| `2` | Argumentos inválidos: valor fora da faixa, nenhuma categoria, valor não inteiro ou opção desconhecida |

Exemplo de erro:

```text
$ python -m app.cli --length 4 --numbers
Erro: O comprimento deve estar entre 8 e 128 caracteres.
```

Não há categorias marcadas por padrão na CLI: a seleção deve ser explícita, e a ausência de categorias gera erro.

## 12. Uso da API

### Contrato

`POST /api/v1/passwords/generate` — corpo JSON (todos os campos são opcionais):

| Campo | Tipo | Padrão | Regra |
|---|---|---|---|
| `length` | inteiro | 16 | 8 a 128 |
| `uppercase` | booleano | `true` | — |
| `lowercase` | booleano | `true` | — |
| `numbers` | booleano | `true` | — |
| `symbols` | booleano | `true` | — |
| `count` | inteiro | 1 | 1 a 10 |

Validação em **modo estrito**: `"16"` (texto), `16.0`/`16.5` (decimais) e `"yes"` (booleano em texto) são rejeitados; campos desconhecidos também.

| Status | Quando | Corpo |
|---|---|---|
| `200` | Sucesso | `{"passwords": [...], "length": n, "count": n}` |
| `422` | Erro de tipo/faixa/campo extra (Pydantic) | `{"detail": [ {...}, ... ]}` (lista de erros) |
| `422` | Nenhuma categoria selecionada (regra de negócio) | `{"detail": "Selecione pelo menos uma categoria de caracteres."}` |
| `405` | Método diferente de POST | — |

### Exemplos

As senhas abaixo estão mascaradas propositalmente; a resposta real contém senhas aleatórias.

```bash
curl -X POST http://127.0.0.1:8000/api/v1/passwords/generate \
  -H "Content-Type: application/json" \
  -d '{"length": 16, "uppercase": true, "lowercase": true, "numbers": true, "symbols": true, "count": 1}'
```

```json
{"passwords": ["****************"], "length": 16, "count": 1}
```

PowerShell:

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/v1/passwords/generate `
  -ContentType "application/json" `
  -Body '{"length": 20, "uppercase": true, "lowercase": false, "numbers": true, "symbols": true, "count": 3}'
```

Erro de regra de negócio:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/passwords/generate \
  -H "Content-Type: application/json" \
  -d '{"uppercase": false, "lowercase": false, "numbers": false, "symbols": false}'
```

```json
{"detail": "Selecione pelo menos uma categoria de caracteres."}
```

## 13. Testes

```bash
make test
# ou, sem Make:
python -m pytest --cov --cov-report=term-missing
```

O desenvolvimento seguiu o ciclo **Red → Green → Refactor**: os testes do núcleo foram commitados antes da implementação (commit `test(core): add failing password generation tests (TDD red)`), e o mesmo foi feito para API, CLI e página web, confirmando a falha antes de implementar.

Cenários cobertos:

- Comprimento mínimo e máximo; abaixo/acima do limite; zero e negativo; não inteiro (`float`, `str`, `None`, `bool`).
- Nenhuma categoria; conjunto vazio; comprimento menor que o número de categorias.
- Apenas maiúsculas, minúsculas, números ou símbolos; todas as categorias.
- Presença obrigatória de cada categoria escolhida e ausência das desmarcadas (testes repetidos no comprimento mínimo, onde a garantia é mais exigida).
- Múltiplas senhas; quantidade inválida e não inteira.
- **Uso de aleatoriedade segura**: `secrets.choice` e `secrets.randbelow` são substituídos por dublês determinísticos, e o teste verifica a saída exata e as chamadas do Fisher–Yates. Não se compara duas senhas aleatórias como "prova" de segurança.
- Contrato da API (campos, padrões, 422, 405), cabeçalhos `no-store` e de segurança, exemplos mascarados no OpenAPI.
- CLI com argumentos válidos, inválidos, `--help` e execução como módulo (`python -m app.cli`).

Resultado da última execução (Windows 11, Python 3.13.5): **81 testes aprovados**, cobertura total de **99%** e **100%** em `app/core`. A única linha não medida é `sys.exit(main())` em `cli.py`, executada em subprocesso pelo teste `test_cli_runs_as_module`. Cobertura alta não é garantia de qualidade; ela só indica que todo o código foi exercitado.

## 14. Comandos do Makefile

| Comando | Ação | Equivalente manual (Windows sem Make) |
|---|---|---|
| `make install` | Instala as dependências | `python -m pip install -r requirements.txt` |
| `make run` | Inicia o Uvicorn com recarga automática | `python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000` |
| `make test` | Executa os testes com cobertura | `python -m pytest --cov --cov-report=term-missing` |
| `make format` | Formata o código com Black | `python -m black app tests` |
| `make lint` | Ruff + verificação de formatação | `python -m ruff check app tests` e `python -m black --check app tests` |

Variáveis podem ser sobrescritas: `make run PORT=9000`, `make install PYTHON=python3`.

> Para ter `make` no Windows: `winget install GnuWin32.Make`, `choco install make` ou usar WSL/Git Bash com Make instalado.

## 15. Execução no VS Code

1. Abra a pasta do projeto no VS Code (`code .`).
2. Instale as extensões recomendadas: **Python**, **Black Formatter** (`ms-python.black-formatter`) e **Ruff** (`charliermarsh.ruff`).
3. Crie o ambiente e instale as dependências (seção 8). `.vscode/settings.json` já aponta o interpretador para `.venv`; se necessário, use *Ctrl+Shift+P → Python: Select Interpreter*.
4. **Executar/depurar**: aba *Run and Debug* (Ctrl+Shift+D) → escolha **SecurePass: servidor web** ou **SecurePass: CLI** → F5.
5. **Testes**: aba *Testing* (ícone de frasco), já configurada para Pytest.
6. Formatação com Black e correções do Ruff são aplicadas ao salvar arquivos Python.

## 16. Segurança das senhas

### Geração

- **Fonte de aleatoriedade**: `secrets`, que usa o CSPRNG do sistema operacional. O módulo `random` não é usado em nenhum ponto (e o Ruff, com as regras de segurança `S`, apontaria seu uso).
- **Algoritmo** (`generate_password`):
  1. valida tipo e faixa do comprimento;
  2. valida as categorias (ao menos uma, nenhuma vazia, `length >= nº de categorias`);
  3. sorteia **um caractere obrigatório de cada categoria** com `secrets.choice`;
  4. completa o restante sorteando do conjunto combinado (sem caracteres repetidos entre conjuntos, para não enviesar a distribuição);
  5. embaralha tudo com **Fisher–Yates** usando `secrets.randbelow`, para que os caracteres obrigatórios não fiquem nas primeiras posições.

### Indicador de entropia (estimativa)

A interface exibe `entropia ≈ comprimento × log₂(tamanho do conjunto)`, arredondada para baixo. Ex.: 16 caracteres com as 4 categorias (75 símbolos possíveis) ≈ 99 bits.

Limitações desse indicador:

- É uma **estimativa matemática para senhas aleatórias**, não uma garantia contra ataques.
- A garantia de "ao menos um de cada categoria" reduz levemente o espaço de busca; a estimativa ignora essa redução, que é pequena.
- Não considera vazamentos, reutilização, phishing, malware, armazenamento inseguro ou limitações do serviço onde a senha será usada.
- Os rótulos (fraca < 60, razoável < 80, forte < 100, muito forte ≥ 100 bits) são faixas didáticas.

### Proteções da aplicação

| Medida | Implementação |
|---|---|
| Nenhum registro em log | Não há logs da aplicação; o log de acesso do Uvicorn registra apenas método, caminho e status. Senhas trafegam só no corpo da resposta. |
| Nenhuma persistência | Sem banco de dados ou arquivos; o JS não usa `localStorage`, `sessionStorage` ou cookies (verificado no teste E2E). |
| Sem senhas na URL | Geração via `POST` com JSON; nenhum parâmetro de consulta. |
| Sem cache | `Cache-Control: no-store, no-cache, must-revalidate, max-age=0`, `Pragma: no-cache`, `Expires: 0` em todas as respostas; `fetch` com `cache: "no-store"`. |
| Inserção segura no HTML | Jinja2 com autoescape; no JS, senhas entram no DOM só via `textContent`. |
| CSP | `default-src 'self'`, sem scripts inline, `frame-ancestors 'none'`, `object-src 'none'`, `base-uri 'none'`. A Swagger UI (`/docs`) fica fora da CSP porque depende de CDN e scripts inline. |
| Outros cabeçalhos | `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`. |
| Documentação sem senhas reais | Exemplos do OpenAPI usam asteriscos (`****************`); ReDoc desativado. |
| Sem monitoramento | Nenhuma ferramenta de telemetria configurada. Observação: o FastAPI 0.147 instala `opentelemetry-api` como dependência transitiva; sem SDK e exportador configurados, ela não coleta nem envia dados. |
| Área de transferência | O botão copiar usa `navigator.clipboard`; a página avisa que outros programas podem ler a área de transferência. |

## 17. Limitações

- Sem HTTPS próprio: para uso fora de `localhost`, coloque a aplicação atrás de um proxy reverso com TLS. A API de área de transferência só funciona em contexto seguro (HTTPS ou localhost).
- A interface web depende de JavaScript (há aviso `<noscript>` indicando a CLI).
- Sem limitação de taxa (rate limiting) no endpoint.
- Conjunto de símbolos fixo (`!@#$%&*()-_=+`); alterá-lo exige editar `constants.py`.
- Não há opção para excluir caracteres ambíguos (`0/O`, `1/l/I`).
- Os testes de interface no navegador foram feitos manualmente/por script descartável, não fazem parte da suíte automatizada.
- O `Makefile` foi escrito para GNU Make, mas **não foi executado** no ambiente de desenvolvimento (Windows sem Make). Os comandos equivalentes foram executados manualmente.

## 18. Evolução

- Opção de excluir caracteres ambíguos e de definir símbolos personalizados.
- Geração de frases-senha (*passphrases*) com lista de palavras (diceware).
- Rate limiting e cabeçalho `Strict-Transport-Security` para implantação pública.
- Testes E2E automatizados (ex.: Playwright) no pipeline.
- Integração contínua (GitHub Actions) com `make lint` e `make test`.
- Empacotamento (`pip install .`) com *entry point* `securepass` para a CLI.
- Imagem Docker para implantação.

## 19. Histórico de commits

Sequência efetivamente realizada (Conventional Commits):

```text
chore: initialize project structure
test(core): add failing password generation tests (TDD red)
feat(core): implement secure password generation
feat(cli): add command-line password generator
feat(api): add password generation endpoint
feat(ui): implement responsive password generator
fix(cli): escape percent sign in symbols help text
docs: add project documentation and VS Code configuration
```

Use `git log --oneline` para conferir.

## 20. Checklist de verificação

| Critério | Status | Evidência |
|---|---|---|
| Funcionalidades RF01–RF11 implementadas | ✅ | Seção 3; testes em `tests/` |
| Aleatoriedade segura (`secrets`) | ✅ | `test_generation_uses_secrets_choice_and_randbelow`, `test_secure_shuffle_implements_fisher_yates_with_randbelow` |
| Categorias respeitadas | ✅ | `test_respects_selected_and_excluded_categories`, `test_all_categories_are_present_when_all_selected` |
| Interface web funcional | ✅ | Teste E2E no Edge headless: geração, regeneração, cópia, validações, indicador |
| Endpoint da API | ✅ | `tests/test_api.py`; teste manual com Uvicorn real |
| CLI independente da web | ✅ | `tests/test_cli.py`; execução real `python -m app.cli` |
| Testes aprovados | ✅ | 81 aprovados |
| Black e Ruff sem apontamentos | ✅ | `black --check` e `ruff check` sem erros |
| Docstrings em funções/classes públicas | ✅ | Regras `D` do Ruff (convenção Google) ativas para `app/` |
| Sem persistência de senhas | ✅ | Seção 16 |
| `make` executado | ⚠️ Não verificado | GNU Make indisponível no ambiente; comandos manuais equivalentes executados |
| Revisão humana do código | ☐ | **[A PREENCHER PELO DESENVOLVEDOR]** |

## 21. Licença

Distribuído sob a licença MIT. Consulte [LICENSE](LICENSE).

## 22. Uso de Inteligência Artificial Generativa

### Ferramentas utilizadas

- **Claude Code** (CLI da Anthropic), com o modelo **Claude Opus 5.5**, operando diretamente no repositório: criou arquivos, executou testes, ferramentas de qualidade e commits.
- Outras ferramentas: **[A PREENCHER PELO DESENVOLVEDOR, se houver]**

### Como a IA foi utilizada

O desenvolvedor forneceu um prompt detalhado com requisitos funcionais e não funcionais, tecnologias, arquitetura, estratégia TDD e critérios de aceitação. A partir dele, a IA:

- **Algoritmo**: implementou `generate_password` (um caractere obrigatório por categoria + preenchimento + Fisher–Yates com `secrets.randbelow`), a remoção de caracteres repetidos entre conjuntos e a rejeição explícita de `bool` como inteiro.
- **Testes**: escreveu os testes antes da implementação (Red) e confirmou as falhas executando o Pytest; criou dublês determinísticos para `secrets.choice`/`secrets.randbelow`; parametrizou cenários de borda.
- **Documentação**: escreveu as docstrings (Google Style, em português), os comentários de decisões e este README.
- **Refatoração e qualidade**: aplicou Black/Ruff, configurou regras de segurança (Bandit via Ruff) e de docstrings.
- **Verificação**: subiu o servidor real, fez requisições HTTP e executou um teste E2E descartável no Microsoft Edge headless (via Chrome DevTools Protocol) para validar a interface.

### Problemas encontrados e soluções adotadas

Ocorridos de fato durante o desenvolvimento:

1. **`--help` da CLI lançava `ValueError`**: o `%` do conjunto de símbolos era interpretado como formatação pelo `argparse`. Encontrado ao executar a CLI manualmente (não havia teste para `--help`). Solução: teste de regressão + escape `%%` (commit `fix(cli)`).
2. **Indicador de entropia inconsistente**: 16 × log₂(75) ≈ 99,66 bits era exibido como "100 bits (forte)", embora "muito forte" comece em 100. Encontrado no teste com navegador headless. Solução: arredondar para baixo e usar o mesmo valor no texto e no rótulo.
3. **Falso positivo do Ruff (S105)** em teste que compara a saída determinística de um mock com uma string fixa. Solução: ignorar S105/S106 apenas em `tests/`, com justificativa no `pyproject.toml`.
4. **Aviso de depreciação do Starlette 1.9** recomendando `httpx2` no `TestClient`. Como o requisito exige HTTPX, apenas essa mensagem específica foi silenciada no Pytest, com comentário.
5. **Conversão CRLF pelo Git no Windows**, que pode afetar o Makefile. Solução: `.gitattributes` com `eol=lf`.
6. **Conflito de atalhos na CLI** (`-l` para comprimento × minúsculas). Solução: categorias com letras maiúsculas (`-U -L -D -S`).
7. **Commits verdes**: os testes da página foram separados em `tests/test_web.py` para que o commit da API não dependesse da interface ainda inexistente.

Outros problemas percebidos pelo desenvolvedor: **[A PREENCHER PELO DESENVOLVEDOR]**

### Decisões revisadas pelo desenvolvedor

- **[A PREENCHER PELO DESENVOLVEDOR]**: ex.: concordância com o uso de funções em vez de classes, com os padrões da API (todas as categorias `true`) versus a CLI (nenhuma por padrão), com a exclusão da CSP para `/docs`.

### Limitações das sugestões da IA

- A IA pode produzir código plausível porém incorreto. Os dois bugs acima foram introduzidos pela própria IA e só foram detectados por **execução real**, não por leitura.
- Escolhas de projeto (limites de entropia, padrões da CLI, textos da interface) são sugestões razoáveis, não requisitos validados com usuários.
- A IA não substitui uma revisão de segurança independente nem testes com usuários reais.

### Importância da validação humana

O desenvolvedor é responsável pelo código entregue. Recomenda-se: ler e compreender cada módulo, executar `make test` e `make lint` localmente, testar a interface manualmente, revisar as decisões listadas acima e registrar nesta seção o que foi alterado após a revisão.

Produtividade e tempo economizado: **[A PREENCHER PELO DESENVOLVEDOR, se desejar; não foram medidos]**

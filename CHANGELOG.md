# Changelog

Todas as mudanças relevantes deste projeto são registradas neste arquivo.

O formato segue o [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/) e o projeto adota o [Versionamento Semântico](https://semver.org/lang/pt-BR/).

## [1.0.0] - 2026-10-19

Primeira versão estável.

### Adicionado

- Núcleo de geração de senhas criptograficamente seguras (`secrets.choice` + Fisher–Yates com `secrets.randbelow`), com comprimento de 8 a 128 e de 1 a 10 senhas por solicitação (RF01–RF08).
- Opção para excluir caracteres ambíguos `0 O 1 l I` na web, na API e na CLI.
- CLI independente da web (`python -m app.cli`), com mensagens claras e códigos de saída (RF10).
- API REST `POST /api/v1/passwords/generate` com validação Pydantic (RF11).
- Interface web responsiva com cópia, regeneração, validação e indicador de entropia (RF09).
- Identidade visual AKCIT, perfis rápidos, ocultar/limpar senhas, cores por tipo de caractere, tema manual e dicas por nível de entropia.
- Suíte de testes com Pytest (130 testes aprovados), Black e Ruff sem apontamentos.
- README com instalação, uso, segurança, capturas de tela e diagramas de funcionamento.

### Corrigido

- Escape do sinal de porcentagem no texto de ajuda de símbolos da CLI.

[1.0.0]: https://github.com/leandrorodriguess/GeradorSenhas/releases/tag/v1.0.0

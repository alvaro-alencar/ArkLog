# ArkLog: conexões pertencentes ao usuário

O ArkLog não recebe token pessoal do proprietário por variável de ambiente.
Álvaro e qualquer cliente usam o mesmo fluxo de autorização.

## Arquitetura

```text
Conexão de fonte → adaptador de coleta → eventos normalizados → OpenRouter → relatório → adaptador de destino
```

A primeira combinação implementada é:

```text
GitHub → OpenRouter → Slack
```

O núcleo já recebe eventos normalizados para que Notion, ClickUp, Jira, Linear,
Vercel e outros provedores possam entrar sem alterar o contrato do LLM.

## O que pertence à plataforma

As variáveis abaixo não concedem acesso à conta GitHub ou Slack de nenhuma pessoa:

- `DATABASE_URL`: banco persistente do ArkLog;
- `AI_API_KEY`: chave da OpenRouter usada sob cota;
- `CONNECTIONS_ENCRYPTION_KEY`: criptografa tokens de usuários no banco;
- `OAUTH_STATE_SECRET`: assina o retorno temporário do OAuth;
- `GITHUB_CLIENT_ID` e `GITHUB_CLIENT_SECRET`: identificam o aplicativo OAuth ArkLog;
- `SLACK_CLIENT_ID` e `SLACK_CLIENT_SECRET`: identificam o aplicativo OAuth ArkLog.

## O que pertence ao usuário

Os tokens devolvidos pelo GitHub e Slack:

- são vinculados ao usuário e à organização Ark;
- são criptografados antes de chegar ao banco;
- nunca são incluídos nas respostas da API;
- não são enviados ao navegador depois do callback;
- podem ser revogados pela tela **Conexões**.

## URLs de produção

Use estas URLs ao cadastrar os aplicativos OAuth:

```text
GitHub callback:
https://www.arksystem.net/api/arklog/v1/connections/github/callback

Slack callback:
https://www.arksystem.net/api/arklog/v1/connections/slack/callback
```

Na Vercel do ArkLog:

```text
PUBLIC_APP_URL=https://www.arksystem.net/arklog
GITHUB_REDIRECT_URI=https://www.arksystem.net/api/arklog/v1/connections/github/callback
SLACK_REDIRECT_URI=https://www.arksystem.net/api/arklog/v1/connections/slack/callback
```

## GitHub

A versão inicial usa um OAuth App e solicita leitura da identidade, e-mail e
repositórios acessíveis pelo usuário. A interface permite selecionar qual
repositório alimentará cada fluxo. Uma evolução futura poderá trocar o OAuth App
por uma GitHub App para permitir autorização granular por instalação e por
repositório já na tela do GitHub.

## Slack

O aplicativo solicita:

- leitura de canais públicos;
- leitura dos canais privados aos quais o bot foi adicionado;
- publicação de mensagens.

O fluxo salva apenas o identificador do canal escolhido. O token do bot fica no
cofre criptografado da conexão.

## Teste gratuito

A conexão não gera consumo. O custo ocorre apenas ao executar um fluxo.
Uma conta `TRIAL` recebe exatamente um relatório, com janela máxima de sete dias.
A cota é reservada antes da OpenRouter e devolvida se coleta, IA ou publicação
falhar.

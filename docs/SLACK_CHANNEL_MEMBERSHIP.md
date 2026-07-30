# Participação do ArkLog em canais Slack

O ArkLog usa um bot pertencente ao workspace conectado pelo usuário. Com a permissão mínima `chat:write`, o bot só publica em canais dos quais participa.

Para liberar um canal, abra-o no Slack e execute:

```text
/invite @ArkLog
```

Canais privados sempre exigem convite explícito. A API traduz o erro `not_in_channel` para essa orientação, sem expor tokens ou detalhes internos.

"""Safe, actionable Slack error messages for ArkLog users."""

from __future__ import annotations


def publication_error_message(error: str) -> str:
    """Translate provider codes without exposing credentials or internals."""
    normalized = error.strip().lower()
    messages = {
        "not_in_channel": (
            "O bot ArkLog ainda não participa do canal escolhido. "
            "Abra o canal no Slack, digite /invite @ArkLog e tente novamente."
        ),
        "channel_not_found": (
            "O canal do Slack não está mais acessível ao ArkLog. "
            "Confirme o canal, convide @ArkLog e tente novamente."
        ),
        "is_archived": "O canal escolhido foi arquivado no Slack. Escolha outro canal.",
        "account_inactive": "A conexão do Slack foi desativada. Reconecte o workspace.",
        "invalid_auth": "A conexão do Slack expirou ou foi revogada. Reconecte o workspace.",
        "token_revoked": "A conexão do Slack foi revogada. Reconecte o workspace.",
        "missing_scope": (
            "A conexão do Slack não possui a permissão necessária. "
            "Reconecte o workspace e tente novamente."
        ),
    }
    return messages.get(normalized, f"O Slack recusou a publicação: {error}.")

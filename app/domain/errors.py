"""Erreurs métier. Le web les traduit en pages d'erreur, le serveur MCP en messages."""

from __future__ import annotations


class GotchaError(Exception):
    """Base de toutes les erreurs métier."""


class NotFoundError(GotchaError):
    """Fiche, piège ou contribution introuvable."""


class InvalidInputError(GotchaError):
    """Donnée refusée ; le message est affichable tel quel à l'utilisateur."""


class IdentityError(GotchaError):
    """Le fournisseur d'identité (GitHub) n'a pas pu identifier le développeur."""


class SecretDetectedError(GotchaError):
    """Le texte envoyé semble contenir une clé ou un jeton : on refuse de l'enregistrer."""

    def __init__(self, kinds: list[str]) -> None:
        self.kinds = kinds
        super().__init__("Votre texte semble contenir un secret : " + ", ".join(kinds))

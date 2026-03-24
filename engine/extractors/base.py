"""
Classe de base pour tous les extracteurs de documents.

Un extracteur prend en entrée le texte brut OCR d'un document
et retourne un modèle de données structuré (ExtractedXxx).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class ExtractionResult(BaseModel):
    success: bool
    data: dict[str, Any] | None = None
    confidence: float = 0.0
    errors: list[str] = []
    raw_text: str | None = None


class BaseExtractor(ABC, Generic[T]):
    """
    Extracteur de base.

    Le flux d'extraction :
    1. Réception du texte brut OCR (ou image)
    2. Appel LLM avec un prompt structuré (schema JSON)
    3. Parsing + validation de la réponse
    4. Retour du modèle typé

    TODO: implémenter la logique d'appel LLM (Anthropic Claude)
    avec un system prompt métier par type de document.
    """

    @abstractmethod
    def get_extraction_prompt(self) -> str:
        """Retourne le prompt système pour ce type de document."""
        ...

    @abstractmethod
    def get_json_schema(self) -> dict[str, Any]:
        """Retourne le schéma JSON attendu en sortie."""
        ...

    @abstractmethod
    def parse_response(self, raw_response: str) -> T:
        """Parse la réponse LLM et retourne le modèle typé."""
        ...

    def extract(self, ocr_text: str) -> ExtractionResult:
        """
        Point d'entrée principal.

        TODO: implémenter l'appel à l'API LLM (Claude).
        TODO: gérer les retries sur erreur de parsing.
        TODO: calculer le score de confiance de l'extraction.
        """
        raise NotImplementedError

"""Classe abstraite pour les extracteurs de données.

Chaque extracteur prend du texte OCR brut et utilise le LLM (Qwen2.5)
pour structurer les données en JSON.
"""

import json
from abc import ABC, abstractmethod

import ollama

from config.settings import MODEL_TEXT


class BaseExtractor(ABC):
    """Classe de base pour l'extraction structurée de données."""

    @property
    @abstractmethod
    def prompt_template(self) -> str:
        """Template du prompt d'extraction. Doit contenir {ocr_text}."""
        ...

    @property
    @abstractmethod
    def document_type(self) -> str:
        """Type de document (carte_grise, cni, etc.)."""
        ...

    def extract(self, ocr_text: str) -> dict:
        """Extrait les données structurées depuis le texte OCR.

        Args:
            ocr_text: Texte brut issu de l'OCR.

        Returns:
            Dict avec les données extraites.
        """
        prompt = self.prompt_template.format(ocr_text=ocr_text)

        response = ollama.chat(
            model=MODEL_TEXT,
            messages=[{"role": "user", "content": prompt}],
        )

        raw = response["message"]["content"].strip()

        try:
            start = raw.find("{")
            end = raw.rfind("}") + 1
            if start >= 0 and end > start:
                data = json.loads(raw[start:end])
            else:
                data = {"_error": f"Pas de JSON trouvé dans: {raw[:200]}"}
        except json.JSONDecodeError:
            data = {"_error": f"JSON invalide: {raw[:200]}"}

        data["_document_type"] = self.document_type
        return data

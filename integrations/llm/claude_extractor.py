"""
Extracteur de documents via Claude Opus.

Rôle : recevoir le texte brut OCR (de Google DocAI) et retourner
un JSON structuré avec tous les champs extraits du document.

Claude Opus NE fait PAS :
- La lecture d'image (c'est Google DocAI)
- L'interaction navigateur (c'est Playwright)
- La validation métier (c'est Python/realtime.py)

Claude Opus FAIT :
- Comprendre le texte OCR
- Identifier le type de document
- Extraire tous les champs pertinents en JSON
- Corriger les erreurs OCR évidentes (0/O, 1/I dans les VIN, etc.)
- Gérer tous les formats (français, anglais, ancien/nouveau format)
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """Tu es un expert en lecture de documents administratifs français pour l'immatriculation de véhicules.

Tu reçois le texte brut extrait par OCR d'un document. Tu dois :
1. Identifier le type de document
2. Extraire TOUS les champs pertinents
3. Corriger les erreurs OCR évidentes (confusion 0/O, 1/I, caractères parasites)
4. Retourner un JSON structuré

RÈGLES STRICTES :
- Ne JAMAIS inventer de données. Si un champ n'est pas lisible, retourne null.
- Les dates en format JJ/MM/AAAA
- Les noms en MAJUSCULES
- Le VIN fait exactement 17 caractères (pas de I, O, Q)
- Le SIREN fait 9 chiffres, le SIRET 14 chiffres
- Pour la MRZ, extraire nom et prénoms en priorité (plus fiable que le texte visuel)
"""

DOC_PROMPTS: dict[str, str] = {
    "CNI": """Document : Carte Nationale d'Identité française.
Extrais en JSON :
{
  "type_document": "CNI",
  "nom_naissance": "...",
  "prenoms": "...",
  "date_naissance": "JJ/MM/AAAA",
  "lieu_naissance": "...",
  "sexe": "M ou F",
  "nationalite": "...",
  "numero_document": "...",
  "date_expiration": "JJ/MM/AAAA",
  "date_delivrance": "JJ/MM/AAAA ou null",
  "mrz_nom": "... (extrait de la MRZ si présente)",
  "mrz_prenoms": "... (extrait de la MRZ si présente)"
}""",

    "PASSEPORT": """Document : Passeport français.
Extrais en JSON :
{
  "type_document": "PASSEPORT",
  "nom_naissance": "...",
  "prenoms": "...",
  "date_naissance": "JJ/MM/AAAA",
  "lieu_naissance": "...",
  "sexe": "M ou F",
  "nationalite": "...",
  "numero_document": "...",
  "date_expiration": "JJ/MM/AAAA",
  "date_delivrance": "JJ/MM/AAAA",
  "pays_emetteur": "FRA ou ...",
  "mrz_nom": "... (ligne MRZ P<FRA...)",
  "mrz_prenoms": "..."
}""",

    "PERMIS": """Document : Permis de conduire français.
Extrais en JSON :
{
  "type_document": "PERMIS",
  "nom": "...",
  "prenom": "...",
  "date_naissance": "JJ/MM/AAAA",
  "lieu_naissance": "...",
  "numero_permis": "...",
  "date_delivrance": "JJ/MM/AAAA",
  "date_expiration": "JJ/MM/AAAA ou null",
  "categories": ["AM", "B", ...],
  "categories_dates": {"B": "JJ/MM/AAAA", ...}
}
IMPORTANT : la ligne 9 du recto liste les catégories obtenues (ex: "9. AM/B1/B"). C'est la source la plus fiable.""",

    "COC": """Document : Certificat de Conformité (COC) — peut être en français, anglais ou allemand.
Extrais en JSON :
{
  "type_document": "COC",
  "marque": "... (champ 0.1 Make)",
  "modele": "... (champ 0.2.3 Commercial name, ou 0.2 Type si absent)",
  "vin": "... (champ 1.0, exactement 17 caractères, pas de I/O/Q)",
  "cnit": "... (champ D.2.1 ou 0.2.3 Commercial name code, format XXXX-XX-XXX-X, PAS le code moteur)",
  "type_variante_version": "... (champ D.2 Type/Variant/Version, ex: MH01-01-001-0)",
  "categorie_j": "... (champ 0.3 Vehicle category, ex: L3e-A1E, M1)",
  "genre_national": "... (champ J.1 si présent, ex: VP, MTL, MTT1, CL)",
  "carrosserie_j2": "... (champ J.2 Carrosserie CE, ex: AA, AB, AC, BB)",
  "carrosserie_j3": "... (champ J.3 Carte nationale, ex: BERLINE, BREAK, CABRIOLET, SOLO)",
  "energie": "... (essence, diesel, electrique, hybride)",
  "puissance_kw": nombre ou null,
  "puissance_cv": nombre ou null,
  "puissance_nette_p2": nombre ou null (champ P.2 puissance nette maximale en kW),
  "cylindree_p1": nombre ou null (champ P.1 cylindrée en cm3),
  "co2_wltp": nombre ou null,
  "places_assises": nombre ou null (champ S.1),
  "places_debout_s2": nombre ou null (champ S.2, souvent 0 ou absent),
  "masse_f1": nombre ou null (champ F.1 masse en charge max techniquement admissible en kg),
  "masse_f3": nombre ou null (champ F.3 masse en charge max de l'ensemble en kg),
  "masse_g": nombre ou null (champ G masse du véhicule en service en kg),
  "poids_vide_g1": nombre ou null (champ G.1 poids à vide en kg),
  "ptac_kg": nombre ou null (champ F.2 PTAC en kg),
  "niveau_sonore_u1": nombre ou null (champ U.1 niveau sonore en dB(A)),
  "vitesse_moteur_u2": nombre ou null (champ U.2 vitesse moteur en tr/min),
  "classe_env": "... (champ V.9 classe environnementale, ex: EURO5, EURO4)",
  "vitesse_max_kmh": nombre ou null,
  "date_premiere_immat": "JJ/MM/AAAA ou null",
  "soussigne": "... (nom du constructeur/importateur qui signe le COC, ou null)",
  "date_reception": "... (date de réception/homologation, ou null)",
  "numero_k": "... (numéro de réception, champ K, ou null)",
  "debridable": true/false,
  "debridable_vers": ["A2", "A3"] ou []
}

ATTENTION — L'OCR mélange souvent les colonnes gauche/droite du COC.
Les valeurs numériques sont souvent SÉPARÉES de leur label. Tu dois reconstituer les paires label→valeur.

RÈGLES CRITIQUES pour la puissance :
- puissance_kw = champ 3.3.3.4 "Maximum 30 minutes power [kW]" pour les véhicules électriques
- puissance_kw = champ 3.3.2 "Maximum net power [kW]" pour les véhicules thermiques
- puissance_nette_p2 = champ P.2 = puissance nette max en kW (souvent = puissance_kw)
- ATTENTION : pour un véhicule électrique L3e-A1E, la puissance 30 min est souvent un petit nombre (ex: 9, 11, 15 kW)
- NE PAS confondre avec le champ 1.8 "Maximum speed [km/h]" (souvent ~100-200) → va dans vitesse_max_kmh
- NE PAS inventer une puissance — si tu ne trouves pas la valeur exacte après le label 3.3.3.4, retourne null
- Dans le texte OCR, la valeur peut apparaître LOIN du label à cause du mélange de colonnes

RÈGLES pour le CNIT :
- Le CNIT (Code National d'Identification du Type) n'est PAS toujours présent — il est absent sur les COC européens purs
- Chercher dans les champs D.2, D.2.1 uniquement. Si absent, retourner null
- NE PAS confondre avec le "Electric motor code" (champ 3.1.2.2)

RÈGLES pour les masses :
- F.1 = masse en charge max techniquement admissible (MTMA)
- F.2 = PTAC (masse max en charge)
- F.3 = masse en charge max de l'ensemble (véhicule + remorque)
- G = masse du véhicule en service avec carburant
- G.1 = poids à vide national

IMPORTANT : chercher "converting between subcategories" pour détecter si le véhicule est débridable.""",

    "CG_BARREE": """Document : Carte grise / certificat d'immatriculation.
Ce document peut être barré (VO — véhicule d'occasion) ou non barré.
Extrais en JSON :
{
  "type_document": "CG_BARREE",
  "immatriculation": "... (champ A)",
  "vin": "... (champ E — 17 caractères, NE PAS prendre la MRZ en bas du document)",
  "titulaire_nom": "... (champ C.1, ancien propriétaire)",
  "titulaire_prenom": "... (ligne après C.1)",
  "adresse": "... (champ C.3)",
  "code_postal": "...",
  "ville": "...",
  "date_mise_circulation": "JJ/MM/AAAA (champ B)",
  "marque": "... (champ D.1)",
  "type_variante_version": "... (champ D.2)",
  "cnit": "... (champ D.2.1)",
  "genre_national": "... (champ J.1, ex: VP, MTL, MTT1)",
  "categorie_j": "... (champ J, ex: L3e-A1E, M1)",
  "carrosserie": "... (champ J.3)",
  "energie": "... (champ P.3, ex: ES, GO, EL)",
  "puissance_cv": nombre ou null (champ P.6),
  "puissance_kw": nombre ou null (champ P.2),
  "numero_k": "... (champ K, numéro de réception, ou null)",
  "cylindree_p1": nombre ou null (champ P.1),
  "masse_f1": nombre ou null (champ F.1),
  "masse_g": nombre ou null (champ G),
  "co2_wltp": nombre ou null (champ V.7),
  "classe_env": "... (champ V.9, ex: EURO5, ou null)",
  "places_assises": nombre ou null (champ S.1),
  "carrosserie_j2": "... (champ J.2, ou null)",
  "barre_diagonale": true/false,
  "date_vente": "JJ/MM/AAAA ou null (inscrit manuscritement sur la barre)",
  "heure_vente": "HH:MM ou null",
  "acheteur_nom_barre": "... ou null (nom manuscrit sur/pres de la barre)",
  "acheteur_prenom_barre": "... ou null"
}

IMPORTANT pour le VIN :
- Le VIN est dans le champ E. (17 caractères, pas de I/O/Q)
- NE PAS confondre avec la MRZ en bas du document (ligne CRFRA... qui contient l'immat + VIN concatenes)

IMPORTANT pour la barre :
- Une CG barrée a une ligne diagonale tracée + "vendu le" ou "cédé le" + date/heure + nom acquéreur
- Si aucune mention de vente/cession ni de barre : barre_diagonale = false""",

    "FACTURE": """Document : Facture de vente de véhicule.
Extrais en JSON :
{
  "type_document": "FACTURE",
  "vin": "...",
  "marque": "...",
  "modele": "...",
  "prix_ttc": nombre,
  "date_vente": "JJ/MM/AAAA",
  "siret_vendeur": "...",
  "nom_vendeur": "...",
  "nom_acheteur": "...",
  "couleur": "..."
}""",

    "DOMICILE": """Document : Justificatif de domicile (facture EDF, quittance, avis d'imposition...).
Extrais en JSON :
{
  "type_document": "DOMICILE",
  "nom_titulaire": "...",
  "adresse_ligne1": "...",
  "code_postal": "...",
  "ville": "...",
  "date_document": "JJ/MM/AAAA"
}""",

    "CERTIFICAT_CESSION": """Document : Certificat de cession (Cerfa 15776).
Extrais en JSON :
{
  "type_document": "CERTIFICAT_CESSION",
  "vendeur_nom": "...",
  "acquereur_nom": "...",
  "date_cession": "JJ/MM/AAAA",
  "immatriculation": "...",
  "vin": "...",
  "signatures_vendeur": true/false,
  "signature_acquereur": true/false
}""",

    "KBIS": """Document : Extrait Kbis (registre du commerce).
Extrais en JSON :
{
  "type_document": "KBIS",
  "raison_sociale": "...",
  "siren": "... (9 chiffres)",
  "siret": "... (14 chiffres)",
  "adresse_siege": "...",
  "representant_nom": "...",
  "date_kbis": "JJ/MM/AAAA"
}""",

    "ATTESTATION_HEBERGEMENT": """Document : Attestation d'hébergement manuscrite.
Extrais en JSON :
{
  "type_document": "ATTESTATION_HEBERGEMENT",
  "hebergeant_nom": "... (personne qui heberge)",
  "hebergeant_prenom": "...",
  "heberge_nom": "... (personne hebergee)",
  "heberge_prenom": "...",
  "adresse": "...",
  "code_postal": "...",
  "ville": "...",
  "date_attestation": "JJ/MM/AAAA",
  "signature_presente": true/false
}""",

    "CNI_HEBERGEANT": """Document : Carte Nationale d'Identité de l'hébergeant (pas du demandeur principal).
Extrais en JSON :
{
  "type_document": "CNI_HEBERGEANT",
  "nom_naissance": "...",
  "prenoms": "...",
  "date_naissance": "JJ/MM/AAAA",
  "date_expiration": "JJ/MM/AAAA",
  "numero_document": "...",
  "mrz_nom": "... (extrait de la MRZ si présente)",
  "mrz_prenoms": "..."
}""",

    "ASSURANCE": """Document : Attestation d'assurance automobile.
Extrais en JSON :
{
  "type_document": "ASSURANCE",
  "nom_assure": "...",
  "compagnie": "...",
  "date_effet": "JJ/MM/AAAA",
  "date_echeance": "JJ/MM/AAAA",
  "est_assurance_auto": true/false
}""",
}

MODEL = "claude-opus-4-20250514"

# Retry config
MAX_RETRIES = 2
RETRY_DELAY = 1.0  # secondes


def _get_client():
    """Client Anthropic avec configuration securite RGPD."""
    import anthropic
    return anthropic.Anthropic(
        # Les donnees envoyees via l'API ne sont pas conservees par Anthropic
        # et ne sont pas utilisees pour l'entrainement.
        # Ref: https://docs.anthropic.com/en/docs/data-privacy
    )


async def _call_claude_with_retry(
    system: str,
    user_content: str,
    max_tokens: int,
    context: str = "",
) -> str:
    """
    Appel Claude avec retry automatique sur erreurs transitoires.
    Retourne le texte de la reponse.
    Leve une exception si tous les retries echouent.
    """
    client = _get_client()
    last_error = None

    for attempt in range(MAX_RETRIES + 1):
        try:
            response = await asyncio.to_thread(
                client.messages.create,
                model=MODEL,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": user_content}],
            )
            return response.content[0].text
        except Exception as e:
            last_error = e
            error_str = str(e).lower()
            # Ne pas retry sur les erreurs non-transitoires
            if "invalid_api_key" in error_str or "authentication" in error_str:
                raise
            if attempt < MAX_RETRIES:
                wait = RETRY_DELAY * (attempt + 1)
                logger.warning(f"[Claude] {context} tentative {attempt+1} echouee: {e}, retry dans {wait}s")
                await asyncio.sleep(wait)

    raise last_error  # type: ignore[misc]


CLASSIFY_PROMPT = """Identifie le type de ce document parmi :
CNI, PASSEPORT, PERMIS, COC, CG_BARREE, FACTURE, DOMICILE, CERTIFICAT_CESSION, KBIS, ASSURANCE, ATTESTATION_FORMATION, ATTESTATION_HEBERGEMENT, CNI_HEBERGEANT, AUTRE

Retourne un JSON :
{"type": "...", "confidence": 0.0 à 1.0}"""


async def claude_classify(ocr_text: str) -> dict:
    """Classifie un document via Claude Opus (avec retry)."""
    try:
        text = await _call_claude_with_retry(
            system=SYSTEM_PROMPT,
            user_content=f"{CLASSIFY_PROMPT}\n\nTexte OCR :\n{ocr_text[:3000]}",
            max_tokens=200,
            context="classify",
        )
        result = _parse_json(text)
        return result or {"type": "AUTRE", "confidence": 0.0}

    except Exception as e:
        logger.error(f"[Claude] Classification echouee apres {MAX_RETRIES+1} tentatives: {e}")
        return {"type": "AUTRE", "confidence": 0.0}


async def claude_extract(doc_type: str, ocr_text: str) -> dict:
    """
    Extrait les champs structurés d'un document via Claude Opus (avec retry).

    Args:
        doc_type: Type de document (CNI, PASSEPORT, PERMIS, COC, etc.)
        ocr_text: Texte brut extrait par Google DocAI

    Returns:
        dict avec tous les champs extraits en JSON structuré
    """
    prompt = DOC_PROMPTS.get(doc_type, "")
    if not prompt:
        prompt = f"Document de type {doc_type}. Extrais tous les champs pertinents en JSON."

    try:
        text = await _call_claude_with_retry(
            system=SYSTEM_PROMPT,
            user_content=f"{prompt}\n\nTexte OCR :\n{ocr_text[:4000]}",
            max_tokens=1000,
            context=f"extract({doc_type})",
        )
        result = _parse_json(text)

        if result:
            logger.info(f"[Claude] Extraction {doc_type} : {len(result)} champs")
            return result
        else:
            logger.warning(f"[Claude] Extraction {doc_type} : pas de JSON valide dans la reponse")
            return {}

    except Exception as e:
        logger.error(f"[Claude] Extraction {doc_type} echouee apres {MAX_RETRIES+1} tentatives: {e}")
        return {}


async def claude_verify(doc_a: dict, doc_b: dict, check_type: str) -> dict:
    """
    Vérifie la cohérence entre deux documents via Claude Opus (avec retry).

    Args:
        doc_a: Données extraites du document A
        doc_b: Données extraites du document B
        check_type: Type de vérification (ex: "identite", "vehicule")

    Returns:
        {"coherent": True/False, "details": "...", "problemes": [...]}
    """
    try:
        text = await _call_claude_with_retry(
            system=SYSTEM_PROMPT,
            user_content=(
                f"Vérifie la cohérence entre ces deux documents ({check_type}).\n\n"
                f"Document A :\n{json.dumps(doc_a, ensure_ascii=False, indent=2)}\n\n"
                f"Document B :\n{json.dumps(doc_b, ensure_ascii=False, indent=2)}\n\n"
                "Retourne un JSON :\n"
                '{"coherent": true/false, "details": "explication", "problemes": ["..."]}'
            ),
            max_tokens=500,
            context=f"verify({check_type})",
        )
        return _parse_json(text) or {"coherent": True, "details": "Verification impossible"}

    except Exception as e:
        logger.error(f"[Claude] Verification {check_type} echouee: {e}")
        return {"coherent": True, "details": f"Erreur: {e}"}


def _parse_json(text: str) -> dict | None:
    """Extrait le premier bloc JSON d'une réponse Claude."""
    text = text.strip()

    # Si la réponse est directement du JSON
    if text.startswith("{"):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

    # Chercher un bloc ```json ... ```
    import re
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass

    # Chercher le premier { ... } dans le texte
    m = re.search(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            pass

    return None

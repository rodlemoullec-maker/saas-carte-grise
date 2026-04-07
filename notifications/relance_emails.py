"""
Générateur d'emails de relance pré-rédigés.

Lit les blocages d'un dossier (codes V-XX) et produit un texte d'email
prêt à coller dans le client email habituel de l'agent (Gmail, Outlook,
Thunderbird).

L'agent ne fait que copier-coller — l'éditeur AutoDoc Pro n'envoie aucun
email, ne stocke aucun email, et n'a accès à aucun email transmis. Le pro
conserve la maîtrise totale de la communication avec son client.

Usage :
    from notifications.relance_emails import generate_relance_email

    text = generate_relance_email(
        dossier=dossier_db,
        agent=agent_db,
    )
    # → l'agent copie ce texte dans son client email
"""
from __future__ import annotations

import logging
from typing import Any

from engine.templates.relance import (
    EMAIL_CERFA_PRET,
    EMAIL_FOOTER,
    EMAIL_HEADER,
    GENERIC_BLOCAGE_TEMPLATE,
    RELANCE_TEMPLATES,
)

logger = logging.getLogger(__name__)


# ─── API publique ───────────────────────────────────────────────────────────


def generate_relance_email(
    dossier: Any,
    agent: Any,
) -> dict:
    """
    Génère le texte d'email de relance pour un dossier en blocage.

    Args:
        dossier: instance DossierDB (avec blocages, validation_warnings, etc.)
        agent: instance Professionnel (le profil de l'agent local)

    Returns:
        dict avec :
        - subject : sujet d'email pré-rempli
        - body : corps de l'email prêt à copier
        - to : adresse email du client (si connue)
        - blocages_count : nombre de problèmes identifiés
        - mode : "relance" | "cerfa_pret" | "no_blocages"
    """
    # Récupérer les blocages
    blocages = _extract_blocages_list(dossier)
    warnings = _extract_warnings_list(dossier)

    # Préparer les variables de personnalisation
    context = _build_context(dossier, agent)

    # ─── Cas 1 : aucun blocage et diagnostic VERT → email "Cerfa prêt" ──
    if not blocages and getattr(dossier, "diagnostic", None) == "VERT":
        body = EMAIL_CERFA_PRET.format(**context)
        return {
            "subject": _build_subject_cerfa_pret(dossier),
            "body": body,
            "to": _client_email(dossier),
            "blocages_count": 0,
            "mode": "cerfa_pret",
        }

    # ─── Cas 2 : aucun blocage mais pas encore VERT → rien à demander ──
    if not blocages and not warnings:
        return {
            "subject": "",
            "body": "",
            "to": _client_email(dossier),
            "blocages_count": 0,
            "mode": "no_blocages",
            "message": (
                "Aucun blocage identifié sur ce dossier. "
                "Lancez d'abord le diagnostic pour vérifier l'état complet."
            ),
        }

    # ─── Cas 3 : blocages → générer la relance ─────────────────────────
    sections = _build_sections(blocages, warnings)
    body = _assemble_email(context, sections)

    return {
        "subject": _build_subject_relance(dossier, len(sections)),
        "body": body,
        "to": _client_email(dossier),
        "blocages_count": len(sections),
        "mode": "relance",
    }


# ─── Helpers d'extraction ───────────────────────────────────────────────────


def _extract_blocages_list(dossier: Any) -> list[dict]:
    """Récupère la liste des blocages depuis le dossier (gère les formats variés)."""
    raw = getattr(dossier, "blocages", None)
    if not raw:
        return []
    if isinstance(raw, list):
        return [b for b in raw if isinstance(b, dict)]
    if isinstance(raw, dict):
        # Certains formats : {"blocages": [...]}
        if "blocages" in raw and isinstance(raw["blocages"], list):
            return raw["blocages"]
        # Sinon on transforme en liste à entrée unique
        return [raw]
    return []


def _extract_warnings_list(dossier: Any) -> list[dict]:
    """Récupère la liste des avertissements (non bloquants mais utiles)."""
    raw = getattr(dossier, "validation_warnings", None)
    if not raw:
        return []
    if isinstance(raw, list):
        return [w for w in raw if isinstance(w, dict)]
    if isinstance(raw, dict):
        if "warnings" in raw and isinstance(raw["warnings"], list):
            return raw["warnings"]
        return [raw]
    return []


def _client_email(dossier: Any) -> str | None:
    """Retourne l'email du client s'il est connu."""
    return getattr(dossier, "client_email", None) or None


# ─── Construction du contexte de personnalisation ──────────────────────────


def _build_context(dossier: Any, agent: Any) -> dict:
    """
    Prépare les variables de personnalisation à injecter dans les templates.
    """
    client_prenom = getattr(dossier, "client_prenom", None) or ""
    client_nom = getattr(dossier, "client_nom", None) or ""

    if client_prenom:
        client_intro = f" {client_prenom}"
    elif client_nom:
        client_intro = f" {client_nom}"
    else:
        client_intro = ""

    # Description du véhicule pour personnaliser
    vehicule_intro = ""
    immat = getattr(dossier, "immatriculation", None)
    vin = getattr(dossier, "vin", None)
    if immat:
        vehicule_intro = f" du véhicule {immat}"
    elif vin:
        vehicule_intro = f" du véhicule {vin[:8]}…"

    # Identité de l'agent
    agent_nom = (
        getattr(agent, "nom_commerce", None)
        or getattr(agent, "raison_sociale", None)
        or "Votre agent"
    )

    agent_signature_parts = []
    adresse = getattr(agent, "adresse", None)
    code_postal = getattr(agent, "code_postal", None)
    ville = getattr(agent, "ville", None)
    if adresse:
        agent_signature_parts.append(adresse)
    if code_postal or ville:
        agent_signature_parts.append(f"{code_postal or ''} {ville or ''}".strip())
    telephone = getattr(agent, "telephone_commerce", None) or getattr(agent, "telephone", None)
    if telephone:
        agent_signature_parts.append(f"Tél : {telephone}")
    email = getattr(agent, "email_commerce", None) or getattr(agent, "email", None)
    if email and email != "agent@local":
        agent_signature_parts.append(email)

    agent_signature = ""
    if agent_signature_parts:
        agent_signature = "\n" + "\n".join(agent_signature_parts)

    return {
        "client_intro": client_intro,
        "client_prenom": client_prenom,
        "client_nom": client_nom,
        "vehicule_intro": vehicule_intro,
        "agent_nom": agent_nom,
        "agent_signature": agent_signature,
    }


# ─── Construction des sections (un point à corriger par blocage) ───────────


def _build_sections(blocages: list[dict], warnings: list[dict]) -> list[dict]:
    """
    Transforme chaque blocage/warning en une section "titre + explication"
    qui sera affichée dans l'email.

    Évite les doublons (si plusieurs blocages partagent le même code, on n'en
    garde qu'un seul dans le mail).
    """
    seen_codes: set[str] = set()
    sections: list[dict] = []

    # Les blocages d'abord (plus prioritaires)
    for b in blocages:
        code = (b.get("code") or "").upper().strip()
        if not code or code in seen_codes:
            continue
        seen_codes.add(code)

        section = _resolve_template(code, b)
        if section:
            sections.append(section)

    # Puis les warnings (informatifs)
    for w in warnings:
        code = (w.get("code") or "").upper().strip()
        if not code or code in seen_codes:
            continue
        # On n'inclut que les warnings qui ont un template dédié
        if code not in RELANCE_TEMPLATES:
            continue
        seen_codes.add(code)
        section = _resolve_template(code, w)
        if section:
            sections.append(section)

    return sections


def _resolve_template(code: str, blocage: dict) -> dict | None:
    """
    Trouve le template adapté à un code de blocage.

    Stratégie :
    1. Match exact sur le code complet
    2. Sinon, fallback générique avec le message brut

    Retourne None si on n'a vraiment rien à dire.
    """
    if code in RELANCE_TEMPLATES:
        tpl = RELANCE_TEMPLATES[code]
        return {
            "titre": tpl["titre"],
            "explication": tpl["explication"],
        }

    # Fallback générique : utilise le message du blocage si dispo
    message = blocage.get("message") or blocage.get("correction") or ""
    if not message:
        return None

    return {
        "titre": GENERIC_BLOCAGE_TEMPLATE["titre"],
        "explication": GENERIC_BLOCAGE_TEMPLATE["explication"].format(message=message),
    }


# ─── Assemblage final ──────────────────────────────────────────────────────


def _assemble_email(context: dict, sections: list[dict]) -> str:
    """
    Assemble l'email final : header + sections puces + footer.
    """
    parts = [EMAIL_HEADER.format(**context)]

    for i, section in enumerate(sections, start=1):
        parts.append(f"{i}. {section['titre']}\n   {section['explication']}\n")

    parts.append(EMAIL_FOOTER.format(**context))
    return "".join(parts)


# ─── Sujets d'email ─────────────────────────────────────────────────────────


def _build_subject_relance(dossier: Any, count: int) -> str:
    """Construit le sujet de l'email de relance."""
    ref = getattr(dossier, "reference", None) or ""
    immat = getattr(dossier, "immatriculation", None) or ""

    if count == 1:
        elements = "1 élément à compléter"
    else:
        elements = f"{count} éléments à compléter"

    if ref and immat:
        return f"Carte grise {immat} ({ref}) — {elements}"
    if ref:
        return f"Carte grise {ref} — {elements}"
    return f"Votre dossier carte grise — {elements}"


def _build_subject_cerfa_pret(dossier: Any) -> str:
    """Sujet quand le dossier est complet et le Cerfa généré."""
    ref = getattr(dossier, "reference", None) or ""
    immat = getattr(dossier, "immatriculation", None) or ""

    if ref and immat:
        return f"Carte grise {immat} ({ref}) — dossier complet"
    if ref:
        return f"Carte grise {ref} — dossier complet"
    return "Votre carte grise — dossier complet"

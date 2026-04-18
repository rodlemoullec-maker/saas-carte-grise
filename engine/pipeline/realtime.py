"""
Pipeline temps reel — logique metier extraite du demo_server.py.

Ce module contient TOUTE la logique metier du systeme :
- OCR (Tesseract + fallback Google DocAI)
- Classification et extraction de documents
- Detection auto VN/VO
- Extraction auto des infos dossier (VIN, nom, etc.)
- Checklist vendeur et client dynamique
- Reglementation permis/puissance/age/anciennete
- Croisements inter-documents
- Diagnostic et estimation taxes
- Messages d'accompagnement

Toutes les fonctions travaillent sur des dicts (format in-memory).
Les routers API convertissent depuis/vers les modeles BDD.
"""
from __future__ import annotations

import hashlib
import logging
import os
import re
import uuid
from datetime import date, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Profil pro (reference globale pour les messages — populee par les routers)
PROFIL_PRO: dict = {}


def set_profil_pro(profil: dict) -> None:
    """Appele par les routers pour peupler PROFIL_PRO depuis la BDD."""
    global PROFIL_PRO
    PROFIL_PRO.update(profil)

# Classification par mots-cles
DOC_TYPES = {
    "CNI": [
        ("carte nationale d'identite", 1.0), ("carte d'identite", 0.9),
        ("republique francaise", 0.3), ("nom de naissance", 0.5),
        ("date de naissance", 0.3), ("nationalite", 0.4),
    ],
    "PASSEPORT": [
        ("passeport", 1.0), ("passport", 0.9),
    ],
    "PERMIS": [
        ("permis de conduire", 1.0), ("driving licence", 0.8),
        ("categories", 0.3), ("prefet", 0.4),
    ],
    "COC": [
        # FR
        ("certificat de conformite", 1.0),
        ("homologation", 0.5), ("cnit", 0.5), ("puissance nette", 0.6),
        ("masse en charge", 0.4),
        # EN — la plupart des COC européens sont rédigés en anglais
        ("certificate of conformity", 1.0),
        ("ec certificate", 1.0),
        ("complete vehicles", 0.6),
        ("manufacturer", 0.4), ("vehicle identification number", 0.5),
        ("type approval", 0.6),
    ],
    "FACTURE": [
        ("facture n", 0.9), ("total ttc", 0.7), ("prix", 0.3),
        ("tva", 0.4), ("vehicule neuf", 0.7), ("vehicule", 0.3),
        ("siret", 0.3), ("garage", 0.4), ("acheteur", 0.3),
    ],
    "DOMICILE": [
        ("edf", 0.7), ("engie", 0.7), ("electricite", 0.5), ("gaz", 0.4),
        ("quittance", 0.6), ("avis d'imposition", 0.7), ("taxe fonciere", 0.6),
        ("attestation d'hebergement", 0.7), ("impot", 0.4),
        ("destinataire", 0.5), ("facture electricite", 0.8),
    ],
    "CG_BARREE": [
        ("certificat d'immatriculation", 1.0), ("carte grise", 1.0),
        ("vendu le", 0.9), ("formule", 0.4), ("titulaire", 0.4),
        ("date de 1", 0.5),  # "Date de 1ère immatriculation" = quasi unique CG
    ],
    "CERTIFICAT_CESSION": [
        ("declaration de cession", 1.0), ("cerfa 15776", 1.0),
        ("15776", 0.9), ("cession d'un vehicule", 0.9),
        ("ancien proprietaire", 0.7), ("nouveau proprietaire", 0.7),
        ("vendeur", 0.3), ("acquereur", 0.3),
        ("date et heure de la cession", 0.8),
    ],
    "KBIS": [
        ("kbis", 1.0), ("extrait du registre", 0.9), ("greffe", 0.7),
        ("tribunal de commerce", 0.7), ("commerce et des societes", 0.6),
        ("raison sociale", 0.5), ("siren", 0.4),
    ],
    "ASSURANCE": [
        ("attestation d'assurance", 1.0), ("assurance automobile", 0.8),
        ("carte verte", 0.8), ("responsabilite civile", 0.6),
        ("compagnie d'assurance", 0.5), ("police", 0.3),
        ("date d'effet", 0.4), ("memo vehicule assure", 0.7),
    ],
    "ATTESTATION_FORMATION": [
        ("attestation de suivi de formation", 1.0),
        ("attestation de formation", 0.9),
        ("suivi de formation", 0.8),
        ("motocyclettes legeres", 0.9),
        ("categorie l5e", 0.8),
        ("formation 7 heures", 0.7), ("formation 7h", 0.7),
        ("date d'obtention de la categorie b", 0.8),
        ("organisme de formation", 0.7),
        ("auto ecole", 0.4), ("moto ecole", 0.5),
        ("permis de conduire en cours de validite", 0.6),
    ],
}


def _ocr_tesseract(file_bytes: bytes, mime_type: str) -> dict:
    """
    Extrait le texte d'un PDF ou image via Tesseract OCR (local, gratuit).

    Retourne {"text": str, "confidence": float} avec le score de confiance moyen.
    """
    import pytesseract
    from PIL import Image
    import io

    images = []

    if mime_type == "application/pdf":
        # D'abord essayer PyPDF (PDF avec texte integre)
        try:
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(file_bytes))
            text = ""
            for page in reader.pages:
                t = page.extract_text()
                if t:
                    text += t + "\n"
            if len(text.strip()) > 50:
                return {"text": text, "confidence": 0.95}  # PDF avec texte natif → haute confiance
        except Exception:
            pass

        # PDF scan → convertir en images
        try:
            from pdf2image import convert_from_bytes
            images = convert_from_bytes(file_bytes, dpi=300)
        except Exception:
            logger.warning("pdf2image echoue (poppler manquant?) — texte vide")
            return {"text": "", "confidence": 0.0}
    else:
        # Image directe (JPG, PNG, TIFF)
        images = [Image.open(io.BytesIO(file_bytes))]

    # OCR Tesseract sur chaque image avec score de confiance
    text = ""
    all_confidences = []
    for img in images:
        t = pytesseract.image_to_string(img, lang="fra")
        text += t + "\n"

        # Extraire les confidences par mot
        data = pytesseract.image_to_data(img, lang="fra", output_type=pytesseract.Output.DICT)
        confidences = [
            int(c) for c in data["conf"]
            if str(c).lstrip("-").isdigit() and int(c) > 0
        ]
        all_confidences.extend(confidences)

    avg_confidence = (
        sum(all_confidences) / len(all_confidences) / 100.0
        if all_confidences else 0.0
    )

    # Si texte trop court, la confiance est probablement surestimee
    if len(text.strip()) < 50:
        avg_confidence = min(avg_confidence, 0.30)

    return {"text": text.strip(), "confidence": avg_confidence}



def _ocr_google_docai(file_bytes: bytes, mime_type: str) -> dict:
    """
    DEPRECATED — conservé pour compatibilité avec les anciens appels du pipeline.

    Dans la version locale d'Imatra, l'OCR passe par PaddleOCR (ou
    Tesseract en fallback) via la factory `get_ocr_provider()`. Cette
    fonction reste un proxy synchrone pour les anciens appels du moteur.

    Retourne {"text": str, "confidence": float}.
    """
    import asyncio
    import concurrent.futures

    try:
        from integrations.ocr_providers import get_ocr_provider
        from config.settings import get_settings

        provider = get_ocr_provider(get_settings().ocr_provider)

        # Le pipeline appelle cette fonction en synchrone — on emballe l'async.
        try:
            running_loop = asyncio.get_running_loop()
        except RuntimeError:
            running_loop = None

        if running_loop is not None:
            # On est dans un event loop — exécuter dans un thread séparé
            with concurrent.futures.ThreadPoolExecutor() as ex:
                fut = ex.submit(
                    asyncio.run, provider.process_document(file_bytes, mime_type)
                )
                result = fut.result()
        else:
            result = asyncio.run(provider.process_document(file_bytes, mime_type))

        return {
            "text": result.full_text,
            "confidence": result.average_confidence,
        }
    except Exception as e:
        logger.warning(f"[OCR local proxy] échec : {e}")
        return {"text": "", "confidence": 0.0}



def classify_document(text: str) -> tuple[str, float, list[str]]:
    """Classifie un document. Retourne (type, confidence, keywords_matches)."""
    text_norm = text.lower()
    for old, new in [("é","e"),("è","e"),("ê","e"),("ë","e"),("à","a"),("â","a"),
                     ("ù","u"),("û","u"),("ô","o"),("î","i"),("ï","i"),("ç","c")]:
        text_norm = text_norm.replace(old, new)

    best_type, best_score, best_kw = "AUTRE", 0.0, []
    for dtype, keywords in DOC_TYPES.items():
        score, matched = 0.0, []
        max_possible = sum(w for _, w in keywords)
        for kw, weight in keywords:
            if kw in text_norm:
                score += weight
                matched.append(kw)
        if max_possible > 0:
            norm_score = score / max_possible
        else:
            norm_score = 0
        if norm_score > best_score:
            best_score = norm_score
            best_type = dtype
            best_kw = matched

    return best_type, round(min(best_score, 1.0), 2), best_kw


# ─── Extraction regex simple ──────────────────────────────────────────────────


# ─── Extraction regex simple ──────────────────────────────────────────────────

def extract_data(doc_type: str, text: str) -> dict:
    """Extrait les champs cles selon le type."""
    data: dict[str, Any] = {}

    # VIN (universel - cherche sur tous les docs)
    # E. suivi du VIN (format CG), ou VIN/chassis explicite
    # NE PAS matcher la MRZ (CRFRA... en bas des CG)
    m = re.search(r"(?:VIN|chassis|E\.)\s*[:\s]*([A-HJ-NPR-Z0-9]{17})\b", text)
    if m:
        data["vin"] = m.group(1)

    # Immatriculation
    m = re.search(r"([A-Z]{2}[\-\s]?\d{3}[\-\s]?[A-Z]{2})", text)
    if m:
        data["immatriculation"] = m.group(1)

    # Dates (format JJ/MM/AAAA)
    dates = re.findall(r"(\d{2}[./]\d{2}[./]\d{4})", text)
    if dates:
        data["dates_detectees"] = dates

    if doc_type == "CNI" or doc_type == "PASSEPORT":
        data["type_identite"] = doc_type  # Pour distinguer CNI vs passeport dans les verifications

        # ─── Champs communs CNI / Passeport ───
        # Nom — formats : "Nom: DUPONT", "Nom/Surname (1)\nDUPONT", "Nom DUPONT"
        m = re.search(r"[Nn]om/[Ss]urname\s*\(\d\)\s*\n\s*([A-Z][A-Z\- ]{1,40})", text)
        if m:
            data["nom_naissance"] = m.group(1).strip()
        else:
            m = re.search(r"[Nn]om\s*(?:de\s*naissance)?\s*[:\s]*([A-Z][A-Z\- ]{1,40})", text)
            if m: data["nom_naissance"] = m.group(1).strip()

        # Prenoms — formats : "Prénoms/Given names (2)\nRodolph, Clément"
        m = re.search(r"[Pp]r[eé]noms?\s*/\s*[A-Za-z ]+\s*\(\d\)\s*\n\s*([A-Za-zÀ-ÿ,\- ]{2,60})", text)
        if m:
            data["prenoms"] = m.group(1).strip()
        else:
            m = re.search(r"[Pp]r[eé]noms?\s*[:\s]*([A-Za-zÀ-ÿ,\- ]{2,60})", text)
            if m: data["prenoms"] = m.group(1).strip()

        m = re.search(r"[Ll]ieu\s*(?:de\s*naissance)?\s*[:\s]*([A-Za-zÀ-ÿ\- ]{2,40})", text)
        if m: data["lieu_naissance"] = m.group(1).strip()
        m = re.search(r"[Nn]ationalit[eé]\s*[:\s]*([A-Za-zÀ-ÿ\- ]{2,30})", text)
        if m: data["nationalite"] = m.group(1).strip()

        # Date de naissance — formats : "15/10/1992", "15.10.1992", "15 10 1992"
        m = re.search(r"(?:n[eé]e?\s*le|[Dd]ate\s*de\s*naissance)\s*[:/\s]*(\d{2}[./]\d{2}[./]\d{4})", text)
        if m:
            data["date_naissance"] = m.group(1)
        else:
            # Format passeport : "Date de naissance/Date...(4)\n15 10 1992"
            m = re.search(r"[Dd]ate\s*de\s*naissance/.*?\n\s*(\d{2})\s+(\d{2})\s+(\d{4})", text)
            if m: data["date_naissance"] = f"{m.group(1)}/{m.group(2)}/{m.group(3)}"

        # Date d'expiration — formats : "16/07/2034", "16.07.2034", "16 07 2034"
        m = re.search(r"(?:expir|[Dd]ate\s*d.expiration)\S*\s*[:/\s]*(\d{2}[./]\d{2}[./]\d{4})", text, re.IGNORECASE)
        if m:
            data["date_expiration"] = m.group(1)
        else:
            # Format passeport : "Date d'expiration/Date of expiry (8)\n16 07 2034"
            m = re.search(r"[Dd]ate\s*d.expiration/.*?\n\s*(\d{2})\s+(\d{2})\s+(\d{4})", text)
            if m: data["date_expiration"] = f"{m.group(1)}/{m.group(2)}/{m.group(3)}"

        # Date de delivrance (pour regle CNI 2004-2013)
        m = re.search(r"[Dd]ate\s*de\s*d[eé]livrance/.*?\n\s*(\d{2})\s+(\d{2})\s+(\d{4})", text)
        if m: data["date_delivrance"] = f"{m.group(1)}/{m.group(2)}/{m.group(3)}"
        if not data.get("date_delivrance"):
            m = re.search(r"[Dd][eé]livr[eé]e?\s*(?:le)?\s*[:\s]*(\d{2}[./]\d{2}[./]\d{4})", text)
            if m: data["date_delivrance"] = m.group(1)

        # Lieu de naissance depuis format passeport
        if not data.get("lieu_naissance"):
            m = re.search(r"[Ll]ieu\s*de\s*naissance/.*?\n\s*([A-Z][A-Za-zÀ-ÿ\- ]{2,30})", text)
            if m: data["lieu_naissance"] = m.group(1).strip()

        # NOTE : l'adresse sur la CNI/passeport n'est PAS extraite pour le Cerfa.
        # L'adresse du Cerfa provient UNIQUEMENT du justificatif de domicile
        # (facture EDF, quittance, etc.) qui atteste de l'adresse actuelle.
        # L'adresse sur la CNI/passeport peut etre obsolete.

        # Taille et sexe (passeport)
        m = re.search(r"[Ss]exe.*?([MF])\b", text)
        if m: data["sexe"] = m.group(1)

        # Deduire le departement de naissance depuis la commune
        lieu = data.get("lieu_naissance")
        if lieu:
            dept = _deduce_departement_from_commune(lieu)
            if dept:
                data["departement_naissance"] = dept

        # ─── MRZ (Machine Readable Zone) — source la plus fiable ───
        # Passeport : P<FRANOM<<PRENOM<PRENOM2...
        # Le nom compose est separe par < (ex: LE<MOULLEC → LE MOULLEC)
        # Les prenoms sont separes par < (ex: RODOLPH<CLEMENT → Rodolph, Clément)
        # MRZ passeport : P<FRA NOM<COMPOSE<<PRENOM1<PRENOM2<<<<
        # Le << (double chevron) separe le nom des prenoms
        # Les < simples separent les mots dans le nom ou entre les prenoms
        m_mrz_line = re.search(r"P<FRA(.+?)(?:\n|$)", text)
        if m_mrz_line:
            data["type_identite"] = "PASSEPORT"
            mrz_content = m_mrz_line.group(1).strip().rstrip("<")
            # Splitter sur << (separateur nom/prenoms)
            parts = mrz_content.split("<<", 1)
            mrz_nom = parts[0].replace("<", " ").strip() if len(parts) > 0 else ""
            mrz_prenoms = parts[1].replace("<", " ").strip() if len(parts) > 1 else ""
            # MRZ prioritaire sur l'OCR du texte (plus fiable)
            if mrz_nom:
                data["nom_naissance"] = mrz_nom
            if mrz_prenoms:
                data["prenoms"] = mrz_prenoms

        # CNI MRZ : IDFRANOM<<PRENOM ou NOM<<PRENOM<
        if not m_mrz_line:
            m = re.search(r"([A-Z]{2,30})<<([A-Z]{2,30})<", text)
            if m:
                if not data.get("nom_naissance"): data["nom_naissance"] = m.group(1)
                if not data.get("prenoms"): data["prenoms"] = m.group(2)

        # Numero de passeport (format : 2 chiffres + 2 lettres + 5 chiffres)
        m_num = re.search(r"\b(\d{2}[A-Z]{2}\d{5})\b", text)
        if m_num: data["numero_document"] = m_num.group(1)

        # Numero CNI (format : variable, souvent 12 chiffres)
        if not data.get("numero_document"):
            m_num_cni = re.search(r"[Nn]o?\s*[:\s]*(\d{12})", text)
            if m_num_cni: data["numero_document"] = m_num_cni.group(1)

        # ─── Extraction specifique CNI ───
        if doc_type == "CNI":
            if not data.get("nom_naissance"):
                m = re.search(r"C\.?1\s+([A-Z]{2,30})", text)
                if m: data["nom_naissance"] = m.group(1).strip()
            # Prenoms : capture la (les) ligne(s) qui suivent l'étiquette
            # "Prénom(s) :" — surtout PAS le mot "Prénom" lui-même.
            if not data.get("prenoms") or data.get("prenoms", "").lower().startswith("pr"):
                m = re.search(
                    r"[Pp]r[eé]nom[s]?\(?\s*s?\s*\)?\s*:?\s*\n+([A-ZÀ-Ÿ][A-Za-zÀ-ÿ\-' ]{1,30})(?:\s*\n([A-ZÀ-Ÿ][A-Za-zÀ-ÿ\-' ]{1,30}))?",
                    text,
                )
                if m:
                    p1 = m.group(1).strip()
                    p2 = (m.group(2) or "").strip()
                    # Filtre les faux positifs (mots qui sont en fait des labels)
                    bad = {"sexe", "ne", "née", "à", "signature", "carte", "nationalité", "république"}
                    if p1.lower() not in bad and len(p1) >= 2:
                        if p2 and p2.lower() not in bad and len(p2) >= 2:
                            data["prenoms"] = f"{p1}, {p2}"
                        else:
                            data["prenoms"] = p1
            # NOTE : l'adresse de la CNI n'est PAS extraite pour le Cerfa.
            # L'adresse du Cerfa vient du justificatif de domicile uniquement.

        # ─── Extraction specifique Passeport ───
        if doc_type == "PASSEPORT":
            # Pays emetteur
            m = re.search(r"(?:[Pp]ays|[Cc]ountry|[Cc]ode)\s*[:\s]*([A-Z]{3})", text)
            if m: data["pays_emetteur"] = m.group(1)
            if not data.get("pays_emetteur") and m_mrz_line:
                data["pays_emetteur"] = "FRA"
            # Sexe (M/F dans la MRZ ou le document)
            m = re.search(r"[Ss]exe\s*[:\s]*([MF])", text)
            if m: data["sexe"] = m.group(1)

        # ─── Verification validite ───
        # La verification d'expiration est faite dans _check_identite_validity()
        # qui est appelee apres l'extraction

    elif doc_type == "PERMIS":
        m = re.search(r"1\.\s*([A-Z\-\s]{2,40})", text)
        if m: data["nom"] = m.group(1).strip()
        m = re.search(r"2\.\s*([A-Za-zÀ-ÿ\-\s]{2,40})", text)
        if m:
            prenom_raw = m.group(1).strip()
            prenom_raw = re.sub(r'([A-Za-zÀ-ÿ]{3,})[^A-Za-zÀ-ÿ\s\-]', r'\1', prenom_raw)
            data["prenom"] = prenom_raw

        # Date de naissance (champ 3)
        m = re.search(r"3\.?\s*(\d{2}[./]\d{2}[./]\d{4})", text)
        if m: data["date_naissance"] = m.group(1)

        # Date de delivrance (champ 4a)
        m = re.search(r"4\s*a\.?\s*(\d{2}[./]\d{2}[./]\d{4})", text)
        if m: data["date_delivrance"] = m.group(1)

        # Date d'expiration (champ 4b)
        m = re.search(r"4\s*[b0]\.?\s*(\d{2}[./]\d{2}[./]\d{4})", text)
        if m: data["date_expiration"] = m.group(1)

        # Categories — priorite 1 : ligne 9 du recto
        m_cat9 = re.search(r"9\.?\s*([A-Z0-9/]{2,30})", text.upper())
        if m_cat9:
            cats_line9 = re.findall(r"(AM|A1|A2|A|BE|B1|B|CE|C|DE|D)", m_cat9.group(1))
            data["categories"] = list(dict.fromkeys(cats_line9))
        else:
            cats_with_date = re.findall(
                r"\b(AM|A1|A2|A|BE|B1|B|CE|C|DE|D)\b\s{0,5}(\d{2}[./]\d{2}[./]\d{2,4})",
                text.upper()
            )
            if cats_with_date:
                valid_cats = list(dict.fromkeys(cat for cat, date in cats_with_date))
                data["categories"] = valid_cats
                data["categories_dates"] = {cat: date for cat, date in cats_with_date}
            else:
                cats = re.findall(r"\b(AM|A1|A2|A|BE|B|CE|C|D)\b", text.upper())
                if cats:
                    data["categories"] = list(dict.fromkeys(cats))
                    data["categories_warning"] = "Extraction par fallback — verifier manuellement"

        # Dates d'obtention par categorie (colonne 10 du verso)
        # Format : "AM ... 29.11.23" ou "B ... 29.11.23"
        # On essaie aussi de matcher la structure du verso
        cats_dates = re.findall(
            r"\b(AM|A1|A2|A|BE|B1|B|CE|C|DE|D)\b[\s\S]{0,20}?(\d{2}[./]\d{2}[./]\d{2,4})",
            text.upper()
        )
        if cats_dates:
            # Ne garder que les categories effectivement dans la liste
            valid_categories = data.get("categories", [])
            dates_par_cat = {}
            for cat, dt in cats_dates:
                if cat in valid_categories and cat not in dates_par_cat:
                    dates_par_cat[cat] = dt
            if dates_par_cat:
                data["categories_dates"] = dates_par_cat

        # Date d'obtention du permis B specifiquement (critique pour la regle des 2 ans)
        if "B" in data.get("categories", []):
            # Chercher dans categories_dates
            date_b = data.get("categories_dates", {}).get("B")
            if date_b:
                data["date_obtention_b"] = date_b
            elif data.get("date_delivrance"):
                # Fallback : date de delivrance du permis
                data["date_obtention_b"] = data["date_delivrance"]

    elif doc_type == "COC":
        # Helper : ligne après une étiquette précise
        def _next_line(label_pattern: str) -> str | None:
            m = re.search(label_pattern + r"[^\n]*\n([^\n]+)", text)
            return m.group(1).strip() if m else None

        # 0.1 Marque (commercial trade name)
        v = _next_line(r"0\.1\.?\s*\n?\s*(?:Make|Marque)")
        if v and v.lower() not in ("trade", "make", "marque"):
            data["marque"] = v.split()[0]  # premier mot uniquement

        # 0.2 Type
        v = _next_line(r"0\.2\.?\s*\n?\s*Type")
        if v and v.lower() not in ("type",):
            data["type_variante_version"] = v
            if not data.get("modele"):
                data["modele"] = v

        # 0.2.3 Commercial name (le vrai nom commercial - "VARG")
        v = _next_line(r"0\.2\.3\.?")
        if v and v.upper() not in ("VARG",) and len(v) <= 30 and not any(c in v for c in [':', '.']):
            data["modele"] = v
        elif v:
            # Cas STARK : "0.2.3.\nVARG" → on récupère VARG
            if re.match(r"^[A-Z][A-Z0-9 \-]{0,30}$", v):
                data["modele"] = v

        # 0.3 Vehicle category
        v = _next_line(r"0\.3\.?\s*\n?\s*Vehicle\s*category")
        if v and re.match(r"^[A-Z]\d", v):
            data["categorie_j"] = v

        # 0.4 Constructeur (nom complet) — déjà capturé via les regex `soussigne`

        # 1.0 VIN (Vehicle identification number)
        v = _next_line(r"1\.0\.?\s*\n?\s*Vehicle\s*identification\s*number")
        if v:
            # VIN = 17 caractères alphanumériques (sans I, O, Q)
            mvin = re.search(r"\b([A-HJ-NPR-Z0-9]{17})\b", v)
            if mvin:
                data["vin"] = mvin.group(1)

        # 1.8 Vitesse maximale [km/h]
        v = _next_line(r"1\.8\.?\s*\n?\s*Maximum\s*speed")
        if v:
            mn = re.search(r"\d+", v)
            if mn:
                data["vitesse_max"] = int(mn.group(0))

        # 2.1.1 Mass in running order = G (poids vide en service)
        v = _next_line(r"2\.1\.1\.?\s*\n?\s*Mass\s*in\s*running\s*order")
        if v:
            mn = re.search(r"\d+", v)
            if mn:
                data["masse_g"] = mn.group(0)
                data["poids_vide_g1"] = mn.group(0)

        # 2.1.3 Technically permissible max laden mass = F.1
        v = _next_line(r"2\.1\.3\.?\s*\n?\s*Technically\s*permissible\s*max\w*\s*laden\s*mass")
        if v:
            mn = re.search(r"\d+", v)
            if mn:
                data["masse_f1"] = mn.group(0)
                data["ptac_kg"] = int(mn.group(0))

        # 3.3.1 Electric vehicle configuration → énergie
        v = _next_line(r"3\.3\.1\.?\s*\n?\s*Electric\s*vehicle\s*configuration")
        if v and re.search(r"electric", v, re.IGNORECASE):
            data["energie"] = "electrique"

        # 3.3.3.4 Puissance électrique max 30 min [kW] → P.2
        v = _next_line(r"3\.3\.3\.4\.?\s*\n?\s*Maximum\s*30\s*minutes\s*power")
        if v:
            mn = re.search(r"\d+", v)
            if mn:
                data["puissance_nette_p2"] = mn.group(0)
                data["puissance_kw"] = int(mn.group(0))

        # 6.16.1 Number of seating positions → S.1
        v = _next_line(r"6\.16\.1\.?\s*\n?\s*Number\s*of\s*seating\s*positions")
        if v:
            mn = re.search(r"\d+", v)
            if mn:
                data["places_assises"] = int(mn.group(0))
                data["places_s1"] = mn.group(0)

        # 4.0.1 Environmental step → V.9 classe environnementale
        v = _next_line(r"4\.0\.1\.?\s*\n?\s*Environmental\s*step")
        if v and len(v) <= 30:
            data["classe_env"] = v.strip()

        # Q : rapport puissance/masse (moto uniquement, kW/kg) — calculé
        if data.get("puissance_kw") and data.get("masse_g"):
            try:
                ratio = float(data["puissance_kw"]) / float(data["masse_g"])
                data["rapport_puiss_masse"] = f"{ratio:.3f}".rstrip("0").rstrip(".")
            except (ValueError, ZeroDivisionError):
                pass
        # Energie (FR: Carburant/Energie, EN: Electric/Fuel, ou "pure electric")
        m = re.search(r"(?:[Cc]arburant|[Ee]nergie|[Ff]uel|[Ee]lectric\s*vehicle\s*configuration)\s*[:\s]*([A-Za-z\s]{2,30})", text)
        if m:
            data["energie"] = m.group(1).strip()
        # Detection directe "pure electric" ou "electric" dans le texte
        if re.search(r"pure\s*electric|electric\s*motor|electric\s*vehicle", text, re.IGNORECASE):
            data["energie"] = data.get("energie", "electrique")
            if "electric" in data["energie"].lower() or "electr" in data["energie"].lower():
                data["energie"] = "electrique"
        m = re.search(r"(?:P\.?6|[Pp]uissance\s*administrative)\s*[:\s]*(\d+)\s*CV", text)
        if m: data["puissance_cv"] = int(m.group(1))
        m = re.search(r"(?:CO2\s*WLTP|V\.?7)\s*[:\s]*(\d+)", text)
        if m: data["co2_wltp"] = int(m.group(1))
        m = re.search(r"(?:CNIT|D\.?2\.?1)\s*[:\s]*([A-Z0-9]{5,12})", text)
        if m: data["cnit"] = m.group(1)
        m = re.search(r"(?:PTAC|[Mm]asse\s*en\s*charge\s*maximale|F\.?2)\s*[:\s]*(\d+)\s*kg", text, re.IGNORECASE)
        if m: data["ptac_kg"] = int(m.group(1))
        m = re.search(r"(?:S\.?1|[Pp]laces\s*assises)\s*[:\s]*(\d+)", text)
        if m: data["places"] = int(m.group(1))
        # Champs supplementaires COC
        m = re.search(r"(?:D\.?2\s*)?[Tt]ype\s*[Vv]ariante\s*[Vv]ersion\s*[:\s]*([A-Z0-9][A-Za-z0-9 ]{2,30})", text)
        if m: data["type_variante_version"] = m.group(1).strip()
        # Nom du constructeur (= "Je soussigné" du Cerfa 13749).
        # Sur un COC européen standard, le constructeur figure dans :
        #   0.4. Company name and address of manufacturer / Nom et adresse du constructeur
        #   3.1.2.1. Manufacturer / Constructeur (backup)
        # Le champ "The undersigned (Anton Wass)" en haut est la PERSONNE qui signe,
        # pas le constructeur — on ne l'utilise PAS.
        constructeur_patterns = [
            r"0\.4\.?\s*(?:Company\s+name\s+and\s+address\s+of\s+manufacturer|Nom\s+et\s+adresse\s+du\s+constructeur)\s*[:\s]*([A-Z][A-Za-zÀ-ÿ0-9&\.\,\- ]{2,80}?)(?:\n|\s{2,}|Carrer|Calle|Rue|Strasse|Via|Avenue|Avenida|Bahnhofstr)",
            r"3\.1\.2\.1\.?\s*(?:Manufacturer|Constructeur)\s*[:\s]*([A-Z][A-Za-zÀ-ÿ0-9&\.\,\- ]{2,80}?)(?:\n|\s{2,})",
        ]
        for pat in constructeur_patterns:
            m = re.search(pat, text)
            if m:
                # Strip trailing comma/space mais préserve les "." des acronymes (S.L., S.A.)
                data["soussigne"] = m.group(1).strip().rstrip(", ")
                break
        # Date de réception par type — FR ("réception le 15/06/2025")
        # ou EN ("granted on 30.10.2025"). Normalisation en JJ/MM/AAAA.
        m = re.search(r"[Rr]eception\s*(?:par\s*type)?\s*(?:le)?\s*[:\s]*(\d{2}/\d{2}/\d{4})", text)
        if m:
            data["date_reception"] = m.group(1)
        else:
            m = re.search(r"granted\s+on\s+(\d{1,2})[./\-](\d{1,2})[./\-](\d{4})", text, re.IGNORECASE)
            if m:
                data["date_reception"] = f"{m.group(1).zfill(2)}/{m.group(2).zfill(2)}/{m.group(3)}"

        # Numéro de réception européen "K" — format eN*directive/année*base*extension
        # Présent sur tous les COC européens. Exemples :
        #   e2*2007/46*0001*15  (voiture FR)
        #   e9*168/2013*16436*02  (moto STARK)
        # On match directement le format, sans dépendre du libellé qui varie selon les pays.
        m = re.search(r"\b(e\d{1,2}\*\d{2,4}/\d{2,4}\*\d{3,6}\*\d{1,4})\b", text)
        if m:
            data["numero_k"] = m.group(1)
        m = re.search(r"(?:J\.?1|[Gg]enre\s*national)\s*[:\s]*([A-Z]{2,10})", text)
        if m: data["genre_national"] = m.group(1).strip()
        m = re.search(r"[Dd]enomination\s*commerciale\s*[:\s]*(.{2,50})", text)
        if m: data["denomination"] = m.group(1).strip()
        m = re.search(r"(?:V\.?9|[Cc]lasse\s*environnementale)\s*[:\s]*(EURO\s*\w+)", text)
        if m: data["classe_env"] = m.group(1).strip()
        m = re.search(r"(?:F\.?1|[Mm]asse\s*(?:en\s*charge)?\s*max\w*\s*tech\w*\s*admiss\w*)\s*[:\s]*(\d+)\s*kg", text, re.IGNORECASE)
        if m: data["masse_f1"] = m.group(1)
        m = re.search(r"(?:G\b|[Mm]asse\s*en\s*service)\s*[:\s]*(\d+)\s*kg", text, re.IGNORECASE)
        if m: data["masse_g"] = m.group(1)
        m = re.search(r"(?:P\.?1|[Cc]ylindree)\s*[:\s]*(\d+)\s*cm", text, re.IGNORECASE)
        if m: data["cylindree_p1"] = m.group(1)
        # Puissance kW (FR: P.2/puissance nette, EN: Maximum 30 minutes power / max power)
        m = re.search(r"(?:P\.?2|[Pp]uissance\s*nette\s*maximale|[Mm]aximum\s*(?:30\s*minutes\s*)?power)\s*[:\s\[]*(?:kW.*?)?(\d+(?:\.\d+)?)", text, re.IGNORECASE)
        if m: data["puissance_nette_p2"] = m.group(1)
        # Fallback : chercher "XX kW" isolé
        if not data.get("puissance_nette_p2"):
            m = re.search(r"\b(\d+(?:\.\d+)?)\s*kW\b", text)
            if m: data["puissance_nette_p2"] = m.group(1)
        # Detection conversion possible A2/A3 (vehicule debridable)
        if re.search(r"converting.*(?:A2|A3)|conversion.*(?:A2|A3)", text, re.IGNORECASE):
            data["debridable"] = True
            data["debridable_vers"] = []
            if re.search(r"A2", text): data["debridable_vers"].append("A2")
            if re.search(r"A3", text): data["debridable_vers"].append("A3")
        # Champs supplementaires pour Cerfa complet
        m = re.search(r"(?:F\.?3|[Mm]asse\s*(?:en\s*charge)?\s*maxi?\s*(?:de\s*l)?\s*ensemble)\s*[:\s]*(\d+)\s*kg", text, re.IGNORECASE)
        if m: data["masse_f3"] = m.group(1)
        m = re.search(r"(?:G\.?1|[Pp]oids\s*a\s*vide\s*national)\s*[:\s]*(\d+)\s*kg", text, re.IGNORECASE)
        if m: data["poids_vide_g1"] = m.group(1)
        # Categorie vehicule (FR: J/categorie, EN: Vehicle category, champ 0.3)
        # Format : L3e-A1E, M1, N1, L1e, etc.
        m = re.search(r"(?:0\.3\.?\s*)?(?:[Vv]ehicle\s*categor|[Cc]ategorie\s*(?:du\s*)?vehicule|J\b)\s*[:\s]*(L\d[A-Za-z0-9\-]*|M\d|N\d)", text)
        if m: data["categorie_j"] = m.group(1).upper()
        # Fallback : chercher L3e, L1e, etc. dans le texte
        if not data.get("categorie_j"):
            m = re.search(r"\b(L[1-7]e(?:-[A-Z0-9]+)?)\b", text)
            if m: data["categorie_j"] = m.group(1).upper()
        m = re.search(r"(?:J\.?2|[Cc]arrosserie\s*CE)\s*[:\s]*([A-Z]{2})", text)
        if m: data["carrosserie_j2"] = m.group(1)
        m = re.search(r"(?:J\.?3|[Cc]arrosserie\s*nationale)\s*[:\s]*([A-Z]{2,15})", text)
        if m: data["carrosserie_j3"] = m.group(1)
        m = re.search(r"(?:U\.?1|[Nn]iveau\s*sonore)\s*[:\s]*(\d+)\s*dB", text, re.IGNORECASE)
        if m: data["niveau_sonore_u1"] = m.group(1)
        m = re.search(r"(?:U\.?2|[Vv]itesse\s*du\s*moteur)\s*[:\s]*(\d+)\s*min", text, re.IGNORECASE)
        if m: data["vitesse_moteur_u2"] = m.group(1)
        m = re.search(r"(?:S\.?2|[Pp]laces\s*debout)\s*[:\s]*(\d+)", text)
        if m: data["places_debout_s2"] = m.group(1)

    elif doc_type == "CERTIFICAT_CESSION":
        # Ancien proprietaire (vendeur)
        m = re.search(r"[Aa]ncien\s*propri[eé]taire\s*[:\s]*\n?\s*([A-Z][A-Za-zÀ-ÿ\- ]{2,50})", text)
        if m: data["vendeur_nom"] = m.group(1).strip()
        # Nouveau proprietaire (acquereur)
        m = re.search(r"[Nn]ouveau\s*propri[eé]taire\s*[:\s]*\n?\s*([A-Z][A-Za-zÀ-ÿ\- ]{2,50})", text)
        if m: data["acquereur_nom"] = m.group(1).strip()
        # Date et heure de cession
        m = re.search(r"[Dd]ate\s*(?:et\s*heure)?\s*(?:de\s*(?:la\s*)?)?cession\s*[:\s]*(\d{2}[./]\d{2}[./]\d{2,4})", text)
        if m: data["date_cession"] = m.group(1)
        # Fallback date
        if not data.get("date_cession"):
            m = re.search(r"[Cc][eé]d[eé]\s*le\s*[:\s]*(\d{2}[./]\d{2}[./]\d{2,4})", text)
            if m: data["date_cession"] = m.group(1)
        # Immatriculation
        m = re.search(r"[Ii]mmatriculation\s*[:\s]*([A-Z]{2}[\-\s]?\d{3}[\-\s]?[A-Z]{2})", text)
        if m: data["immatriculation"] = m.group(1).strip()
        # VIN
        m = re.search(r"(?:VIN|[Nn]um[eé]ro\s*(?:d.)?identification)\s*[:\s]*([A-HJ-NPR-Z0-9]{17})", text)
        if m: data["vin"] = m.group(1)
        # Signatures presentes (detection visuelle)
        data["signature_vendeur_presente"] = bool(
            re.search(r"[Ss]ignature\s*(?:du\s*)?vendeur", text)
        )
        data["signature_acquereur_presente"] = bool(
            re.search(r"[Ss]ignature\s*(?:de\s*l.)?\s*acqu[eé]reur", text)
        )
        # Numero de formule (si present)
        m = re.search(r"[Ff]ormule\s*[:\s]*(\d{10,})", text)
        if m: data["numero_formule"] = m.group(1)

    elif doc_type == "FACTURE":
        m = re.search(r"[Aa]cheteur|[Cc]lient\s*[:\s]*([A-Za-zÀ-ÿ\-\s]{2,60})", text)
        if m: data["acheteur"] = m.group(1).strip()
        m = re.search(r"SIRET\s*[:\s]*([\d\s]{14,18})", text)
        if m: data["siret_vendeur"] = re.sub(r"\s", "", m.group(1))
        # Couleur
        m = re.search(r"[Cc]ouleur\s*[:\s]*([A-Za-zÀ-ÿ ]{2,20})", text)
        if m: data["couleur"] = m.group(1).strip().lower()
        m = re.search(r"[Tt]otal\s*TTC\s*[:\s]*([\d\s.,]+)\s*EUR", text)
        if m: data["prix_ttc"] = m.group(1).strip()
        m = re.search(r"[Mm]arque\s*[:\s]*([A-Za-zÀ-ÿ\-\s]{2,30})", text)
        if m: data["marque"] = m.group(1).strip()
        # Vendeur (premiere ligne du doc = nom du garage)
        first_line = text.strip().split("\n")[0].strip()
        if first_line and len(first_line) > 3 and first_line[0].isupper():
            data["nom_vendeur"] = first_line
        # Date de facture/vente
        m = re.search(r"[Dd]ate\s*(?:de\s*)?(?:facture|vente)\s*[:\s]*(\d{2}/\d{2}/\d{4})", text)
        if m: data["date_vente"] = m.group(1)

    elif doc_type == "ASSURANCE":
        # Extraction attestation d'assurance auto
        # On verifie que c'est bien une assurance auto + nom de l'assure
        m = re.search(r"(?:[Nn]om|[Ss]ouscripteur|[Aa]ssur[eé])\s*[:\s]*([A-Za-zÀ-ÿ\- ]{2,50})", text)
        if m: data["nom_assure"] = m.group(1).strip()
        m = re.search(r"(?:[Cc]ompagnie|[Aa]ssureur)\s*[:\s]*([A-Za-zÀ-ÿ\- ]{2,50})", text)
        if m: data["compagnie"] = m.group(1).strip()
        # Dates de validite
        m = re.search(r"(?:[Dd]ate\s*d.effet|[Dd]ebut)\s*[:\s]*(\d{2}[./]\d{2}[./]\d{2,4})", text)
        if m: data["date_effet"] = m.group(1)
        m = re.search(r"(?:[Ee]ch[eé]ance|[Ee]xpir|[Ff]in)\s*[:\s]*(\d{2}[./]\d{2}[./]\d{2,4})", text)
        if m: data["date_echeance"] = m.group(1)
        # Verification que c'est bien une assurance automobile
        data["est_assurance_auto"] = bool(
            re.search(r"auto|vehicule|carte verte|responsabilit[eé] civile|RC", text, re.IGNORECASE)
        )

    elif doc_type == "DOMICILE":
        m = re.search(r"(?:[Nn]om|[Tt]itulaire|[Dd]estinataire)\s*[:\s]*([A-Za-zÀ-ÿ\- ]{2,60})", text)
        if m: data["nom_titulaire"] = m.group(1).strip()
        m = re.search(r"(\d{5})\s+([A-Z][A-Za-zÀ-ÿ\-]{1,30})", text)
        if m:
            data["code_postal"] = m.group(1)
            data["ville"] = m.group(2).strip()
        m = re.search(r"(\d+\s*(?:rue|avenue|boulevard|bd|impasse|chemin|place|allee)\s+[A-Za-zÀ-ÿ\- ]{2,50})", text, re.IGNORECASE)
        if m: data["adresse"] = m.group(1).strip().rstrip()

    elif doc_type == "CG_BARREE":
        # Titulaire C.1
        m = re.search(r"C\.?1\s+([A-Z][A-Z\- ]{1,30})", text)
        if m: data["titulaire"] = m.group(1).strip()
        # Prenom (ligne apres C.1)
        if data.get("titulaire"):
            m = re.search(r"C\.?1\s+" + re.escape(data["titulaire"]) + r"\s*\n\s*([A-Z][A-Za-zÀ-ÿ\- ]{1,30})", text)
            if m: data["titulaire_prenom"] = m.group(1).strip()
        # Vendu le (si CG barree)
        m = re.search(r"[Vv]endu\s*le\s*[:\s]*(\d{2}[./]\d{2}[./]\d{4})", text)
        if m: data["date_vente"] = m.group(1)
        data["barre_diagonale"] = bool(re.search(r"barr[eé]|diagonale|vendu le", text, re.IGNORECASE))
        # Couleur (case R de la CG française) — laissée vide si ambigu, le SIV
        # met "INDÉTERMINÉE" par défaut. Cf. décision produit : pas de mapping
        # marketing étendu, on ne reconnaît que les 10 couleurs standard.
        m = re.search(r"\bR\s*[:\s]+([A-Za-zÀ-ÿ ]{2,30})", text)
        if not m:
            m = re.search(r"[Cc]ouleur\s*[:\s]*([A-Za-zÀ-ÿ ]{2,30})", text)
        if m:
            data["couleur"] = m.group(1).strip().lower()

        # Nom de l'acheteur inscrit sur la barre horizontale
        # Formats courants : "vendu le JJ/MM/AAAA à NOM PRENOM"
        #                    "cédé à NOM PRENOM le JJ/MM/AAAA"
        #                    "NOM PRENOM" sur la ligne de barre
        m = re.search(
            r"(?:[Vv]endu|[Cc][eé]d[eé])\s*(?:le\s*\d{2}[./]\d{2}[./]\d{2,4})?\s*"
            r"(?:[aà]|au\s*profit\s*de)\s+([A-Z][A-Za-zÀ-ÿ\- ]{2,50})",
            text
        )
        if m:
            acheteur_barre = m.group(1).strip()
            # Separer nom et prenom (le nom est generalement en premier, en majuscules)
            parts = acheteur_barre.split()
            nom_parts = []
            prenom_parts = []
            for p in parts:
                if p == p.upper() and len(p) > 1:
                    nom_parts.append(p)
                else:
                    prenom_parts.append(p)
            data["acheteur_nom_barre"] = " ".join(nom_parts) if nom_parts else acheteur_barre
            data["acheteur_prenom_barre"] = " ".join(prenom_parts) if prenom_parts else None
            data["acheteur_barre_complet"] = acheteur_barre
        # A. Immatriculation
        m = re.search(r"A\.?\s*([A-Z]{2}[\-\s]?\d{3}[\-\s]?[A-Z]{2})", text)
        if m: data["immatriculation"] = m.group(1).strip()
        # B. Date 1ere immatriculation
        m = re.search(r"B\.?\s*(\d{2}/\d{2}/\d{4})", text)
        if m: data["date_premiere_immat"] = m.group(1)
        # C.3 Adresse
        m = re.search(r"C\.?3\s*\n\s*(.+)\n\s*(\d{5})\s+([A-Z][A-Za-zÀ-ÿ\- ]+)", text)
        if m:
            data["adresse"] = m.group(1).strip()
            data["code_postal"] = m.group(2)
            data["ville"] = m.group(3).strip()
        # D.1 Marque
        m = re.search(r"D\.?1\s+([A-Z][A-Z\- ]{1,20})", text)
        if m: data["marque"] = m.group(1).strip()
        # D.2 Type Variante Version
        m = re.search(r"D\.?2\s+([A-Z0-9][A-Z0-9 ]{1,20})", text)
        if m: data["type_variante_version"] = m.group(1).strip()
        # D.2.1 CNIT
        m = re.search(r"D\.?2\.?1\s+([A-Z0-9]{5,20})", text)
        if m: data["cnit"] = m.group(1).strip()
        # D.3 Denomination
        m = re.search(r"D\.?3\s+([A-Za-z0-9 \-]{2,40})", text)
        if m: data["denomination"] = m.group(1).strip()
        # E. VIN
        m = re.search(r"E\.?\s*([A-HJ-NPR-Z0-9]{17})", text)
        if m: data["vin"] = m.group(1)
        # F.1 Masse tech admissible
        m = re.search(r"F\.?1\s*\n?\s*(\d{2,5})", text)
        if m: data["masse_f1"] = m.group(1)
        # F.2 PTAC
        m = re.search(r"F\.?2\s+(\d{2,5})", text)
        if m: data["ptac_kg"] = m.group(1)
        # G Masse en service
        m = re.search(r"\bG\b\s*\n?\s*(\d{2,5})", text)
        if m: data["masse_g"] = m.group(1)
        # G.1 Poids a vide
        m = re.search(r"G\.?1\s+(\d{2,5})", text)
        if m: data["poids_vide_g1"] = m.group(1)
        # J Categorie (ex: L3e-A1E, M1, N1)
        m = re.search(r"\bJ\b\s*\n?\s*(L\d[A-Za-z0-9\-]*|M\d|N\d)", text)
        if m: data["categorie_j"] = m.group(1)
        # J.1 Genre national
        m = re.search(r"J\.?1\s+([A-Z]{2,5})", text)
        if m: data["genre_national"] = m.group(1).strip()
        # J.3 Carrosserie
        m = re.search(r"J\.?3\s+([A-Z]{2,15})", text)
        if m: data["carrosserie_j3"] = m.group(1).strip()
        # K Homologation
        m = re.search(r"K\s*\n?\s*(e\d\*[\d/\*\w]+)", text)
        if m: data["numero_k"] = m.group(1)
        # P.1 Cylindree
        m = re.search(r"P\.?1\s*\n?\s*(\d+)", text)
        if m and int(m.group(1)) > 0: data["cylindree_p1"] = m.group(1)
        # P.2 Puissance nette kW
        m = re.search(r"P\.?2\s+(\d+)", text)
        if m: data["puissance_nette_p2"] = m.group(1)
        # P.3 Energie
        m = re.search(r"P\.?3\s+([A-Z]{2,10})", text)
        if m: data["energie"] = m.group(1).strip()
        # P.6 Puissance administrative CV
        m = re.search(r"P\.?6\s+(\d+)", text)
        if m: data["puissance_cv"] = int(m.group(1))
        # S.1 Places
        m = re.search(r"S\.?1\s+(\d+)", text)
        if m: data["places"] = int(m.group(1))
        # Numero formule
        m = re.search(r"(\d{4}[A-Z]{2}\d{5})", text)
        if m: data["numero_formule"] = m.group(1)
        # Date certificat (I)
        m = re.search(r"I\s+(\d{2}/\d{2}/\d{4})", text)
        if m: data["date_certificat"] = m.group(1)

    elif doc_type == "KBIS":
        m = re.search(r"(?:SIREN|RCS)\s*[:\s]*(\d{9})", text)
        if m: data["siren"] = m.group(1)
        m = re.search(r"SIRET\s*[:\s]*(\d{14})", text)
        if m: data["siret"] = m.group(1)
        m = re.search(r"(?:[Rr]aison\s*sociale|[Dd]enomination)\s*[:\s]*(.{2,80})", text)
        if m: data["raison_sociale"] = m.group(1).strip()
        m = re.search(r"(?:[Gg]erant|[Pp]resident|[Dd]irigeant|[Rr]epresentant)\s*[:\s]*([A-Za-zÀ-ÿ\- ]{2,60})", text)
        if m: data["representant"] = m.group(1).strip()

    return data


# ─── Diagnostic v2 - base sur ce qui est fourni ──────────────────────────────


# ─── Diagnostic v2 - base sur ce qui est fourni ──────────────────────────────

def run_diagnostic(dossier: dict) -> dict:
    """
    Diagnostic v2.

    VN : CNI + domicile + COC + facture + permis
    VO : CNI + domicile + CG barree + permis

    Croisements :
    - VIN coherent entre docs
    - Nom coherent CNI ↔ domicile
    - CNI non expiree
    - CG barree correctement (VO)

    Resultat → VERT si tout ok (Cerfa generable), ROUGE si blocage.
    """
    docs = dossier["documents"]
    flow = dossier["type"]  # VN ou VO
    blocages: list[dict] = []
    warnings: list[dict] = []
    infos: list[dict] = []

    # Index par type
    by_type: dict[str, list[dict]] = {}
    for d in docs:
        by_type.setdefault(d["type"], []).append(d)

    is_pm = dossier.get("is_personne_morale", False)
    # Detection auto personne morale si Kbis present
    if "KBIS" in by_type:
        is_pm = True
        dossier["is_personne_morale"] = True

    # ─── 1. Pieces presentes / manquantes ─────────────────────────────────
    required_common = {
        "CNI": "Piece d'identite (CNI ou passeport)",
        "DOMICILE": "Justificatif de domicile",
    }
    required_vn = {"COC": "Certificat de conformite (COC)", "FACTURE": "Facture vehicule neuf"}
    required_vo = {"CG_BARREE": "Carte grise barree"}  # CG fournie par le CLIENT
    # Pas d'assurance dans les pieces a deposer
    # Le Cerfa est le LIVRABLE du systeme, pas une piece a fournir

    required = {**required_common}
    if flow == "VN":
        required.update(required_vn)
    else:
        required.update(required_vo)

    # Personne morale : Kbis obligatoire, permis non requis
    if is_pm:
        required["KBIS"] = "Kbis (personne morale - obligatoire)"
        required.pop("PERMIS", None)  # Pas de permis pour PM
    else:
        required["PERMIS"] = "Permis de conduire"

    # CNI ou PASSEPORT comptent pour "CNI"
    types_present = set(by_type.keys())
    if "PASSEPORT" in types_present:
        types_present.add("CNI")

    for code, label in required.items():
        if code in types_present:
            infos.append({"code": f"{code}_OK", "message": f"{label} - present"})
        else:
            blocages.append({"code": f"{code}_MANQUANT", "message": f"{label} - manquant", "correction": f"Uploader le document : {label}"})

    # ─── 2. Coherence VIN ─────────────────────────────────────────────────
    vins_found: dict[str, str] = {}
    if dossier.get("vin"):
        vins_found["SAISIE_PRO"] = dossier["vin"]

    for d in docs:
        ext = d.get("extracted_data", {})
        if ext.get("vin"):
            vins_found[d["type"]] = ext["vin"]

    unique_vins = set(vins_found.values())
    if len(unique_vins) > 1:
        detail = ", ".join(f"{src}={vin}" for src, vin in vins_found.items())
        blocages.append({
            "code": "VIN_INCOHERENT",
            "message": f"VIN different entre les documents : {detail}",
            "correction": "Verifier que tous les documents concernent le meme vehicule",
        })
    elif len(unique_vins) == 1:
        vin = list(unique_vins)[0]
        if len(vin) != 17:
            blocages.append({"code": "VIN_FORMAT", "message": f"VIN invalide ({len(vin)} car. au lieu de 17)", "correction": "Verifier le VIN"})
        elif set(vin) & set("IOQ"):
            blocages.append({"code": "VIN_CHARS", "message": "VIN contient I, O ou Q (interdit)", "correction": "Confusion O/0 ou I/1 probable"})
        else:
            infos.append({"code": "VIN_OK", "message": f"VIN coherent sur {len(vins_found)} source(s) : {vin}"})

    # ─── 3. Coherence nom CNI ↔ domicile ──────────────────────────────────
    nom_cni = None
    nom_domicile = None

    for d in by_type.get("CNI", []) + by_type.get("PASSEPORT", []):
        ext = d.get("extracted_data", {})
        if ext.get("nom"):
            nom_cni = ext["nom"].upper().strip()

    for d in by_type.get("DOMICILE", []):
        ext = d.get("extracted_data", {})
        if ext.get("nom_titulaire"):
            nom_domicile = ext["nom_titulaire"].upper().strip()

    if nom_cni and nom_domicile:
        # Comparaison simple : le nom CNI doit etre contenu dans le nom domicile ou vice versa
        if nom_cni in nom_domicile or nom_domicile in nom_cni or nom_cni == nom_domicile:
            infos.append({"code": "NOM_COHERENT", "message": f"Nom coherent : CNI ({nom_cni}) ↔ domicile ({nom_domicile})"})
        else:
            # Cas hebergement : le client n'habite pas a son nom
            # Verifier si attestation d'hebergement + CNI hebergeant sont deposes
            has_attestation_hebergement = any(
                d.get("type", "").upper() == "ATTESTATION_HEBERGEMENT"
                for d in docs
            )
            has_cni_hebergeant = any(
                d.get("type", "").upper() == "CNI_HEBERGEANT"
                for d in docs
            )
            if has_attestation_hebergement and has_cni_hebergeant:
                infos.append({
                    "code": "HEBERGEMENT_VALIDE",
                    "message": f"Hebergement : {nom_cni} heberge chez {nom_domicile} — attestation fournie",
                })
            else:
                # Stocker la divergence pour que _get_client_docs_attendus puisse
                # ajouter les docs d'hebergement a la checklist
                warnings.append({
                    "code": "NOM_DIVERGENT_HEBERGEMENT",
                    "message": (
                        f"Le nom sur la piece d'identite ({nom_cni}) ne correspond pas "
                        f"au nom sur le justificatif de domicile ({nom_domicile}). "
                        f"Si vous etes heberge(e), deposez une attestation d'hebergement "
                        f"et la piece d'identite de votre hebergeant."
                    ),
                    "requires_hebergement": True,
                })

    # ─── 4. CNI non expiree ───────────────────────────────────────────────
    for d in by_type.get("CNI", []) + by_type.get("PASSEPORT", []):
        ext = d.get("extracted_data", {})
        if ext.get("date_expiration"):
            try:
                parts = ext["date_expiration"].replace("/", ".").split(".")
                exp = date(int(parts[2]), int(parts[1]), int(parts[0]))
                if exp < date.today():
                    days_expired = (date.today() - exp).days
                    if days_expired > 5 * 365:
                        blocages.append({"code": "CNI_EXPIREE", "message": f"CNI expiree depuis {days_expired} jours (> 5 ans)", "correction": "Fournir une piece d'identite valide"})
                    else:
                        warnings.append({"code": "CNI_EXPIREE_RECENTE", "message": f"CNI expiree depuis {days_expired} jours (regle +5 ans 2004-2013 possible)"})
                else:
                    infos.append({"code": "CNI_VALIDE", "message": f"CNI valide jusqu'au {ext['date_expiration']}"})
            except (ValueError, IndexError):
                warnings.append({"code": "CNI_DATE_ILLISIBLE", "message": "Date d'expiration CNI non lisible"})

    # ─── 4 bis. Lisibilité OCR du nom/prénom (CNI / Passeport) ────────────
    # Si l'OCR n'a pas pu lire correctement le nom ou le prénom, on émet un
    # warning (non bloquant) pour informer l'agent — le Cerfa reste générable.
    # L'agent peut ensuite saisir manuellement les valeurs avant soumission SIV.
    def _looks_illegible(value: str) -> bool:
        if not value:
            return True
        v = value.strip()
        if len(v) < 2:
            return True
        # Beaucoup de chiffres ou caractères spéciaux dans un nom => OCR raté
        bad_chars = sum(1 for c in v if not (c.isalpha() or c in " -'À-ÿ"))
        if bad_chars / max(len(v), 1) > 0.3:
            return True
        return False

    for d in by_type.get("CNI", []) + by_type.get("PASSEPORT", []):
        ext = d.get("extracted_data", {})
        nom_brut = ext.get("nom_naissance", "") or ""
        prenoms_brut = ext.get("prenoms", "") or ""
        if _looks_illegible(nom_brut):
            warnings.append({
                "code": "NOM_OCR_ILLISIBLE",
                "message": (
                    "Le nom n'a pas pu être lu correctement par l'OCR sur la pièce d'identité. "
                    "Vérifiez et corrigez manuellement avant soumission SIV."
                ),
            })
        if _looks_illegible(prenoms_brut):
            warnings.append({
                "code": "PRENOM_OCR_ILLISIBLE",
                "message": (
                    "Le prénom n'a pas pu être lu correctement par l'OCR sur la pièce d'identité. "
                    "Vérifiez et corrigez manuellement avant soumission SIV."
                ),
            })

    # ─── 5. CG barree (VO uniquement) ─────────────────────────────────────
    if flow == "VO":
        for d in by_type.get("CG_BARREE", []):
            ext = d.get("extracted_data", {})
            # 5a. Barre diagonale — warning au lieu de blocage : on extrait
            # quand même les données du véhicule, l'agent peut continuer mais
            # devra obtenir la CG barrée avant soumission SIV.
            if ext.get("barre_diagonale"):
                infos.append({"code": "CG_BARREE_OK", "message": "CG barree en diagonale - OK"})
            else:
                warnings.append({
                    "code": "CG_NON_BARREE_WARNING",
                    "message": (
                        "La carte grise n'est pas encore barree. Vous pouvez generer "
                        "le Cerfa, mais avant la soumission au SIV, le vendeur doit "
                        "tracer une barre diagonale, inscrire \"vendu le\" suivi de la "
                        "date et l'heure de la vente, le nom et prenom de l'acheteur, "
                        "puis signer."
                    ),
                })
            # 5b. Date de vente sur la barre
            if ext.get("date_vente"):
                infos.append({"code": "CG_DATE_VENTE", "message": f"Date de vente sur CG : {ext['date_vente']}"})
            elif ext.get("barre_diagonale"):
                blocages.append({
                    "code": "CG_DATE_VENTE_MANQUANTE",
                    "message": "Date de vente absente sur la carte grise barree",
                    "correction": "Inscrivez la date de la vente sur la barre (format : JJ/MM/AAAA).",
                })
            # 5c. Nom de l'acheteur manuscrit (personne physique ou morale)
            is_pm = dossier.get("is_personne_morale", False)
            if ext.get("acheteur_nom_barre"):
                label = "Acheteur" if not is_pm else "Societe acquereuse"
                acheteur_txt = ext.get("acheteur_nom_barre", "")
                if ext.get("acheteur_prenom_barre") and not is_pm:
                    acheteur_txt += f" {ext['acheteur_prenom_barre']}"
                infos.append({
                    "code": "CG_ACHETEUR_BARRE_OK",
                    "message": f"{label} inscrit sur la barre : {acheteur_txt}",
                })
            elif ext.get("barre_diagonale"):
                if is_pm:
                    blocages.append({
                        "code": "CG_ACHETEUR_BARRE_MANQUANT",
                        "message": "Raison sociale de l'acquereur absente sur la carte grise barree",
                        "correction": "La raison sociale de la societe acquereuse doit etre inscrite a la main sur ou pres de la barre diagonale.",
                    })
                else:
                    blocages.append({
                        "code": "CG_ACHETEUR_BARRE_MANQUANT",
                        "message": "Nom et prenom de l'acheteur absents sur la carte grise barree",
                        "correction": "Le nom et prenom de l'acheteur doivent etre inscrits a la main sur ou pres de la barre diagonale.",
                    })

    # ─── 6. Donnees extraites du COC (VN) ─────────────────────────────────
    if flow == "VN":
        for d in by_type.get("COC", []):
            ext = d.get("extracted_data", {})
            if ext.get("marque"):
                infos.append({"code": "COC_MARQUE", "message": f"Marque : {ext['marque']}"})
            if ext.get("modele"):
                infos.append({"code": "COC_MODELE", "message": f"Modele : {ext['modele']}"})
            if ext.get("puissance_cv"):
                infos.append({"code": "COC_PUISSANCE", "message": f"Puissance : {ext['puissance_cv']} CV"})
            if ext.get("co2_wltp"):
                infos.append({"code": "COC_CO2", "message": f"CO2 WLTP : {ext['co2_wltp']} g/km"})

            # Warning : puissance administrative P.6 manquante.
            # Pour les motos électriques (et plus généralement les véhicules
            # dont le COC ne contient pas la puissance fiscale française),
            # l'agent doit la saisir à la main avant soumission SIV.
            cat = (ext.get("categorie_j") or "").upper()
            if not ext.get("puissance_cv"):
                if cat.startswith("L"):
                    msg_complement = (
                        " Pour les motos électriques considérées comme "
                        "équivalentes >125 cc, la valeur dépend de l'arrêté "
                        "ministériel de réception type — vérifiez auprès "
                        "de la base SIV ou du constructeur."
                    )
                else:
                    msg_complement = ""
                warnings.append({
                    "code": "P6_PUISSANCE_ADMIN_MANQUANTE",
                    "message": (
                        "La puissance administrative (P.6) n'a pas été "
                        "trouvée dans le COC. Saisissez-la manuellement "
                        "sur le Cerfa avant soumission SIV." + msg_complement
                    ),
                })

    # ─── 7. Estimation taxes (si COC disponible) ──────────────────────────
    tax_estimate = None
    coc_data = {}
    for d in by_type.get("COC", []):
        coc_data = d.get("extracted_data", {})

    domicile_cp = None
    for d in by_type.get("DOMICILE", []):
        domicile_cp = d.get("extracted_data", {}).get("code_postal")

    if coc_data.get("puissance_cv") or coc_data.get("co2_wltp"):
        tax_estimate = _estimate_taxes(
            puissance_cv=coc_data.get("puissance_cv"),
            co2_wltp=coc_data.get("co2_wltp"),
            ptac_kg=coc_data.get("ptac_kg"),
            code_postal=domicile_cp,
            energie=coc_data.get("energie"),
        )

    # ─── 8. Diagnostic final ──────────────────────────────────────────────
    # Tri-couleur :
    #   ROUGE  = au moins un blocage (Cerfa non générable, relance client requise)
    #   ORANGE = pas de blocage mais des warnings (Cerfa générable, agent doit
    #            vérifier manuellement les points signalés avant soumission SIV)
    #   VERT   = aucun blocage, aucun warning (Cerfa générable sereinement)
    if blocages:
        diagnostic = "ROUGE"
    elif warnings:
        diagnostic = "ORANGE"
    else:
        diagnostic = "VERT"

    return {
        "diagnostic": diagnostic,
        "blocages": blocages,
        "warnings": warnings,
        "infos": infos,
        "tax_estimate": tax_estimate,
        "documents_analyses": len(docs),
        "types_detectes": list(by_type.keys()),
        # Cerfa générable en VERT et ORANGE — bloqué uniquement en ROUGE
        "cerfa_disponible": diagnostic in ("VERT", "ORANGE"),
    }


# ─── Estimation taxes simplifiee ──────────────────────────────────────────────

TARIF_CV: dict[str, float] = {
    "75": 46.15, "77": 46.15, "78": 46.15, "91": 46.15, "92": 46.15,
    "93": 46.15, "94": 46.15, "95": 46.15, "69": 43.00, "13": 51.20,
    "06": 51.20, "33": 51.00, "31": 44.00, "59": 53.00, "67": 48.00,
    "68": 48.00, "44": 51.00, "34": 44.00, "35": 51.00, "76": 35.00,
    "14": 35.00, "62": 33.00, "57": 33.00, "54": 33.00,
}
DEFAULT_TARIF_CV = 43.00

MALUS_CO2 = [
    (118, 118, 50), (119, 120, 100), (121, 130, 170), (131, 140, 400),
    (141, 150, 1000), (151, 160, 3000), (161, 170, 5000), (171, 180, 8000),
    (181, 190, 12000), (191, 200, 18000), (201, 210, 25000), (211, 230, 40000),
    (231, 999, 60000),
]



def _estimate_taxes(puissance_cv=None, co2_wltp=None, ptac_kg=None,
                    code_postal=None, energie=None) -> dict:
    notes = []
    is_elec = energie and "electr" in energie.lower()

    # Y1
    dept = (code_postal or "")[:2]
    tarif = TARIF_CV.get(dept, DEFAULT_TARIF_CV)
    y1 = 0.0
    if puissance_cv and not is_elec:
        y1 = tarif * puissance_cv
        notes.append(f"Dept {dept} : {tarif} EUR/CV x {puissance_cv} CV")
    elif is_elec:
        notes.append("Vehicule electrique - exoneration taxe regionale")

    # Y3
    y3 = 0.0
    if co2_wltp and not is_elec:
        for smin, smax, montant in MALUS_CO2:
            if smin <= co2_wltp <= smax:
                y3 = montant
                break
        if co2_wltp < 118:
            notes.append(f"CO2 {co2_wltp} g/km - pas de malus")

    # Y4
    y4 = 0.0 if is_elec else 11.0

    # Y5
    y5 = 2.76

    # Y6
    y6 = 0.0
    if ptac_kg and ptac_kg > 1800 and not is_elec:
        y6 = (ptac_kg - 1800) * 10
        notes.append(f"PTAC {ptac_kg} kg - malus poids {y6} EUR")

    total = y1 + y3 + y4 + y5 + y6
    notes.append("Estimation INDICATIVE - montant final = SIV")

    return {
        "y1_taxe_regionale": round(y1, 2),
        "y3_malus_co2": round(y3, 2),
        "y4_taxe_gestion": round(y4, 2),
        "y5_redevance": round(y5, 2),
        "y6_malus_poids": round(y6, 2),
        "total": round(total, 2),
        "notes": notes,
    }


# ─── Schemas ──────────────────────────────────────────────────────────────────







# ─── Routes ───────────────────────────────────────────────────────────────────

def _build_recap_validation(dossier: dict) -> dict:
    """
    Construit le recapitulatif que le pro doit valider avant envoi du lien client.
    Synthese de toutes les infos extraites des documents.
    Le pro doit cocher pour confirmer et declencher l'envoi.
    """
    dossier_type = dossier.get("type", "?")
    is_vo = dossier_type == "VO"

    # Infos vehicule extraites
    vehicule = {
        "type_dossier": "Vehicule d'occasion (VO)" if is_vo else "Vehicule neuf (VN)",
        "vin": dossier.get("vin"),
        "immatriculation": dossier.get("immatriculation") if is_vo else None,
    }

    # Enrichir avec les donnees extraites des docs vendeur
    for d in dossier.get("documents_vendeur", []):
        ext = d.get("extracted_data", {})
        if not ext:
            continue
        dtype = d.get("type", "").upper()

        if dtype == "COC":
            vehicule["marque"] = ext.get("marque")
            vehicule["modele"] = ext.get("modele")
            vehicule["cnit"] = ext.get("cnit")
            vehicule["energie"] = ext.get("energie")
            vehicule["puissance_kw"] = ext.get("puissance_kw")
            vehicule["co2_wltp"] = ext.get("co2_wltp")
        elif dtype == "FACTURE":
            vehicule["prix_ttc"] = ext.get("prix_ttc")
            vehicule["date_vente"] = ext.get("date_vente")
            vehicule["vendeur_siret"] = ext.get("siret_vendeur")
        elif dtype == "CG_BARREE":
            vehicule["marque"] = vehicule.get("marque") or ext.get("marque")
            vehicule["genre_national"] = ext.get("genre_national")
            vehicule["date_mise_circulation"] = ext.get("date_mise_circulation")

    # Infos client extraites
    client = {
        "nom": dossier.get("client_nom"),
        "prenom": dossier.get("client_prenom"),
        "telephone": dossier.get("client_telephone"),
        "email": dossier.get("client_email"),
    }

    # Documents deposes
    docs_deposes = [
        {"type": d.get("type"), "filename": d.get("filename"), "status": d.get("quality", {}).get("status", "ok")}
        for d in dossier.get("documents_vendeur", [])
    ]

    return {
        "pret": True,
        "vehicule": vehicule,
        "client": client,
        "documents_deposes": docs_deposes,
        "message": (
            f"Dossier {dossier_type} detecte. "
            f"Verifiez les informations ci-dessous puis validez pour envoyer "
            f"le lien securise au {dossier.get('client_telephone', '?')}. "
            f"Votre client pourra y deposer ses documents d'identite "
            f"pour completer la demarche de generation du Cerfa."
        ),
        "action_requise": "Cochez pour confirmer et envoyer le lien au client",
        "envoi_lien_auto": False,
        "mentions_legales_pro": {
            "responsabilite_soumission": (
                "En tant que professionnel habilite SIV, vous restez seul responsable "
                "de la veracite et de la completude du dossier soumis a l'administration. "
                "Imatra est un outil d'aide a la constitution du dossier et ne se "
                "substitue pas a votre obligation de verification."
            ),
            "verification_ocr": (
                "Les donnees extraites automatiquement des documents (OCR via Google Document AI "
                "et IA via Claude/Anthropic) peuvent contenir des erreurs. Il vous appartient de "
                "verifier les informations avant toute soumission au SIV. Imatra ne peut etre "
                "tenu responsable des erreurs d'extraction."
            ),
            "sous_traitants": (
                "Le traitement des documents fait appel a Google Document AI (lecture optique) "
                "et Anthropic Claude (extraction des donnees). Ces services sont bases aux Etats-Unis "
                "et ne conservent pas les donnees au-dela du traitement. Transferts encadres par des "
                "clauses contractuelles types (CCT) conformes au RGPD."
            ),
            "estimation_taxes": (
                "Les estimations de taxes d'immatriculation sont fournies a titre indicatif. "
                "Le montant definitif est determine par le SIV au moment de la soumission."
            ),
            "conservation_donnees": (
                "Les documents et donnees du dossier sont conserves le temps de la demarche "
                "puis archives conformement a la reglementation en vigueur (5 ans). "
                "Voir notre politique de confidentialite."
            ),
            "limitation_responsabilite": (
                "Imatra ne garantit pas l'acceptation du dossier par le SIV. "
                "En cas de rejet, les honoraires factures ne sont pas remboursables "
                "si le rejet est du a des documents incorrects fournis par le vendeur ou le client."
            ),
        },
    }



def _deduce_sexe_from_prenom(prenom: str | None) -> str | None:
    """
    Deduit le sexe (M/F) a partir du prenom.
    Utilise une heuristique simple basee sur les terminaisons courantes
    des prenoms francais. En cas de doute, retourne None.
    """
    if not prenom:
        return None

    p = prenom.strip().split()[0].lower()  # Premier prenom uniquement

    # Terminaisons typiquement feminines
    feminine_endings = (
        "elle", "ette", "ine", "ise", "ane", "enne", "onne",
        "ia", "ie", "ee", "ée", "lle", "tte", "nne",
        "ina", "ita", "ola", "yla", "na", "da", "ra",
    )
    # Prenoms masculins qui finissent par des terminaisons ambigues
    masculine_exceptions = {
        "antoine", "maxime", "philippe", "pierre", "andre", "claude",
        "dominique", "camille", "stephane", "patrice", "serge",
        "frederic", "jerome", "herve", "rene", "michele",
        "noe", "moise", "elie", "jesse", "lee", "joe",
    }
    # Prenoms feminins courants qui ne matchent pas les terminaisons
    feminine_names = {
        "sarah", "margot", "manon", "marion", "maryam", "fatimah",
        "fleur", "esther", "judith", "ingrid", "agnes", "dolores",
    }
    # Prenoms epicenes (M ou F) → on ne peut pas deviner
    epicene = {"claude", "dominique", "camille", "eden", "charlie", "andrea", "morgan"}

    if p in epicene:
        return None
    if p in feminine_names:
        return "F"
    if p in masculine_exceptions:
        return "M"
    if any(p.endswith(e) for e in feminine_endings):
        return "F"

    # Par defaut on considere masculin (majorite des prenoms sans
    # terminaison feminine typique) — le systeme peut demander
    # confirmation au client si besoin
    return "M"



def _auto_detect_dossier_type(dossier: dict) -> None:
    """
    Déduit automatiquement VN ou VO à partir des documents déposés par le pro.

    Règle métier : la présence d'un COC est l'indicateur fort d'un véhicule
    NEUF. Pour une occasion, le SIV a déjà l'homologation en base et le COC
    n'est jamais redemandé. Donc :
      - COC présent → VN (même si une CG est aussi présente, ex: CG provisoire,
        moto qui vient d'être immatriculée par le concessionnaire, etc.)
      - CG_BARREE seule (sans COC) → VO
      - FACTURE seule → VN (le COC suivra)
    """
    doc_types = {d.get("type", "").upper() for d in dossier.get("documents_vendeur", [])}

    if "COC" in doc_types:
        dossier["type"] = "VN"
    elif "CG_BARREE" in doc_types:
        dossier["type"] = "VO"
    elif "FACTURE" in doc_types:
        dossier["type"] = "VN"
    # Sinon on ne change pas (reste None ou la valeur precedente)



def _auto_extract_dossier_fields(dossier: dict) -> None:
    """
    Extrait automatiquement VIN, immatriculation, nom/prenom client
    depuis les documents deposes par le pro.
    """
    for d in dossier.get("documents_vendeur", []):
        ext = d.get("extracted_data", {})
        if not ext:
            continue

        dtype = d.get("type", "").upper()

        # VIN
        if not dossier.get("vin") and ext.get("vin"):
            dossier["vin"] = ext["vin"]

        # Immatriculation (depuis CG barree)
        if not dossier.get("immatriculation") and ext.get("immatriculation"):
            dossier["immatriculation"] = ext["immatriculation"]

        # Nom/prenom client (= ACHETEUR) :
        # - VN : depuis la facture (case "Acheteur")
        # - VO : exclusivement depuis la CNI de l'acheteur (cf. _auto_extract_client_fields).
        #   On n'utilise NI le titulaire C.1 de la CG (= vendeur),
        #   NI la barre manuscrite (souvent illisible).
        if dtype == "FACTURE":
            if not dossier.get("client_nom") and ext.get("acheteur_nom"):
                dossier["client_nom"] = ext["acheteur_nom"]
            if not dossier.get("client_prenom") and ext.get("acheteur_prenom"):
                dossier["client_prenom"] = ext["acheteur_prenom"]



def _auto_extract_client_fields(dossier: dict) -> None:
    """
    Extrait automatiquement les infos du client depuis ses documents :
    - Sexe deduit du prenom (CNI)
    - Detection personne morale (si Kbis uploade)
    """
    # En version locale, tous les docs sont dans documents_vendeur.
    # On parcourt les deux listes pour rester compatible avec l'historique.
    for d in dossier.get("documents_client", []) + dossier.get("documents_vendeur", []):
        ext = d.get("extracted_data", {})
        if not ext:
            continue

        dtype = d.get("type", "").upper()

        # Sexe : prioritairement extrait directement de la CNI/passeport
        # (champ "Sexe : M/F"), sinon en dernier recours déduit du prénom.
        if dtype in ("CNI", "PASSEPORT") and not dossier.get("client_sexe"):
            sexe_extrait = (ext.get("sexe") or "").upper().strip()
            if sexe_extrait in ("M", "F"):
                dossier["client_sexe"] = sexe_extrait
            else:
                prenom = ext.get("prenoms") or ext.get("prenom")
                sexe = _deduce_sexe_from_prenom(prenom)
                if sexe:
                    dossier["client_sexe"] = sexe

            # Mettre a jour nom/prenom depuis la CNI (plus fiable que facture/CG)
            if ext.get("nom_naissance"):
                dossier["client_nom"] = ext["nom_naissance"]
            if prenom:
                dossier["client_prenom"] = prenom

        # Detection auto personne morale si Kbis uploade
        if dtype == "KBIS":
            dossier["is_personne_morale"] = True
            if ext.get("siren"):
                dossier["siren"] = ext["siren"]
            if ext.get("raison_sociale"):
                dossier["raison_sociale"] = ext["raison_sociale"]



def _check_pro_docs(dossier: dict) -> dict:
    """
    Checklist interactive complete cote vendeur.

    Le profil pro est toujours vert (renseigne au parametrage, requis avant
    de pouvoir creer un dossier). Il est affiche pour confirmation visuelle.

    Les elements bloquants sont : info client + documents vehicule.
    """

    # ─── 1. Profil pro (toujours vert — informatif) ───
    # Le pro ne peut pas acceder a cette page sans profil complet.
    # On affiche en vert pour confirmer visuellement que c'est pris en compte.
    profil_items = [
        {"id": "profil_nom_commerce", "label": "Nom du commerce", "status": "ok", "value": PROFIL_PRO.get("nom_commerce")},
        {"id": "profil_adresse", "label": "Adresse de la structure", "status": "ok", "value": PROFIL_PRO.get("adresse")},
        {"id": "profil_telephone", "label": "Telephone du commerce", "status": "ok", "value": PROFIL_PRO.get("telephone_commerce")},
        {"id": "profil_cachet", "label": "Cachet commercial", "status": "ok"},
        {"id": "profil_signature", "label": "Signature", "status": "ok"},
        {"id": "profil_kbis", "label": "Kbis du commerce", "status": "ok",
         "value": PROFIL_PRO.get("raison_sociale"), "siret": PROFIL_PRO.get("siret"),
         "warning": PROFIL_PRO.get("kbis_warning")},
    ]

    # ─── 2. Verification info client ───
    client_tel = dossier.get("client_telephone")
    info_items = []
    info_items.append({
        "id": "client_telephone",
        "label": "Portable du client",
        "status": "ok" if client_tel else "manquant",
        "value": client_tel,
        "action": None if client_tel else "Renseignez le numero de portable du client",
    })

    info_ok = all(item["status"] == "ok" for item in info_items)

    # ─── 3. Verification documents vehicule ───
    is_vo = (dossier.get("type") or "").upper() in ("VO", "OCCASION")
    type_detected = dossier.get("type") is not None

    if is_vo:
        # VO : CG barree obligatoire + certificat de cession (sauf si le pro coche "pas de cession")
        pas_de_cession = dossier.get("pas_de_certificat_cession", False)
        required = {"CG_BARREE": "Carte grise barree"}
        if not pas_de_cession:
            required["CERTIFICAT_CESSION"] = "Certificat de cession (Cerfa 15776) signe"
        optional = {"COC": "COC (recommande)"}
    elif type_detected:
        required = {"COC": "COC", "FACTURE": "Facture de vente"}
        optional = {}
    else:
        # Type pas encore detecte — on montre les deux listes
        required = {}
        optional = {}

    docs_vendeur = dossier.get("documents_vendeur", [])

    doc_items = []
    found_types = set()
    has_illisible = False

    for d in docs_vendeur:
        dtype = d.get("type", "PENDING").upper()
        found_types.add(dtype)
        status = d.get("status", "PENDING")
        quality = d.get("quality", {})

        if status == "REJECTED" or quality.get("status") == "illisible":
            doc_status = "illisible"
            has_illisible = True
            action = quality.get("message", "Re-deposez un scan plus net")
        elif status in ("EXTRACTED", "MERGED"):
            doc_status = "ok"
            action = None
        else:
            doc_status = "en_cours"
            action = None

        # Extraire l'info CNIT pour le COC
        extracted = d.get("extracted_data", {})
        has_cnit = bool(extracted.get("cnit")) if dtype == "COC" else None

        doc_items.append({
            "id": f"doc_{dtype.lower()}",
            "label": dtype,
            "filename": d.get("filename"),
            "source": d.get("source", "vendeur"),
            "status": doc_status,
            "quality": quality,
            "action": action,
            "has_cnit": has_cnit,
        })

    # Docs manquants
    missing_docs = []
    for dtype, label in required.items():
        if dtype not in found_types:
            missing_docs.append({
                "id": f"doc_{dtype.lower()}",
                "label": label,
                "status": "manquant",
                "required": True,
                "action": f"Deposez le document : {label}",
            })
    for dtype, label in optional.items():
        if dtype not in found_types:
            missing_docs.append({
                "id": f"doc_{dtype.lower()}",
                "label": label,
                "status": "manquant",
                "required": False,
                "action": f"Recommande : deposez le {label}",
            })

    docs_ok = (
        type_detected
        and not has_illisible
        and all(
            any(d["label"] == req and d["status"] == "ok" for d in doc_items)
            for req in required
        )
        and not any(m["required"] for m in missing_docs)
    )

    # ─── Synthese ───
    # Le profil est toujours ok (requis au parametrage).
    # Seuls info client + docs peuvent bloquer.
    all_ok = info_ok and docs_ok

    return {
        "profil": {"items": profil_items, "ok": True},
        "info_client": {"items": info_items, "ok": info_ok},
        "documents": {
            "type_detecte": dossier.get("type"),
            "items": doc_items,
            "missing": missing_docs,
            "has_illisible": has_illisible,
            "ok": docs_ok,
        },
        "rappel_assurance": _build_rappel_assurance(dossier),
        "all_ok": all_ok,
        # Le lien SMS est envoyable dès que les docs véhicule sont OK,
        # même si les docs client ont des problèmes (CNI expirée, domicile ancien, etc.)
        # Le client pourra corriger via le lien.
        "client_link_ready": docs_ok,
        "blocages": [
            item for section in [info_items, doc_items, missing_docs]
            for item in section
            if item["status"] in ("manquant", "illisible")
        ],
    }



def _analyze_faces(doc_type: str, extracted: dict) -> dict | None:
    """
    Analyse les champs extraits pour determiner quelles faces sont presentes.
    Retourne None pour les documents sans recto/verso.
    """
    FACE_FIELDS = {
        "CNI": {
            "recto": ["nom_naissance", "prenoms", "date_naissance", "lieu_naissance", "sexe"],
            "verso": ["date_expiration", "n_document", "numero_document"],
            "required": ["nom_naissance", "date_naissance", "date_expiration"],
        },
        "PASSEPORT": {
            "recto": ["nom_naissance", "prenoms", "date_naissance", "date_expiration",
                       "n_document", "numero_document", "mrz_nom"],
            "verso": [],
            "required": ["nom_naissance", "date_naissance", "date_expiration"],
        },
        "PERMIS": {
            "recto": ["nom", "prenom", "date_naissance", "categories", "numero_permis"],
            "verso": ["categories_dates"],
            "required": ["date_naissance", "categories"],
        },
    }

    fields = FACE_FIELDS.get(doc_type)
    if not fields:
        return None

    def _has(f):
        v = extracted.get(f)
        if v is None:
            return False
        if isinstance(v, str) and not v.strip():
            return False
        if isinstance(v, list) and len(v) == 0:
            return False
        return True

    if not fields["verso"]:
        required_ok = all(_has(f) for f in fields["required"])
        return {
            "recto_verso": False,
            "complet": required_ok,
            "message": None if required_ok else "Informations manquantes. Re-deposez le document.",
        }

    recto_found = sum(1 for f in fields["recto"] if _has(f))
    verso_found = sum(1 for f in fields["verso"] if _has(f))

    recto_present = recto_found >= 2
    verso_present = verso_found >= 1

    required_ok = all(_has(f) for f in fields["required"])

    if required_ok:
        message = "Document complet."
    elif recto_present and not verso_present:
        message = "Une seule face detectee. Deposez l'autre face pour completer."
    elif verso_present and not recto_present:
        message = "Une seule face detectee. Deposez l'autre face pour completer."
    else:
        missing = [f for f in fields["required"] if not _has(f)]
        message = f"Informations manquantes : {', '.join(missing)}. Deposez l'autre face ou re-deposez."

    return {
        "recto_verso": True,
        "recto_present": recto_present,
        "verso_present": verso_present,
        "complet": required_ok,
        "message": message,
    }


def _check_client_docs(dossier: dict) -> dict:
    """
    Checklist DYNAMIQUE cote client.
    Se met a jour apres chaque upload en fonction de ce qui a ete depose.

    Exemples d'adaptation dynamique :
    - Client uploade Kbis → PM detectee → permis retire de la liste
    - Vehicule = moto + permis B depose → attestation formation 7h ajoutee
    - Client repond "co-titulaire oui" → lien co-titulaire a envoyer
    """
    # Utiliser la liste dynamique des docs attendus
    docs_attendus = _get_client_docs_attendus(dossier)

    required = {d["type"]: d["label"] for d in docs_attendus if d.get("obligatoire")}
    optional = {d["type"]: d["label"] for d in docs_attendus if not d.get("obligatoire")}

    docs_client = dossier.get("documents_client", [])

    checklist = []
    found_types = set()
    has_illisible = False

    for d in docs_client:
        dtype = d.get("type", "PENDING").upper()
        # CNI et PASSEPORT comptent pour le meme besoin
        if dtype == "PASSEPORT":
            found_types.add("CNI")
        found_types.add(dtype)
        status = d.get("status", "PENDING")
        quality = d.get("quality", {})

        if status == "REJECTED" or quality.get("status") == "illisible":
            doc_status = "illisible"
            has_illisible = True
        elif status in ("EXTRACTED", "MERGED"):
            doc_status = "ok"
        else:
            doc_status = "en_cours"

        # Analyser la completude des faces pour les docs recto/verso
        faces = _analyze_faces(dtype, d.get("extracted_data", {}))

        checklist.append({
            "type": dtype,
            "filename": d.get("filename"),
            "source": d.get("source", "client"),
            "status": doc_status,
            "quality": quality,
            "faces": faces,
        })

    # Docs manquants (calcules depuis la liste dynamique)
    missing = []
    for dtype, label in required.items():
        if dtype not in found_types:
            # Trouver la raison dans docs_attendus si elle existe
            raison = next((d.get("raison") for d in docs_attendus if d["type"] == dtype and d.get("raison")), None)
            entry = {"type": dtype, "label": label, "required": True}
            if raison:
                entry["raison"] = raison
            missing.append(entry)
    for dtype, label in optional.items():
        if dtype not in found_types:
            missing.append({"type": dtype, "label": label, "required": False})

    # Tous les docs requis presents, lisibles, et faces completes ?
    def _doc_ok(req, c):
        """Un doc est ok si son statut est ok ET (pas de faces ou faces completes)."""
        type_match = c["type"] in (req, "PASSEPORT") if req == "CNI" else c["type"] == req
        if not type_match or c["status"] != "ok":
            return False
        # Si le doc a des faces recto/verso, verifier qu'elles sont completes
        faces = c.get("faces")
        if faces and faces.get("recto_verso") and not faces.get("complet"):
            return False
        return True

    all_required_ok = all(
        any(_doc_ok(req, c) for c in checklist)
        for req in required
    )

    # Infos deduites automatiquement
    is_pm = dossier.get("is_personne_morale", False)
    is_moto = _detect_is_moto(dossier)

    # Questions a poser au client dans la page d'upload
    questions_client = []
    if not is_pm:
        questions_client.append({
            "id": "is_personne_morale",
            "question": "Vous achetez en tant que societe (personne morale) ?",
            "type": "boolean",
            "impact": "Si oui, un Kbis sera demande et le permis ne sera plus requis.",
        })
    questions_client.append({
        "id": "has_co_titulaire",
        "question": "Y a-t-il un co-titulaire pour ce vehicule ?",
        "type": "boolean",
        "impact": "Si oui, le co-titulaire recevra un lien pour deposer ses documents et signer.",
    })

    # ─── Alertes client — problèmes détectés sur les docs déjà déposés ───
    # Ces alertes sont affichées au client pour qu'il sache quoi corriger.
    alertes = []

    for d in docs_client:
        dtype = d.get("type", "").upper()
        ext = d.get("extracted_data", {})

        # CNI / Passeport expiré
        if dtype in ("CNI", "PASSEPORT") and ext.get("date_expiration"):
            try:
                from datetime import date
                parts = ext["date_expiration"].replace("/", ".").split(".")
                if len(parts) == 3:
                    exp = date(int(parts[2]) if len(parts[2]) == 4 else 2000 + int(parts[2]), int(parts[1]), int(parts[0]))
                    if exp < date.today():
                        alertes.append({
                            "type": "erreur",
                            "doc": dtype,
                            "message": f"Votre pièce d'identité est expirée (date d'expiration : {ext['date_expiration']}). Déposez une pièce d'identité en cours de validité.",
                        })
            except (ValueError, IndexError):
                pass

        # Permis expiré
        if dtype == "PERMIS" and ext.get("date_expiration"):
            try:
                from datetime import date
                parts = ext["date_expiration"].replace("/", ".").split(".")
                if len(parts) == 3:
                    exp = date(int(parts[2]) if len(parts[2]) == 4 else 2000 + int(parts[2]), int(parts[1]), int(parts[0]))
                    if exp < date.today():
                        alertes.append({
                            "type": "erreur",
                            "doc": "PERMIS",
                            "message": f"Votre permis de conduire est expiré (date d'expiration : {ext['date_expiration']}). Déposez un permis en cours de validité.",
                        })
            except (ValueError, IndexError):
                pass

    # Domicile de plus de 6 mois
    for d in docs_client:
        dtype = d.get("type", "").upper()
        ext = d.get("extracted_data", {})
        if dtype == "DOMICILE" and ext.get("date_document"):
            try:
                from datetime import date, timedelta
                parts = ext["date_document"].replace("/", ".").split(".")
                if len(parts) == 3:
                    doc_date = date(int(parts[2]) if len(parts[2]) == 4 else 2000 + int(parts[2]), int(parts[1]), int(parts[0]))
                    if (date.today() - doc_date).days > 180:
                        alertes.append({
                            "type": "erreur",
                            "doc": "DOMICILE",
                            "message": f"Votre justificatif de domicile date du {ext['date_document']} — il doit dater de moins de 6 mois. Déposez un document plus récent.",
                        })
            except (ValueError, IndexError):
                pass

    # Nom divergent (hébergement)
    noms_cni = set()
    noms_domicile = set()
    for d in docs_client:
        dtype = d.get("type", "").upper()
        ext = d.get("extracted_data", {})
        if dtype in ("CNI", "PASSEPORT"):
            nom = ext.get("nom_naissance") or ext.get("nom")
            if nom:
                noms_cni.add(nom.upper().strip())
        if dtype == "DOMICILE":
            nom = ext.get("nom_titulaire")
            if nom:
                noms_domicile.add(nom.upper().strip())

    if noms_cni and noms_domicile:
        match = any(
            c in d or d in c
            for c in noms_cni for d in noms_domicile
        )
        if not match:
            nom_cni_str = ", ".join(noms_cni)
            nom_dom_str = ", ".join(noms_domicile)
            alertes.append({
                "type": "avertissement",
                "doc": "DOMICILE",
                "message": (
                    f"Le nom sur votre pièce d'identité ({nom_cni_str}) ne correspond pas "
                    f"au nom sur le justificatif de domicile ({nom_dom_str}). "
                    "Deux options : déposez un justificatif à votre nom, "
                    "ou fournissez une attestation d'hébergement et la pièce d'identité de votre hébergeant."
                ),
            })

    # Verrou client
    type_vehicule_connu = bool(dossier.get("type"))
    has_alertes_bloquantes = any(a["type"] == "erreur" for a in alertes)
    client_verrouille = type_vehicule_connu and all_required_ok and not has_illisible and not has_alertes_bloquantes

    return {
        "documents_attendus": docs_attendus,
        "documents": checklist,
        "missing": missing,
        "has_illisible": has_illisible,
        "all_required_ok": all_required_ok,
        "ready_for_diagnostic": all_required_ok and not has_illisible and not has_alertes_bloquantes,
        "client_verrouille": client_verrouille,
        "alertes": alertes,
        "infos_deduites": {
            "sexe": dossier.get("client_sexe"),
            "personne_morale": is_pm,
            "type_dossier": dossier.get("type"),
            "vehicule_moto": is_moto,
        },
        "questions": questions_client,
    }



def _check_cerfa_blocages(dossier: dict) -> dict:
    """
    Verifie si la generation du Cerfa peut se lancer.
    Bloque si :
    - Un doc pro est manquant ou illisible
    - Un doc client est manquant ou illisible
    - Tout element empechant la generation du Cerfa
    """
    pro_status = _check_pro_docs(dossier)
    client_status = _check_client_docs(dossier)

    reasons = []

    # Docs pro (structure : pro_status["documents"]["has_illisible"], pro_status["documents"]["items"])
    pro_docs = pro_status.get("documents", {})
    if pro_docs.get("has_illisible"):
        illisibles = [d.get("filename", "?") for d in pro_docs.get("items", []) if d.get("status") == "illisible"]
        reasons.append(f"Document(s) vendeur illisible(s) : {', '.join(illisibles)}")
    for m in pro_docs.get("missing", []):
        if m.get("required"):
            reasons.append(f"Document vendeur manquant : {m.get('label', '?')}")

    # Docs client (structure : client_status["documents"], client_status["missing"])
    if client_status.get("has_illisible"):
        illisibles = [d.get("filename", "?") for d in client_status.get("documents", []) if d.get("status") == "illisible"]
        reasons.append(f"Document(s) client illisible(s) : {', '.join(illisibles)}")
    for m in client_status.get("missing", []):
        if m.get("required"):
            reasons.append(f"Document client manquant : {m.get('label', '?')}")

    blocked = len(reasons) > 0

    return {
        "blocked": blocked,
        "reasons": reasons,
        "pro_status": pro_status,
        "client_status": client_status,
    }


def _get_nom_from_docs(docs: list, doc_type: str) -> str | None:
    """Extrait le nom depuis les docs client pour un type donne (CNI, DOMICILE, etc.)."""
    for d in docs:
        dtype = (d.get("type") or "").upper()
        ext = d.get("extracted_data", {})
        if not ext:
            continue
        if doc_type == "CNI" and dtype in ("CNI", "PASSEPORT"):
            nom = ext.get("nom_naissance") or ext.get("nom") or ext.get("mrz_nom")
            if nom:
                return nom.upper().strip()
        elif doc_type == "DOMICILE" and dtype == "DOMICILE":
            nom = ext.get("nom_titulaire")
            if nom:
                return nom.upper().strip()
    return None


def _get_vehicle_power_info(dossier: dict) -> dict:
    """
    Extrait les infos de puissance du vehicule depuis les docs pro (COC / CG barree).
    Retourne : categorie_l, puissance_kw, cylindree_cc, genre_national.
    """
    info = {
        "categorie_j": None,
        "puissance_kw": None,
        "cylindree_cc": None,
        "genre_national": None,
        "is_moto": False,
        "is_electrique": False,
    }

    for d in dossier.get("documents_vendeur", []):
        ext = d.get("extracted_data", {})
        if not ext:
            continue

        # Categorie J
        cat_j = ext.get("categorie_j", "")
        if cat_j and cat_j.upper().startswith("L"):
            info["categorie_j"] = cat_j.upper()
            info["is_moto"] = True

        # Genre national
        genre = ext.get("genre_national", "")
        if genre:
            info["genre_national"] = genre.upper()
            if genre.upper() in ("MTL", "MTT1", "MTT2", "CL", "QM", "CYCL"):
                info["is_moto"] = True

        # Puissance kW (P.2 du COC)
        p_kw = ext.get("puissance_nette_p2") or ext.get("puissance_kw")
        if p_kw:
            try:
                info["puissance_kw"] = float(p_kw)
            except (ValueError, TypeError):
                pass

        # Cylindree (P.1 du COC)
        cyl = ext.get("cylindree_p1") or ext.get("cylindree")
        if cyl:
            try:
                info["cylindree_cc"] = float(cyl)
            except (ValueError, TypeError):
                pass

        # Energie
        energie = ext.get("energie", "").upper()
        if energie in ("ELECTRIQUE", "ELECTRIC", "EL", "ELEC"):
            info["is_electrique"] = True

        # Debridable (COC mentionne conversion vers A2/A3)
        if ext.get("debridable"):
            info["debridable"] = True
            info["debridable_vers"] = ext.get("debridable_vers", [])

    return info



def _determine_permis_requis(vehicle_info: dict) -> dict:
    """
    Determine le permis requis et les documents complementaires
    en fonction du type et de la puissance du vehicule.

    Retourne :
    - permis_min : categorie minimum requise
    - formation_7h : True si formation 7h possible avec permis B
    - message : explication pour le client
    """
    if not vehicle_info["is_moto"]:
        return {"permis_min": "B", "formation_7h": False, "message": None}

    puissance = vehicle_info.get("puissance_kw")
    cylindree = vehicle_info.get("cylindree_cc")
    cat_j = vehicle_info.get("categorie_j", "")
    debridable = vehicle_info.get("debridable", False)
    debridable_vers = vehicle_info.get("debridable_vers", [])

    # ALERTE : vehicule debridable vers A2/A3
    # Si le COC mentionne la possibilite de conversion vers des categories
    # superieures, la puissance reelle est superieure a ce que la categorie
    # actuelle (A1E) laisse penser. Le permis B + formation 7h ne suffit PAS
    # car le vehicule est concu pour des puissances A2/A3.
    if debridable and ("A2" in debridable_vers or "A3" in debridable_vers):
        max_cat = "A" if "A3" in debridable_vers else "A2"
        return {
            "permis_min": max_cat,
            "formation_7h": False,
            "debridable": True,
            "message": (
                f"Vehicule {cat_j} homologue en version bridee mais le COC indique "
                f"une conversion possible vers {'/'.join(debridable_vers)}. "
                f"La puissance reelle du vehicule depasse le seuil du permis B + formation 7h. "
                f"Un permis {max_cat} est requis."
            ),
        }

    # Cyclomoteur (L1e) — ≤ 4 kW
    if cat_j.startswith("L1") or (puissance is not None and puissance <= 4):
        return {
            "permis_min": "AM",
            "formation_7h": False,
            "message": "Cyclomoteur (≤ 4 kW) — permis AM, B ou superieur suffit.",
        }

    # Moto legere / 125cc (L3e ≤ 11 kW)
    is_tricycle = cat_j.startswith("L5")

    if not is_tricycle and puissance is not None and puissance <= 11:
        return {
            "permis_min": "A1",
            "formation_7h": True,
            "age_min_formation": 20,  # B ≥ 2 ans, donc au moins 20 ans
            "message": (
                f"Vehicule {cat_j} de {puissance} kW — "
                f"permis A1 requis (age minimum 16 ans), ou permis B + attestation de formation 7h "
                f"(permis B obtenu depuis 2 ans minimum)."
            ),
        }

    # Tricycle L5e ≤ 15 kW
    if is_tricycle and puissance is not None and puissance <= 15:
        return {
            "permis_min": "A1",
            "formation_7h": True,
            "age_min_formation": 20,
            "message": (
                f"Tricycle {cat_j} de {puissance} kW — "
                f"permis A1 requis, ou permis B + attestation de formation 7h "
                f"(permis B obtenu depuis 2 ans minimum)."
            ),
        }

    # Tricycle L5e > 15 kW — cas special : B + formation 7h possible si age >= 21 ans
    if is_tricycle and puissance is not None and puissance > 15:
        return {
            "permis_min": "A",
            "formation_7h": True,
            "age_min_formation": 21,
            "tricycle_puissant": True,
            "message": (
                f"Tricycle {cat_j} de {puissance} kW (> 15 kW) — "
                f"permis A requis, ou permis B + attestation de formation 7h "
                f"(permis B obtenu depuis 2 ans minimum ET age minimum 21 ans)."
            ),
        }

    if cylindree is not None and cylindree <= 125 and puissance is None:
        return {
            "permis_min": "A1",
            "formation_7h": True,
            "message": (
                "Vehicule 125 cc — permis A1 requis, "
                "ou permis B + attestation de formation 7h."
            ),
        }

    # Moto intermediaire (≤ 35 kW) — pas de formation 7h possible
    if puissance is not None and puissance <= 35:
        return {
            "permis_min": "A2",
            "formation_7h": False,
            "age_min": 18,
            "message": (
                f"Vehicule {cat_j} de {puissance} kW — "
                f"permis A2 requis (age minimum 18 ans). Le permis B ne suffit pas."
            ),
        }

    # Moto puissante (> 35 kW)
    if puissance is not None and puissance > 35:
        return {
            "permis_min": "A",
            "formation_7h": False,
            "age_min": 20,
            "age_min_acces_direct": 24,
            "message": (
                f"Vehicule {cat_j} de {puissance} kW — "
                f"permis A requis (minimum 20 ans : 2 ans de permis A2 + formation complementaire, "
                f"ou 24 ans en acces direct)."
            ),
        }

    # Puissance inconnue — moto detectee mais pas de detail de puissance
    # SECURITE : on ne peut PAS conclure que B + formation 7h suffit
    # sans connaitre la puissance. On exige le permis moto par defaut.
    return {
        "permis_min": "A2",
        "formation_7h": False,
        "puissance_inconnue": True,
        "message": (
            "Deux-roues motorise detecte mais puissance non extraite du COC. "
            "Impossible de confirmer que le permis B + formation 7h suffit. "
            "Un permis moto (A1, A2 ou A) est requis par securite. "
            "Verifiez la puissance sur le COC (champ P.2 en kW)."
        ),
    }



def _get_client_docs_attendus(dossier: dict) -> list:
    """
    Retourne la liste DYNAMIQUE des documents attendus cote client.

    S'adapte en fonction de :
    - Type de vehicule (moto/voiture, puissance, cylindree)
    - Profil (personne physique/morale)
    - Documents deja deposes (permis, Kbis)
    - Reglementation permis en vigueur
    """
    is_pm = dossier.get("is_personne_morale", False)

    vehicle_info = _get_vehicle_power_info(dossier)
    permis_requis = _determine_permis_requis(vehicle_info)
    permis_categories = _get_permis_categories(dossier)
    is_vo = (dossier.get("type") or "").upper() in ("VO", "OCCASION")

    docs = []

    if is_pm:
        docs.append({"type": "KBIS", "label": "Kbis de la societe", "obligatoire": True})
        docs.append({"type": "CNI", "label": "CNI du representant legal", "obligatoire": True})
        docs.append({"type": "DOMICILE", "label": "Justificatif de domicile du siege", "obligatoire": True})
    else:
        docs.append({"type": "CNI", "label": "Piece d'identite (CNI ou Passeport)", "obligatoire": True,
                     "info": "Deposez 1 ou 2 fichiers — le systeme detecte automatiquement chaque face."})
        docs.append({"type": "PERMIS", "label": "Permis de conduire", "obligatoire": True,
                     "info": "Deposez 1 ou 2 fichiers — le systeme detecte automatiquement chaque face."})
        docs.append({"type": "DOMICILE", "label": "Justificatif de domicile", "obligatoire": True})

        # ─── Co-titulaire : demander docs selon type ───
        metadata = dossier.get("metadata", {})
        if metadata.get("has_cotitulaire"):
            cotitulaires = metadata.get("cotitulaires", [])
            for i, cot in enumerate(cotitulaires):
                if cot.get("type") == "morale":
                    cot_nom = cot.get("raison_sociale", f"co-titulaire {i+1}")
                    docs.append({
                        "type": f"KBIS_COTITULAIRE_{i+1}",
                        "label": f"Kbis du co-titulaire ({cot_nom})",
                        "obligatoire": True,
                    })
                else:
                    cot_nom = f"{cot.get('nom', '')} {cot.get('prenom', '')}".strip() or f"co-titulaire {i+1}"
                    docs.append({
                        "type": f"CNI_COTITULAIRE_{i+1}",
                        "label": f"Pièce d'identité du co-titulaire ({cot_nom})",
                        "obligatoire": True,
                        "info": "CNI ou passeport du co-titulaire. Déposez 1 ou 2 fichiers.",
                    })

        # ─── Detection hebergement : nom CNI ≠ nom domicile ───
        # Si les deux sont deposes et que les noms divergent,
        # ajouter attestation d'hebergement + CNI hebergeant
        nom_cni_check = _get_nom_from_docs(dossier.get("documents_client", []), "CNI")
        nom_domicile_check = _get_nom_from_docs(dossier.get("documents_client", []), "DOMICILE")
        needs_hebergement = False
        if nom_cni_check and nom_domicile_check:
            if (nom_cni_check not in nom_domicile_check
                    and nom_domicile_check not in nom_cni_check
                    and nom_cni_check != nom_domicile_check):
                needs_hebergement = True

        if needs_hebergement:
            # Avertissement + deux options pour le client
            docs.append({
                "type": "ALERTE_NOM_DOMICILE",
                "label": "Nom different sur le justificatif de domicile",
                "obligatoire": False,
                "bloquant": False,
                "raison": (
                    f"Le nom sur votre piece d'identite ({nom_cni_check}) ne correspond pas "
                    f"au nom sur le justificatif de domicile ({nom_domicile_check}). "
                    f"Deux options : modifiez votre justificatif de domicile ci-dessus "
                    f"pour en deposer un a votre nom, ou fournissez les documents "
                    f"d'hebergement ci-dessous."
                ),
            })
            # Verifier si les docs d'hebergement sont deja deposes
            client_types = {d.get("type", "").upper() for d in dossier.get("documents_client", [])}
            if "ATTESTATION_HEBERGEMENT" not in client_types:
                docs.append({
                    "type": "ATTESTATION_HEBERGEMENT",
                    "label": "Attestation d'hebergement",
                    "obligatoire": True,
                    "raison": (
                        "Attestation manuscrite signee par votre hebergeant, "
                        "ou remplacez le justificatif de domicile par un document a votre nom."
                    ),
                })
            if "CNI_HEBERGEANT" not in client_types:
                docs.append({
                    "type": "CNI_HEBERGEANT",
                    "label": "Piece d'identite de l'hebergeant",
                    "obligatoire": True,
                    "raison": (
                        f"Piece d'identite de {nom_domicile_check} (votre hebergeant), "
                        f"ou remplacez le justificatif de domicile par un document a votre nom."
                    ),
                    "info": "Deposez 1 ou 2 fichiers — le systeme detecte automatiquement chaque face.",
                })

        # Verification validite piece d'identite (CNI/passeport)
        identite_problems = _check_identite_validity(dossier)
        docs.extend(identite_problems)

        # Verification validite du permis (si deja depose)
        if permis_categories is not None:
            permis_problems = _check_permis_validity(dossier, vehicle_info, permis_requis)
            docs.extend(permis_problems)

        # Croisement CNI/passeport ↔ permis (si les deux sont deposes)
        if permis_categories is not None:
            coherence_problems = _check_identite_permis_coherence(dossier)
            docs.extend(coherence_problems)

        # Verification age minimum pour permis B (auto) — 18 ans
        if not vehicle_info["is_moto"]:
            client_age = _get_client_age(dossier)
            if client_age is not None and client_age < 18:
                docs.append({
                    "type": "AGE_INSUFFISANT",
                    "label": "Age insuffisant pour le permis B",
                    "obligatoire": True,
                    "bloquant": True,
                    "raison": f"Le client a {client_age} ans. Le permis B requiert 18 ans minimum.",
                })

        # Verification permis vs vehicule (si permis deja depose)
        if vehicle_info["is_moto"] and permis_categories is not None:
            min_cat = permis_requis["permis_min"]

            # Hierarchie permis moto : AM < A1 < A2 < A
            moto_hierarchy = {"AM": 0, "A1": 1, "A2": 2, "A": 3}
            min_level = moto_hierarchy.get(min_cat, 0)

            # Quel est le meilleur permis moto du client ?
            client_moto_cats = [c for c in permis_categories if c in moto_hierarchy]
            client_best_level = max((moto_hierarchy[c] for c in client_moto_cats), default=-1)

            has_b = "B" in permis_categories

            if client_best_level >= min_level:
                # Le client a le bon permis moto → pas de doc complementaire
                pass
            elif has_b and permis_requis["formation_7h"]:
                # Le client a le permis B et le vehicule accepte B + formation 7h
                # Verification en deux temps :
                # 1. Si attestation formation deja deposee → verifier date_B + 2 ans <= date_attestation
                # 2. Si attestation pas encore deposee → verifier date_B + 2 ans <= aujourd'hui

                permis_data = _get_permis_data(dossier)

                # Verifier si l'attestation de formation est deja deposee
                attestation_data = None
                for dc in dossier.get("documents_client", []):
                    if dc.get("type", "").upper() == "ATTESTATION_FORMATION":
                        attestation_data = dc.get("extracted_data", {})
                        break

                anciennete = _check_anciennete_permis_b(permis_data, attestation_data)

                if anciennete.get("exempt_formation"):
                    # Permis B avant 1980 → exempt de formation
                    docs.append({
                        "type": "INFO_EXEMPTION",
                        "label": "Exempt de formation 7h",
                        "obligatoire": False,
                        "info": anciennete["message"],
                    })
                elif anciennete.get("eligible_formation_7h"):
                    if attestation_data:
                        # Attestation deja deposee ET anciennete validee
                        pass  # L'attestation est deja dans les docs, pas besoin de la redemander
                    else:
                        # Pas encore d'attestation → la demander
                        docs.append({
                            "type": "ATTESTATION_FORMATION",
                            "label": "Attestation de suivi de formation 7h",
                            "obligatoire": True,
                            "raison": (
                                f"{permis_requis['message']} "
                                f"{anciennete['message']}"
                            ),
                        })
                elif anciennete.get("anciennete_inconnue"):
                    docs.append({
                        "type": "PERMIS_INSUFFISANT",
                        "label": "Anciennete permis B non verifiable",
                        "obligatoire": True,
                        "bloquant": True,
                        "raison": anciennete["message"],
                        "action": (
                            "La date d'obtention du permis B n'a pas pu etre lue. "
                            "Deposez un scan plus net ou fournissez un permis A1."
                        ),
                    })
                elif anciennete.get("attestation_invalide"):
                    # Attestation deposee mais date_B + 2 ans > date_attestation
                    docs.append({
                        "type": "PERMIS_INSUFFISANT",
                        "label": "Attestation de formation invalide",
                        "obligatoire": True,
                        "bloquant": True,
                        "raison": anciennete["message"],
                        "action": anciennete.get("action", ""),
                    })
                else:
                    # Permis B < 2 ans → formation 7h impossible
                    docs.append({
                        "type": "PERMIS_INSUFFISANT",
                        "label": "Permis B trop recent pour la formation 7h",
                        "obligatoire": True,
                        "bloquant": True,
                        "raison": anciennete["message"],
                        "action": (
                            f"Le permis B doit etre detenu depuis 2 ans minimum. "
                            f"Eligible a partir du {anciennete.get('date_eligible', '?')}. "
                            f"Un permis A1 est requis en attendant."
                        ),
                    })
            elif has_b and not permis_requis["formation_7h"]:
                # Le client a le permis B mais le vehicule est trop puissant
                docs.append({
                    "type": "PERMIS_INSUFFISANT",
                    "label": f"Permis {min_cat} requis",
                    "obligatoire": True,
                    "raison": permis_requis["message"],
                    "bloquant": True,
                    "action": (
                        f"Le permis B ne suffit pas pour ce vehicule. "
                        f"Un permis {min_cat} est obligatoire."
                    ),
                })
            elif not has_b and client_best_level < min_level:
                # Le client n'a pas le bon niveau de permis moto
                docs.append({
                    "type": "PERMIS_INSUFFISANT",
                    "label": f"Permis {min_cat} requis",
                    "obligatoire": True,
                    "raison": permis_requis["message"],
                    "bloquant": True,
                    "action": f"Un permis {min_cat} minimum est requis pour ce vehicule.",
                })

        # Verification d'age (si CNI deja deposee)
        if vehicle_info["is_moto"]:
            client_age = _get_client_age(dossier)

            if client_age is not None:
                # Age minimum selon le permis requis
                age_min = permis_requis.get("age_min")
                age_min_formation = permis_requis.get("age_min_formation")

                # Cas L5e > 15 kW : B + formation possible mais age >= 21
                if permis_requis.get("tricycle_puissant") and has_b and client_age < 21:
                    docs.append({
                        "type": "AGE_INSUFFISANT",
                        "label": "Age insuffisant pour B + formation (tricycle > 15 kW)",
                        "obligatoire": True,
                        "bloquant": True,
                        "raison": (
                            f"Le client a {client_age} ans. Pour conduire un tricycle > 15 kW "
                            f"avec le permis B + formation 7h, il faut avoir 21 ans minimum."
                        ),
                        "action": "Un permis A est requis, ou attendre 21 ans pour B + formation.",
                    })

                # Age minimum pour A2 (18 ans)
                elif age_min and permis_requis["permis_min"] == "A2" and client_age < 18:
                    docs.append({
                        "type": "AGE_INSUFFISANT",
                        "label": "Age insuffisant pour le permis A2",
                        "obligatoire": True,
                        "bloquant": True,
                        "raison": f"Le client a {client_age} ans. Le permis A2 requiert 18 ans minimum.",
                        "action": "Le client doit avoir 18 ans minimum pour le permis A2.",
                    })

                # Age minimum pour A (20 ans via A2+2 ans, ou 24 ans en acces direct)
                elif age_min and permis_requis["permis_min"] == "A" and client_age < 20:
                    docs.append({
                        "type": "AGE_INSUFFISANT",
                        "label": "Age insuffisant pour le permis A",
                        "obligatoire": True,
                        "bloquant": True,
                        "raison": (
                            f"Le client a {client_age} ans. Le permis A requiert minimum "
                            f"20 ans (2 ans de A2 + formation) ou 24 ans en acces direct."
                        ),
                        "action": "Le client doit avoir 20 ans minimum pour le permis A.",
                    })

        # Info reglementaire affichee au client (meme avant depot du permis)
        if vehicle_info["is_moto"] and permis_requis["message"]:
            docs.append({
                "type": "INFO_REGLEMENTAIRE",
                "label": "Information permis",
                "obligatoire": False,
                "info": permis_requis["message"],
            })

    # Assurance — basee sur le parametrage global du pro
    is_vo_dossier = (dossier.get("type") or "").upper() in ("VO", "OCCASION")
    demander_assurance = (
        (is_vo_dossier and PROFIL_PRO.get("demander_assurance_client_vo"))
        or (not is_vo_dossier and PROFIL_PRO.get("demander_assurance_client_vn"))
    )
    if demander_assurance:
        docs.append({
            "type": "ASSURANCE",
            "label": "Attestation d'assurance",
            "obligatoire": True,
            "raison": (
                f"{PROFIL_PRO.get('nom_commerce', 'Votre vendeur')} vous demande de fournir "
                "une attestation d'assurance pour ce vehicule "
                "(attestation provisoire ou carte verte)."
            ),
        })

    # Note : le CT n'est PAS dans la checklist client.
    # C'est un document vendeur — le rappel CT est affiche cote pro (voir _check_pro_docs).

    return docs



def _check_identite_validity(dossier: dict) -> list:
    """
    Verifie la validite de la piece d'identite (CNI ou passeport) :
    1. Non expiree
    2. Regle CNI 2004-2013 : +5 ans de validite pour les majeurs
    3. Passeport : pas de regle supplementaire, juste la date d'expiration

    Retourne une liste de problemes.
    """
    problems = []

    for d in dossier.get("documents_client", []):
        dtype = d.get("type", "").upper()
        is_cotitulaire = dtype.startswith("CNI_COTITULAIRE")
        if dtype not in ("CNI", "PASSEPORT") and not is_cotitulaire:
            continue

        ext = d.get("extracted_data", {})
        date_exp_str = ext.get("date_expiration")
        label_prefix = "co-titulaire — " if is_cotitulaire else ""
        type_id = label_prefix + ext.get("type_identite", dtype)

        if not date_exp_str:
            # Pas de date d'expiration extractible → warning
            problems.append({
                "type": "IDENTITE_EXPIRATION_INCONNUE",
                "label": f"Date d'expiration du {type_id} non lisible",
                "obligatoire": True,
                "bloquant": False,
                "raison": "La date d'expiration n'a pas pu etre lue. Verifiez que le document est en cours de validite.",
            })
            continue

        # Parser la date
        date_exp = None
        for fmt in ("%d.%m.%Y", "%d/%m/%Y", "%d.%m.%y", "%d/%m/%y"):
            try:
                date_exp = datetime.strptime(date_exp_str, fmt)
                if date_exp.year > 2050:
                    date_exp = date_exp.replace(year=date_exp.year - 100)
                break
            except ValueError:
                continue

        if not date_exp:
            continue

        today = datetime.utcnow()

        # Regle CNI 2004-2013 : +5 ans pour les majeurs
        # Les CNI delivrees entre le 02/01/2004 et le 31/12/2013 aux personnes
        # majeures beneficient de 5 ans de validite supplementaires (15 ans au total)
        date_exp_effective = date_exp

        if type_id == "CNI":
            # Chercher la date de delivrance pour appliquer la regle 2004-2013
            date_deliv_str = ext.get("date_delivrance")
            if date_deliv_str:
                date_deliv = None
                for fmt in ("%d.%m.%Y", "%d/%m/%Y", "%d.%m.%y", "%d/%m/%y"):
                    try:
                        date_deliv = datetime.strptime(date_deliv_str, fmt)
                        if date_deliv.year > 2050:
                            date_deliv = date_deliv.replace(year=date_deliv.year - 100)
                        break
                    except ValueError:
                        continue

                if date_deliv:
                    # Si delivree entre 2004 et 2013 → +5 ans
                    if 2004 <= date_deliv.year <= 2013:
                        # Verifier que le titulaire etait majeur a la delivrance
                        date_naiss_str = ext.get("date_naissance")
                        if date_naiss_str:
                            date_naiss = None
                            for fmt in ("%d.%m.%Y", "%d/%m/%Y"):
                                try:
                                    date_naiss = datetime.strptime(date_naiss_str, fmt)
                                    break
                                except ValueError:
                                    continue
                            if date_naiss:
                                age_delivrance = date_deliv.year - date_naiss.year
                                if (date_deliv.month, date_deliv.day) < (date_naiss.month, date_naiss.day):
                                    age_delivrance -= 1
                                if age_delivrance >= 18:
                                    # Majeur + delivree 2004-2013 → +5 ans
                                    date_exp_effective = date_exp.replace(year=date_exp.year + 5)

        if today > date_exp_effective:
            msg_extra = ""
            if type_id == "CNI" and date_exp_effective != date_exp:
                msg_extra = (
                    f" (regle 2004-2013 appliquee : validite etendue "
                    f"jusqu'au {date_exp_effective.strftime('%d/%m/%Y')})"
                )
            if today > date_exp_effective:
                problems.append({
                    "type": "IDENTITE_EXPIREE",
                    "label": f"{type_id} expire",
                    "obligatoire": True,
                    "bloquant": True,
                    "raison": (
                        f"{type_id} expire le {date_exp.strftime('%d/%m/%Y')}{msg_extra}. "
                        "Un document d'identite en cours de validite est obligatoire."
                    ),
                    "action": f"Renouvelez votre {type_id} ou fournissez un passeport valide.",
                })
        else:
            # Document valide — info
            if date_exp_effective != date_exp:
                problems.append({
                    "type": "IDENTITE_REGLE_2004_2013",
                    "label": "CNI — regle 2004-2013 appliquee",
                    "obligatoire": False,
                    "info": (
                        f"CNI delivree entre 2004 et 2013 a un majeur : validite etendue de 5 ans. "
                        f"Date imprimee : {date_exp.strftime('%d/%m/%Y')} → "
                        f"valide jusqu'au {date_exp_effective.strftime('%d/%m/%Y')}."
                    ),
                })

        break  # Un seul doc d'identite suffit

    return problems



def _deduce_departement_from_commune(commune: str) -> str | None:
    """
    Deduit le code departement a partir de la commune de naissance.

    Utilise le code postal si disponible dans le texte, sinon une table
    des grandes villes francaises. Pour les petites communes, retourne None
    (le pro devra verifier manuellement).
    """
    if not commune:
        return None

    c = commune.upper().strip()

    # Table des grandes villes / prefectures → departement
    COMMUNES_DEPT = {
        "PARIS": "75", "MARSEILLE": "13", "LYON": "69", "TOULOUSE": "31",
        "NICE": "06", "NANTES": "44", "MONTPELLIER": "34", "STRASBOURG": "67",
        "BORDEAUX": "33", "LILLE": "59", "RENNES": "35", "REIMS": "51",
        "SAINT-ETIENNE": "42", "LE HAVRE": "76", "TOULON": "83",
        "GRENOBLE": "38", "DIJON": "21", "ANGERS": "49", "NIMES": "30",
        "VILLEURBANNE": "69", "CLERMONT-FERRAND": "63", "LE MANS": "72",
        "AIX-EN-PROVENCE": "13", "BREST": "29", "TOURS": "37",
        "AMIENS": "80", "LIMOGES": "87", "PERPIGNAN": "66",
        "METZ": "57", "BESANCON": "25", "ORLEANS": "45",
        "ROUEN": "76", "MULHOUSE": "68", "CAEN": "14",
        "NANCY": "54", "ARGENTEUIL": "95", "SAINT-DENIS": "93",
        "MONTREUIL": "93", "ROUBAIX": "59", "TOURCOING": "59",
        "AVIGNON": "84", "NANTERRE": "92", "VITRY-SUR-SEINE": "94",
        "CREMIEUX": "38", "POITIERS": "86", "AUBERVILLIERS": "93",
        "COLOMBES": "92", "DUNKERQUE": "59", "VALENCE": "26",
        "QUIMPER": "29", "LORIENT": "56", "VANNES": "56",
        "SAINT-BRIEUC": "22", "CERGY": "95", "PONTOISE": "95",
        "BAYONNE": "64", "PAU": "64", "LA ROCHELLE": "17",
        "CALAIS": "62", "BOULOGNE-BILLANCOURT": "92",
        "AJACCIO": "2A", "BASTIA": "2B",
        "FORT-DE-FRANCE": "972", "POINTE-A-PITRE": "971",
        "SAINT-DENIS-REUNION": "974", "CAYENNE": "973", "MAMOUDZOU": "976",
    }

    # Recherche directe
    if c in COMMUNES_DEPT:
        return COMMUNES_DEPT[c]

    # Recherche partielle (ex: "CERGY PONTOISE" → match "CERGY")
    for ville, dept in COMMUNES_DEPT.items():
        if ville in c or c in ville:
            return dept

    return None



def _has_docs_via_fichier(dossier: dict, doc_types: list[str]) -> bool:
    """Verifie si au moins un des documents indiques a ete depose via fichier (pas photo)."""
    for d in dossier.get("documents_client", []):
        if d.get("type", "").upper() in [t.upper() for t in doc_types]:
            if not d.get("captured_by_camera", False):
                return True
    return False



def _make_incoherence_problem(
    problem_type: str, label: str, raison: str, dossier: dict, doc_types: list[str]
) -> dict:
    """
    Cree un probleme d'incoherence avec la bonne severite :
    - Si docs deposes via fichier → BLOCAGE + demande photo
    - Si docs deposes via photo → WARNING (l'ecart est probablement reel)
    """
    via_fichier = _has_docs_via_fichier(dossier, doc_types)

    if via_fichier:
        return {
            "type": problem_type,
            "label": label + " — reprenez en photo",
            "obligatoire": True,
            "bloquant": True,
            "raison": raison,
            "action": (
                "Les documents ont ete deposes en fichier. "
                "Reprenez les documents concernes en photo directement "
                "pour une meilleure lisibilite."
            ),
            "demande_photo": True,
        }
    else:
        return {
            "type": problem_type,
            "label": label,
            "obligatoire": True,
            "bloquant": False,
            "raison": raison,
        }



def _check_identite_permis_coherence(dossier: dict) -> list:
    """
    Croise les informations entre la piece d'identite (CNI/passeport) et le permis :
    - Date de naissance identique
    - Commune de naissance identique
    - Nom identique

    Regle : si incoherence detectee ET document depose via fichier → BLOCAGE + demande photo.
    Si depose via photo → WARNING.
    """
    problems = []

    identite_data = None
    for d in dossier.get("documents_client", []):
        if d.get("type", "").upper() in ("CNI", "PASSEPORT"):
            identite_data = d.get("extracted_data", {})
            break

    permis_data = None
    for d in dossier.get("documents_client", []):
        if d.get("type", "").upper() == "PERMIS":
            permis_data = d.get("extracted_data", {})
            break

    if not identite_data or not permis_data:
        return problems

    doc_types_concernes = ["CNI", "PASSEPORT", "PERMIS"]

    # ─── 1. Date de naissance ───
    date_naiss_id = identite_data.get("date_naissance", "").strip()
    date_naiss_permis = permis_data.get("date_naissance", "").strip()

    if date_naiss_id and date_naiss_permis:
        dn_id = date_naiss_id.replace("/", ".").replace("-", ".")
        dn_p = date_naiss_permis.replace("/", ".").replace("-", ".")
        if dn_id != dn_p:
            problems.append(_make_incoherence_problem(
                "INCOHERENCE_DATE_NAISSANCE",
                "Date de naissance differente entre CNI et permis",
                (
                    f"CNI/passeport : {date_naiss_id} — Permis : {date_naiss_permis}. "
                    "Les deux documents doivent appartenir a la meme personne."
                ),
                dossier, doc_types_concernes,
            ))

    # ─── 2. Commune de naissance ───
    lieu_id = (identite_data.get("lieu_naissance") or "").upper().strip()
    lieu_permis = (permis_data.get("lieu_naissance") or "").upper().strip()

    if not lieu_permis:
        m = re.search(r"\(([A-Z][A-Za-zÀ-ÿ\- ]{2,30})\)", str(permis_data))
        if m:
            lieu_permis = m.group(1).upper().strip()

    if lieu_id and lieu_permis:
        if lieu_id != lieu_permis and lieu_id not in lieu_permis and lieu_permis not in lieu_id:
            problems.append(_make_incoherence_problem(
                "INCOHERENCE_LIEU_NAISSANCE",
                "Lieu de naissance different entre CNI et permis",
                f"CNI/passeport : {lieu_id} — Permis : {lieu_permis}.",
                dossier, doc_types_concernes,
            ))

    # ─── 3. Nom CNI ↔ Permis ───
    nom_id = (identite_data.get("nom_naissance") or identite_data.get("nom") or "").upper().strip()
    nom_permis = (permis_data.get("nom") or "").upper().strip()

    if nom_id and nom_permis and len(nom_id) > 1 and len(nom_permis) > 1:
        if nom_id != nom_permis and nom_id not in nom_permis and nom_permis not in nom_id:
            problems.append(_make_incoherence_problem(
                "INCOHERENCE_NOM",
                "Nom different entre CNI et permis",
                f"CNI/passeport : '{nom_id}' — Permis : '{nom_permis}'.",
                dossier, doc_types_concernes,
            ))

    # ─── 4. Nom acheteur sur CG barree — supprimé ───
    # L'identité de l'acquéreur vient désormais directement de la CNI uploadée
    # par l'agent. La barre manuscrite de la CG ne sert plus à rien dans le
    # rapprochement (souvent illisible OCR + redondante avec la CNI).

    # ─── 5. Date vente CG barree ↔ date cession certificat 15776 ───
    date_vente_cg = None
    for d in dossier.get("documents_vendeur", []):
        if d.get("type", "").upper() == "CG_BARREE":
            date_vente_cg = (d.get("extracted_data", {}).get("date_vente") or "").strip()
            break

    date_cession = None
    for d in dossier.get("documents_vendeur", []):
        if d.get("type", "").upper() == "CERTIFICAT_CESSION":
            date_cession = (d.get("extracted_data", {}).get("date_cession") or "").strip()
            break

    if date_vente_cg and date_cession:
        dv = date_vente_cg.replace("/", ".").replace("-", ".")
        dc = date_cession.replace("/", ".").replace("-", ".")
        if dv != dc:
            problems.append(_make_incoherence_problem(
                "INCOHERENCE_DATE_VENTE_CESSION",
                "Date de vente CG barree differente du certificat de cession",
                (
                    f"Date de vente sur la CG barree : {date_vente_cg} — "
                    f"Date de cession sur le 15776 : {date_cession}. "
                    "Les deux dates doivent etre identiques."
                ),
                dossier, ["CG_BARREE", "CERTIFICAT_CESSION"],
            ))

    # ─── 6. Nom acquereur certificat cession ↔ CNI client ───
    for d in dossier.get("documents_vendeur", []):
        if d.get("type", "").upper() == "CERTIFICAT_CESSION":
            ext_ces = d.get("extracted_data", {})
            nom_acq = (ext_ces.get("acquereur_nom") or "").upper().strip()

            if nom_acq and nom_id and len(nom_acq) > 1:
                if (nom_acq != nom_id
                        and nom_acq not in nom_id
                        and nom_id not in nom_acq):
                    problems.append(_make_incoherence_problem(
                        "INCOHERENCE_NOM_CESSION",
                        "Nom acquereur sur certificat de cession different de la CNI",
                        (
                            f"Acquereur sur le certificat de cession : '{nom_acq}' — "
                            f"Nom sur la CNI/passeport : '{nom_id}'. "
                            "Le nom de l'acquereur sur le 15776 doit correspondre au client."
                        ),
                        dossier, ["CNI", "PASSEPORT", "CERTIFICAT_CESSION"],
                    ))
            break

    # ─── 7. Attestation assurance ↔ vehicule + client ───
    # Si l'assurance a ete demandee et deposee, verifier :
    # - VIN assurance = VIN vehicule
    # - Nom assure = nom CNI client
    # - Assurance non expiree
    if dossier.get("demander_assurance_client"):
        for d in dossier.get("documents_client", []):
            if d.get("type", "").upper() == "ASSURANCE":
                ext_ass = d.get("extracted_data", {})

                # Verifier que c'est bien une assurance auto
                if not ext_ass.get("est_assurance_auto"):
                    problems.append({
                        "type": "ASSURANCE_PAS_AUTO",
                        "label": "Le document ne semble pas etre une attestation d'assurance automobile",
                        "obligatoire": True,
                        "bloquant": True,
                        "raison": (
                            "Le document depose n'a pas ete reconnu comme une attestation "
                            "d'assurance automobile. Deposez une attestation d'assurance auto, "
                            "une carte verte ou un memo vehicule assure."
                        ),
                    })

                # Nom assure ↔ nom CNI client
                nom_assure = (ext_ass.get("nom_assure") or "").upper().strip()
                if nom_assure and nom_id and len(nom_assure) > 1:
                    if (nom_assure != nom_id
                            and nom_assure not in nom_id
                            and nom_id not in nom_assure):
                        problems.append(_make_incoherence_problem(
                            "INCOHERENCE_NOM_ASSURANCE",
                            "Nom sur l'assurance different de la CNI",
                            (
                                f"Nom sur l'attestation d'assurance : '{nom_assure}' — "
                                f"Nom sur la CNI/passeport : '{nom_id}'."
                            ),
                            dossier, ["CNI", "PASSEPORT", "ASSURANCE"],
                        ))

                # Assurance non expiree
                date_ech_str = ext_ass.get("date_echeance")
                if date_ech_str:
                    for fmt in ("%d.%m.%Y", "%d/%m/%Y", "%d.%m.%y", "%d/%m/%y"):
                        try:
                            date_ech = datetime.strptime(date_ech_str, fmt)
                            if date_ech.year > 2050:
                                date_ech = date_ech.replace(year=date_ech.year - 100)
                            if date_ech < datetime.utcnow():
                                problems.append({
                                    "type": "ASSURANCE_EXPIREE",
                                    "label": "Attestation d'assurance expiree",
                                    "obligatoire": True,
                                    "bloquant": True,
                                    "raison": (
                                        f"L'attestation d'assurance a expire le "
                                        f"{date_ech.strftime('%d/%m/%Y')}. "
                                        "Fournissez une attestation en cours de validite."
                                    ),
                                })
                            break
                        except ValueError:
                            continue

                break

    return problems



def _check_permis_validity(dossier: dict, vehicle_info: dict, permis_requis: dict) -> list:
    """
    Verifie la validite du permis depose par le client :
    1. Le document est bien un permis (classification correcte)
    2. Le permis n'est pas expire (date_expiration vs aujourd'hui)
    3. Les categories correspondent au vehicule
    4. Le permis est au nom du client (coherence avec CNI)

    Retourne une liste de problemes detectes (vide si tout est ok).
    """
    problems = []
    permis_data = _get_permis_data(dossier)

    if not permis_data:
        return problems  # Pas encore depose, pas de verification

    # ─── 1. Verification expiration ───
    date_exp_str = permis_data.get("date_expiration")
    if date_exp_str:
        date_exp = None
        for fmt in ("%d.%m.%Y", "%d/%m/%Y", "%d.%m.%y", "%d/%m/%y"):
            try:
                date_exp = datetime.strptime(date_exp_str, fmt)
                if date_exp.year > 2050:
                    date_exp = date_exp.replace(year=date_exp.year - 100)
                break
            except ValueError:
                continue

        if date_exp and date_exp < datetime.utcnow():
            problems.append({
                "type": "PERMIS_EXPIRE",
                "label": "Permis de conduire expire",
                "obligatoire": True,
                "bloquant": True,
                "raison": (
                    f"Le permis a expire le {date_exp.strftime('%d/%m/%Y')}. "
                    "Un permis en cours de validite est obligatoire."
                ),
                "action": "Renouvelez votre permis de conduire avant de poursuivre la demarche.",
            })
    # Note : si pas de date d'expiration (ancien permis rose) → considere valide

    # ─── 2. Verification categories vs vehicule ───
    categories = permis_data.get("categories", [])
    if categories:
        min_cat = permis_requis.get("permis_min", "B")

        if vehicle_info.get("is_moto"):
            # Pour les motos, la verification detaillee est deja faite dans
            # _get_client_docs_attendus (attestation formation, blocage, etc.)
            pass
        else:
            # Pour les voitures : le permis B doit etre present
            if "B" not in categories and "BE" not in categories:
                problems.append({
                    "type": "PERMIS_CATEGORIE_MANQUANTE",
                    "label": "Categorie B absente du permis",
                    "obligatoire": True,
                    "bloquant": True,
                    "raison": (
                        f"Le permis depose a les categories {', '.join(categories)} "
                        "mais la categorie B est requise pour conduire une voiture."
                    ),
                    "action": "Deposez un permis avec la categorie B.",
                })

    # Note : la coherence nom/date/lieu entre CNI et permis est geree
    # par _check_identite_permis_coherence() (logique centralisee fichier vs photo)

    return problems



def _build_session_message(dossier: dict, checklist: dict) -> dict:
    """
    Message de session adapte : premiere visite ou retour.
    """
    docs_deposes = len([d for d in dossier.get("documents_client", []) if d.get("status") in ("EXTRACTED", "MERGED")])
    docs_manquants = len([m for m in checklist.get("missing", []) if m.get("required")])

    from notifications.messages import CLIENT as MSG_CLIENT

    if dossier.get("client_docs_envoyes"):
        return {"message": MSG_CLIENT["docs_deja_envoyes"], "retour": True}

    if docs_deposes == 0:
        return {"message": MSG_CLIENT["session_premiere_visite"], "premiere_visite": True}
    else:
        if docs_manquants > 0:
            msg = MSG_CLIENT["session_retour"].format(docs_deposes=docs_deposes, docs_manquants=docs_manquants)
        else:
            msg = MSG_CLIENT["session_retour_complet"]
        return {"message": msg, "retour": True, "docs_deposes": docs_deposes, "docs_manquants": docs_manquants}



def _build_rappel_assurance(dossier: dict) -> dict | None:
    """
    Rappel assurance cote pro.
    Affiche l'etat du choix assurance pour ce dossier.
    """
    if dossier.get("type") is None:
        return None

    choix_fait = dossier.get("choix_assurance_pro")

    from notifications.messages import PRO as MSG_PRO

    is_vo_dossier = (dossier.get("type") or "").upper() in ("VO", "OCCASION")

    flotte_couvre = (
        (is_vo_dossier and PROFIL_PRO.get("assurance_flotte_vo"))
        or (not is_vo_dossier and PROFIL_PRO.get("assurance_flotte_vn"))
    )
    demander_client = (
        (is_vo_dossier and PROFIL_PRO.get("demander_assurance_client_vo"))
        or (not is_vo_dossier and PROFIL_PRO.get("demander_assurance_client_vn"))
    )

    if flotte_couvre:
        return {"status": "couvert", "message": MSG_PRO["assurance_flotte_ok"]}

    if demander_client:
        return {"status": "demande_client", "message": MSG_PRO["assurance_demander_client"]}

    return {"status": "gere_par_pro", "message": MSG_PRO["assurance_gerer_direct"]}



def _detect_is_moto(dossier: dict) -> bool:
    """Detecte si le vehicule est une moto (utilise _get_vehicle_power_info)."""
    return _get_vehicle_power_info(dossier)["is_moto"]



def _get_permis_categories(dossier: dict) -> list | None:
    """
    Retourne les categories du permis deja depose par le client.
    None si le permis n'a pas encore ete depose.
    """
    for d in dossier.get("documents_client", []):
        if d.get("type", "").upper() == "PERMIS":
            ext = d.get("extracted_data", {})
            cats = ext.get("categories")
            if cats:
                return cats
            return []
    return None



def _get_permis_data(dossier: dict) -> dict | None:
    """
    Retourne toutes les donnees extraites du permis (categories, dates, etc.).
    None si le permis n'a pas encore ete depose.
    """
    for d in dossier.get("documents_client", []):
        if d.get("type", "").upper() == "PERMIS":
            return d.get("extracted_data", {})
    return None



def _get_client_age(dossier: dict) -> int | None:
    """
    Calcule l'age du client depuis sa date de naissance extraite de la CNI ou du permis.
    Retourne l'age en annees ou None si non disponible.
    """
    date_naissance_str = None

    # Chercher dans la CNI d'abord (plus fiable)
    for d in dossier.get("documents_client", []):
        dtype = d.get("type", "").upper()
        ext = d.get("extracted_data", {})
        if dtype in ("CNI", "PASSEPORT") and ext.get("date_naissance"):
            date_naissance_str = ext["date_naissance"]
            break

    # Fallback : depuis le permis
    if not date_naissance_str:
        for d in dossier.get("documents_client", []):
            if d.get("type", "").upper() == "PERMIS":
                ext = d.get("extracted_data", {})
                if ext.get("date_naissance"):
                    date_naissance_str = ext["date_naissance"]
                    break

    if not date_naissance_str:
        return None

    # Parser la date
    date_naissance = None
    for fmt in ("%d.%m.%Y", "%d/%m/%Y", "%d.%m.%y", "%d/%m/%y"):
        try:
            date_naissance = datetime.strptime(date_naissance_str, fmt)
            if date_naissance.year > 2050:
                date_naissance = date_naissance.replace(year=date_naissance.year - 100)
            break
        except ValueError:
            continue

    if not date_naissance:
        return None

    # Calcul age en annees civiles
    today = datetime.utcnow()
    age = today.year - date_naissance.year
    if (today.month, today.day) < (date_naissance.month, date_naissance.day):
        age -= 1
    return age



def _check_anciennete_permis_b(permis_data: dict, attestation_data: dict | None = None) -> dict:
    """
    Verifie l'anciennete du permis B pour la regle des 2 ans (formation 7h 125cc).

    Logique en deux temps :
    1. Si attestation de formation DEJA deposee → verifier que date_B + 2 ans <= date_attestation
       (la moto-ecole a du verifier, mais on re-verifie par securite)
    2. Si attestation PAS encore deposee → verifier que date_B + 2 ans <= aujourd'hui
       (sinon la formation n'a pas pu etre faite)

    Reglementation :
    - Permis B obtenu depuis >= 2 ans : formation 7h possible
    - Permis B obtenu avant le 1er mars 1980 : EXEMPT de formation
    - Permis B < 2 ans : formation 7h non possible, permis A1 obligatoire

    Retourne : {"eligible_formation_7h": bool, "exempt_formation": bool, "message": str}
    """
    if not permis_data:
        return {"eligible_formation_7h": False, "exempt_formation": False,
                "anciennete_inconnue": True,
                "message": "Date d'obtention du permis B non disponible — impossible de verifier l'anciennete."}

    date_b_str = permis_data.get("date_obtention_b") or permis_data.get("date_delivrance")
    if not date_b_str:
        return {"eligible_formation_7h": False, "exempt_formation": False,
                "anciennete_inconnue": True,
                "message": "Date d'obtention du permis B non extraite — impossible de verifier l'anciennete de 2 ans."}

    # Parser la date (formats : JJ.MM.AA, JJ/MM/AA, JJ.MM.AAAA, JJ/MM/AAAA)
    from datetime import timedelta
    date_b = None
    for fmt in ("%d.%m.%y", "%d/%m/%y", "%d.%m.%Y", "%d/%m/%Y"):
        try:
            date_b = datetime.strptime(date_b_str, fmt)
            # Si annee sur 2 chiffres et > 50, c'est 1900+
            if date_b.year > 2050:
                date_b = date_b.replace(year=date_b.year - 100)
            break
        except ValueError:
            continue

    if not date_b:
        return {"eligible_formation_7h": False, "exempt_formation": False,
                "anciennete_inconnue": True,
                "message": f"Date du permis B '{date_b_str}' non interpretable."}

    # Exemption : permis B avant le 1er mars 1980
    date_1980 = datetime(1980, 3, 1)
    if date_b < date_1980:
        return {
            "eligible_formation_7h": False,
            "exempt_formation": True,
            "date_obtention_b": date_b.strftime("%d/%m/%Y"),
            "message": (
                f"Permis B obtenu le {date_b.strftime('%d/%m/%Y')} (avant le 01/03/1980). "
                "Vous etes EXEMPT de la formation 7h — aucune attestation requise."
            ),
        }

    # Regle des 2 ans — calcul dynamique en annees civiles
    # Permis B du 29/11/2023 → eligible le 29/11/2025
    date_eligible = date_b.replace(year=date_b.year + 2)
    date_b_fmt = date_b.strftime("%d/%m/%Y")
    date_eligible_fmt = date_eligible.strftime("%d/%m/%Y")

    # Date de reference pour la verification :
    # - Si attestation deposee → date de l'attestation (la formation a eu lieu ce jour)
    # - Sinon → aujourd'hui (la formation n'a pas encore eu lieu)
    date_reference = None
    date_ref_label = "aujourd'hui"

    if attestation_data:
        # Chercher la date de l'attestation
        date_att_str = (
            attestation_data.get("date_formation")
            or attestation_data.get("date_document")
            or attestation_data.get("date_attestation")
        )
        if date_att_str:
            for fmt in ("%d.%m.%y", "%d/%m/%y", "%d.%m.%Y", "%d/%m/%Y"):
                try:
                    date_reference = datetime.strptime(date_att_str, fmt)
                    if date_reference.year > 2050:
                        date_reference = date_reference.replace(year=date_reference.year - 100)
                    date_ref_label = f"date attestation ({date_reference.strftime('%d/%m/%Y')})"
                    break
                except ValueError:
                    continue

    if date_reference is None:
        date_reference = datetime.utcnow()
        date_ref_label = "aujourd'hui"

    # Anciennete en annees et mois par rapport a la date de reference
    annees = date_reference.year - date_b.year
    mois = date_reference.month - date_b.month
    if date_reference.day < date_b.day:
        mois -= 1
    if mois < 0:
        annees -= 1
        mois += 12

    if date_reference >= date_eligible:
        return {
            "eligible_formation_7h": True,
            "exempt_formation": False,
            "date_obtention_b": date_b_fmt,
            "date_eligible": date_eligible_fmt,
            "anciennete_annees": annees,
            "anciennete_mois": mois,
            "message": (
                f"Permis B obtenu le {date_b_fmt} "
                f"({annees} ans et {mois} mois a {date_ref_label}). "
                "Eligible a la formation 7h pour conduire un 125cc/L5e."
            ),
        }
    else:
        # Verifier si c'est un probleme d'attestation trop ancienne
        if attestation_data and date_reference < date_eligible:
            return {
                "eligible_formation_7h": False,
                "exempt_formation": False,
                "attestation_invalide": True,
                "date_obtention_b": date_b_fmt,
                "date_eligible": date_eligible_fmt,
                "message": (
                    f"Attestation de formation invalide : le permis B a ete obtenu le {date_b_fmt} "
                    f"et la formation a eu lieu le {date_reference.strftime('%d/%m/%Y')} — "
                    f"soit moins de 2 ans apres l'obtention du permis B. "
                    f"Le permis B devait etre detenu depuis le {date_eligible_fmt} minimum."
                ),
                "action": (
                    "L'attestation de formation n'est pas valide car le permis B "
                    "n'avait pas 2 ans d'anciennete au moment de la formation. "
                    "Un permis A1 est requis."
                ),
            }

        return {
            "eligible_formation_7h": False,
            "exempt_formation": False,
            "date_obtention_b": date_b_fmt,
            "date_eligible": date_eligible_fmt,
            "anciennete_annees": annees,
            "anciennete_mois": mois,
            "message": (
                f"Permis B obtenu le {date_b_fmt} — "
                f"anciennete insuffisante ({annees} an(s) et {mois} mois). "
                f"Eligible a la formation 7h a partir du {date_eligible_fmt}. "
                "Un permis A1 est requis en attendant."
            ),
        }


# ─── Diagnostic et Cerfa ─────────────────────────────────────────────────────


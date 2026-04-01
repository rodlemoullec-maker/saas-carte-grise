"""
Serveur demo v2 - moteur adapte au projet reel.

Logique :
- Le pro depose ses docs, le systeme detecte automatiquement VN/VO
- Le moteur classifie, extrait, croise, verifie en temps reel
- Checklist interactive : tout doit etre present et lisible pour generer le Cerfa
- Le Cerfa est genere automatiquement avec cachet et signature du pro

Usage : python demo_server.py → http://localhost:8000
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

from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Carte Grise Pro - Demo v2", version="0.3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── In-memory storage ────────────────────────────────────────────────────────

DOSSIERS: dict[str, dict] = {}
UPLOAD_DIR = Path("./data/demo_uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


# ─── Classification par mots-cles ─────────────────────────────────────────────

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
        ("certificat de conformite", 1.0), ("certificate of conformity", 0.9),
        ("homologation", 0.5), ("cnit", 0.5), ("puissance nette", 0.6),
        ("masse en charge", 0.4),
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
        ("certificat d'immatriculation", 0.6), ("carte grise", 0.6),
        ("vendu le", 0.9), ("formule", 0.3), ("titulaire", 0.3),
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
    Fallback OCR via Google Document AI (payant, pour docs que Tesseract ne gere pas).

    Retourne {"text": str, "confidence": float}.
    """
    from integrations.ocr_providers.google_docai import GoogleDocAIProvider

    creds = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "")
    if not creds:
        for f_cred in Path(".").glob("**/gen-lang-client*.json"):
            creds = str(f_cred)
            break
    if not creds:
        return {"text": "", "confidence": 0.0}

    ocr = GoogleDocAIProvider(credentials_path=creds)
    result = ocr.process_sync(file_bytes, mime_type)
    return {"text": result.full_text, "confidence": result.average_confidence}


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

def extract_data(doc_type: str, text: str) -> dict:
    """Extrait les champs cles selon le type."""
    data: dict[str, Any] = {}

    # VIN (universel - cherche sur tous les docs)
    m = re.search(r"(?:VIN|chassis|[Ee])\s*[:\s]*([A-HJ-NPR-Z0-9]{17})", text)
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
            # Format Google DocAI CNI (champs sur lignes separees)
            if not data.get("nom_naissance"):
                m = re.search(r"C\.?1\s+([A-Z]{2,30})", text)
                if m: data["nom_naissance"] = m.group(1).strip()
            if not data.get("prenoms"):
                nom = data.get("nom_naissance", "")
                if nom:
                    m = re.search(re.escape(nom) + r"\s*\n\s*([A-Z][a-zÀ-ÿ]{1,20})", text)
                    if m: data["prenoms"] = m.group(1).strip()
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
        # Marque (FR: "Marque", EN: "Make", ou champ 0.1)
        m = re.search(r"(?:0\.1\.?\s*)?(?:[Mm]arque|[Mm]ake)\s*[:\s(]*([A-Z][A-Za-z\-]{1,20})", text)
        if m: data["marque"] = m.group(1).strip()
        # Modele / denomination commerciale (FR + EN)
        m = re.search(r"(?:[Dd]enomination\s*(?:commerciale)?|[Cc]ommercial\s*name)\s*[:\s]*(.{2,50})", text)
        if m: data["modele"] = m.group(1).strip()
        # Type (champ 0.2)
        m = re.search(r"(?:0\.2\.?\s*)?[Tt]ype\s*[:\s]*([A-Z][A-Za-z0-9\- ]{1,30})", text)
        if m and not data.get("modele"): data["modele"] = m.group(1).strip()
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
        m = re.search(r"[Ss]oussign[eé]\s*[:\s]*(.{2,50})", text)
        if m: data["soussigne"] = m.group(1).strip()
        m = re.search(r"[Rr]eception\s*(?:par\s*type)?\s*(?:le)?\s*[:\s]*(\d{2}/\d{2}/\d{4})", text)
        if m: data["date_reception"] = m.group(1)
        m = re.search(r"(?:n[.\s]*\(K\)|sous\s*le\s*n[.\s]*)\s*[:\s]*(e\d\*[\d/\*]+\w+)", text)
        if m: data["numero_k"] = m.group(1).strip()
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
        # J Categorie
        m = re.search(r"\bJ\b\s*\n?\s*(L\d[A-Za-z\-]*|M\d|N\d)", text)
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
            warnings.append({
                "code": "NOM_DIVERGENT",
                "message": f"Nom CNI ({nom_cni}) ≠ nom domicile ({nom_domicile})",
                "correction": "Verifier nom de naissance vs nom d'usage",
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

    # ─── 5. CG barree (VO uniquement) ─────────────────────────────────────
    if flow == "VO":
        for d in by_type.get("CG_BARREE", []):
            ext = d.get("extracted_data", {})
            if ext.get("barre_diagonale"):
                infos.append({"code": "CG_BARREE_OK", "message": "CG barree en diagonale - OK"})
            else:
                blocages.append({"code": "CG_NON_BARREE", "message": "CG non barree en diagonale", "correction": "Barrer la CG + noter 'vendu le' + date + heure + signer"})
            if ext.get("date_vente"):
                infos.append({"code": "CG_DATE_VENTE", "message": f"Date de vente sur CG : {ext['date_vente']}"})

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
    # Binaire : VERT (tout ok, Cerfa generable) ou ROUGE (blocage)
    if blocages:
        diagnostic = "ROUGE"
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
        "cerfa_disponible": diagnostic == "VERT",
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

class ProfilProSetup(BaseModel):
    """Parametrage initial du profil pro (une seule fois, a l'installation)."""
    nom_commerce: str                  # Ex: "Moto Center Paris"
    adresse: str                       # Ex: "12 rue de la Moto, 75011 Paris"
    telephone_commerce: str            # Telephone du commerce (affiche dans le SMS)
    email_commerce: str | None = None  # Email du commerce
    # Assurance flotte
    assurance_flotte_vn: bool = False  # Couvre les VN apres vente en attente d'immatriculation ?
    assurance_flotte_vo: bool = False  # Couvre les VO apres vente en attente d'immatriculation ?
    # SIRET et raison sociale extraits automatiquement du Kbis (pas de saisie)
    # Cachet, signature et Kbis uploades separement via endpoints dedies


class DossierCreate(BaseModel):
    client_telephone: str             # Seul champ obligatoire — pour envoyer le lien SMS
    client_email: str | None = None   # Optionnel — lien aussi envoye par email si renseigne


# ─── Profil Pro (in-memory pour la demo) ─────────────────────────────────────

PROFIL_PRO: dict = {}


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.get("/api/health")
def health():
    return {"status": "ok", "version": "0.3.0", "dossiers": len(DOSSIERS)}


@app.get("/api/mentions-legales")
def get_mentions_legales():
    """Retourne les mentions legales, CGU et CGV du service."""
    return {
        "service": {
            "nom": "AutoDoc Pro",
            "description": (
                "AutoDoc Pro est un service d'aide a la constitution de dossiers "
                "de carte grise destine aux professionnels de l'automobile habilites SIV."
            ),
        },
        "cgu": {
            "objet": (
                "AutoDoc Pro fournit un outil de numerisation, d'extraction et de verification "
                "automatique des documents necessaires a la demande d'immatriculation de vehicules. "
                "Le service genere des formulaires Cerfa pre-remplis a partir des documents fournis."
            ),
            "limitation_responsabilite": {
                "outil_aide": (
                    "AutoDoc Pro est un outil d'aide a la constitution de dossier. "
                    "Il ne se substitue ni au professionnel habilite SIV, ni a l'administration "
                    "(ANTS/SIV), ni a un conseiller juridique."
                ),
                "pas_de_garantie_resultat": (
                    "AutoDoc Pro ne garantit pas l'acceptation du dossier par le SIV. "
                    "La decision d'immatriculation releve exclusivement de l'administration."
                ),
                "ocr_approximatif": (
                    "L'extraction automatique des donnees (OCR) est realisee a titre d'aide. "
                    "Les donnees extraites peuvent contenir des erreurs. Le professionnel "
                    "est tenu de verifier l'exactitude des informations avant soumission."
                ),
                "estimation_taxes": (
                    "Les estimations de taxes sont fournies a titre indicatif et ne constituent "
                    "pas un engagement contractuel. Le montant definitif est determine par le SIV."
                ),
                "reglementation": (
                    "Les informations reglementaires (permis requis, etc.) "
                    "sont fournies a titre informatif et peuvent ne pas refleter les dernieres "
                    "evolutions legislatives. Le professionnel est tenu de se conformer "
                    "a la reglementation en vigueur."
                ),
                "indisponibilite": (
                    "AutoDoc Pro ne peut etre tenu responsable des indisponibilites du SIV, "
                    "du site service-public.gouv.fr, ou de tout service tiers."
                ),
            },
            "responsabilites_pro": {
                "veracite_dossier": (
                    "Le professionnel habilite SIV est seul responsable de la veracite "
                    "et de la completude du dossier soumis a l'administration."
                ),
                "verification": (
                    "Le professionnel s'engage a verifier les donnees extraites automatiquement "
                    "avant toute soumission au SIV."
                ),
                "documents_clients": (
                    "Le professionnel s'assure que les documents fournis par ses clients "
                    "sont authentiques et conformes."
                ),
            },
            "responsabilites_client": {
                "authenticite": (
                    "Le client certifie que les documents deposes sont authentiques et le concernent "
                    "personnellement. La fourniture de faux documents constitue un delit "
                    "(articles 441-1 et suivants du Code penal)."
                ),
                "exactitude": (
                    "Le client certifie que les informations contenues dans ses documents "
                    "sont exactes et a jour."
                ),
            },
        },
        "cgv": {
            "tarification": (
                "Le service est facture au professionnel par dossier traite : "
                "12 EUR par dossier moto, 14 EUR par dossier voiture. "
                "Le tarif est fixe et independant du prix facture par le professionnel a son client."
            ),
            "paiement": (
                "Le professionnel peut traiter jusqu'a 5 dossiers en batch. "
                "Le paiement des dossiers en cours est requis avant de pouvoir "
                "traiter de nouveaux dossiers."
            ),
            "non_remboursement": (
                "Les honoraires factures ne sont pas remboursables en cas de rejet du dossier "
                "par le SIV si le rejet est du a des documents incorrects ou incomplets "
                "fournis par le professionnel ou son client."
            ),
            "remboursement": (
                "En cas de dysfonctionnement du service ayant empeche la generation du Cerfa, "
                "le dossier concerne ne sera pas facture."
            ),
        },
        "donnees_personnelles": {
            "responsable": "AutoDoc Pro",
            "finalite": "Constitution de dossiers de demande d'immatriculation de vehicules",
            "base_legale": "Consentement (client) / Execution contractuelle (professionnel)",
            "conservation": {
                "documents_client": "Supprimes a la finalisation du dossier",
                "dossiers_pro": "Archives 5 ans (obligation legale)",
                "donnees_facturation": "Archives 10 ans (obligation comptable)",
            },
            "contact_dpo": "rgpd@cartegrisepro.fr",
            "politique_complete": "cartegrisepro.fr/confidentialite",
        },
    }


# ─── Parametrage profil pro ──────────────────────────────────────────────────

@app.post("/api/profil")
def setup_profil(req: ProfilProSetup):
    """
    Parametrage initial du profil pro (une seule fois, a l'installation).

    Le pro renseigne :
    - Nom du commerce
    - Adresse de la structure
    - Telephone du commerce
    - Email du commerce (optionnel)
    - SIRET (optionnel)

    Cachet et signature sont uploades separement.
    Ces infos sont integrees dans le SMS envoye au client.
    """
    PROFIL_PRO.update({
        "nom_commerce": req.nom_commerce,
        "adresse": req.adresse,
        "telephone_commerce": req.telephone_commerce,
        "email_commerce": req.email_commerce,
        "assurance_flotte_vn": req.assurance_flotte_vn,
        "assurance_flotte_vo": req.assurance_flotte_vo,
        "cachet_path": PROFIL_PRO.get("cachet_path"),
        "signature_path": PROFIL_PRO.get("signature_path"),
        "kbis_path": PROFIL_PRO.get("kbis_path"),
    })
    _update_setup_complete()
    message = "Informations enregistrees."
    if PROFIL_PRO.get("setup_complete"):
        message = "Votre espace est pret ! Vous pouvez creer votre premier dossier."
    return {"status": "ok", "message": message, "profil": PROFIL_PRO}


@app.get("/api/profil")
def get_profil():
    """Retourne le profil pro actuel."""
    if not PROFIL_PRO:
        raise HTTPException(404, "Profil non configure. Utilisez POST /api/profil.")
    return PROFIL_PRO


@app.post("/api/profil/cachet")
async def upload_cachet(file: UploadFile):
    """Upload de la photo du cachet commercial (une seule fois)."""
    file_bytes = await file.read()
    path = UPLOAD_DIR / "profil" / "cachet"
    path.mkdir(parents=True, exist_ok=True)
    filepath = path / (file.filename or "cachet.png")
    with open(filepath, "wb") as f:
        f.write(file_bytes)
    PROFIL_PRO["cachet_path"] = str(filepath)
    _update_setup_complete()
    return {"status": "ok", "cachet_path": str(filepath)}


@app.post("/api/profil/signature")
async def upload_signature(file: UploadFile):
    """Upload de la photo de la signature du pro (une seule fois)."""
    file_bytes = await file.read()
    path = UPLOAD_DIR / "profil" / "signature"
    path.mkdir(parents=True, exist_ok=True)
    filepath = path / (file.filename or "signature.png")
    with open(filepath, "wb") as f:
        f.write(file_bytes)
    PROFIL_PRO["signature_path"] = str(filepath)
    _update_setup_complete()
    return {"status": "ok", "signature_path": str(filepath)}


@app.post("/api/profil/kbis")
async def upload_kbis_pro(file: UploadFile):
    """
    Upload du Kbis du vendeur pro (obligatoire au parametrage).

    Le systeme :
    1. Stocke le fichier
    2. Lance l'OCR (Tesseract → Google DocAI fallback)
    3. Extrait SIREN, raison sociale, adresse siege, date du Kbis
    4. Verifie que le Kbis est valide (date < 3 mois)
    5. Auto-remplit les infos du profil si pas encore renseignees

    Usage : identification du pro, responsabilite juridique, facturation.
    Ne sert PAS pour le Cerfa (le Cerfa utilise le SIREN du client si PM).
    """
    file_bytes = await file.read()

    # Stocker
    path = UPLOAD_DIR / "profil" / "kbis"
    path.mkdir(parents=True, exist_ok=True)
    filepath = path / (file.filename or "kbis.pdf")
    with open(filepath, "wb") as f:
        f.write(file_bytes)

    # OCR avec fallback
    mime = file.content_type or "application/pdf"
    raw_text = ""
    ocr_confidence = 0.0

    try:
        tess = _ocr_tesseract(file_bytes, mime)
        raw_text = tess["text"]
        ocr_confidence = tess["confidence"]
    except Exception:
        pass

    if ocr_confidence < 0.40 or len(raw_text.strip()) < 50:
        try:
            goo = _ocr_google_docai(file_bytes, mime)
            if goo["confidence"] > ocr_confidence:
                raw_text = goo["text"]
                ocr_confidence = goo["confidence"]
        except Exception:
            pass

    # Extraire les infos du Kbis
    kbis_extracted = extract_data("KBIS", raw_text)

    # Verifier la date du Kbis (< 3 mois)
    kbis_warning = None
    date_kbis = kbis_extracted.get("date_kbis") or kbis_extracted.get("date_document")
    if date_kbis:
        try:
            from datetime import timedelta
            date_obj = datetime.strptime(date_kbis, "%d/%m/%Y")
            if (datetime.utcnow() - date_obj) > timedelta(days=90):
                kbis_warning = (
                    f"Kbis date du {date_kbis} (plus de 3 mois). "
                    "Un Kbis de moins de 3 mois est recommande."
                )
        except (ValueError, TypeError):
            pass

    # Sauvegarder dans le profil
    PROFIL_PRO["kbis_path"] = str(filepath)
    PROFIL_PRO["kbis_ocr_confidence"] = ocr_confidence
    PROFIL_PRO["kbis_extracted"] = kbis_extracted
    PROFIL_PRO["kbis_warning"] = kbis_warning

    # Auto-remplir SIREN et raison sociale depuis le Kbis
    if kbis_extracted.get("siren"):
        PROFIL_PRO["siret"] = kbis_extracted["siren"]
    if kbis_extracted.get("raison_sociale"):
        PROFIL_PRO["raison_sociale"] = kbis_extracted["raison_sociale"]
    # Auto-remplir adresse depuis le Kbis si pas encore renseignee
    if not PROFIL_PRO.get("adresse") and kbis_extracted.get("adresse"):
        PROFIL_PRO["adresse"] = kbis_extracted["adresse"]

    _update_setup_complete()

    result = {
        "status": "ok",
        "kbis_path": str(filepath),
        "ocr_confidence": ocr_confidence,
        "extracted": kbis_extracted,
    }
    if kbis_warning:
        result["warning"] = kbis_warning

    return result


def _update_setup_complete():
    """Met a jour le flag setup_complete du profil pro."""
    PROFIL_PRO["setup_complete"] = bool(
        PROFIL_PRO.get("nom_commerce")
        and PROFIL_PRO.get("adresse")
        and PROFIL_PRO.get("telephone_commerce")
        and PROFIL_PRO.get("cachet_path")
        and PROFIL_PRO.get("signature_path")
        and PROFIL_PRO.get("kbis_path")
    )


# ─── Dossiers ────────────────────────────────────────────────────────────────

@app.post("/api/dossiers")
def create_dossier(req: DossierCreate):
    # Le pro ne peut pas creer de dossier si son profil n'est pas complet
    profil_required = ["nom_commerce", "adresse", "telephone_commerce", "cachet_path", "signature_path", "kbis_path"]
    profil_manquants = [f for f in profil_required if not PROFIL_PRO.get(f)]
    if profil_manquants:
        raise HTTPException(422, detail={
            "error": "profil_incomplet",
            "message": "Bienvenue ! Pour commencer, prenez un instant pour completer votre profil — c'est rapide et ca nous permettra de bien preparer vos dossiers.",
            "manquants": profil_manquants,
        })

    dossier_id = str(uuid.uuid4())
    ref = f"CG-2026-{len(DOSSIERS) + 1:05d}"
    dossier = {
        "id": dossier_id,
        "reference": ref,
        # Saisi par le pro
        "client_telephone": req.client_telephone,
        "client_email": req.client_email,
        # Deduit automatiquement des documents
        "type": None,                # VN ou VO — deduit apres upload (CG barree=VO, COC+Facture=VN)
        "vin": None,                 # Extrait du COC (VN) ou CG barree (VO)
        "immatriculation": None,     # Extraite de la CG barree (VO)
        "client_nom": None,          # Extrait de la facture (VN) ou CG barree (VO)
        "client_prenom": None,       # Idem
        "client_sexe": None,         # Deduit du prenom (CNI)
        # Renseigne par le client (pas par le pro)
        "is_personne_morale": False, # Le client indique s'il est PM dans sa page d'upload
        "co_titulaire": None,        # Le client renseigne le co-titulaire dans sa page d'upload
        # Statut
        "status": "PENDING",
        "diagnostic": None,
        "blocages": [],
        "warnings": [],
        "infos": [],
        "tax_estimate": None,
        "documents_vendeur": [],
        "documents_client": [],
        "documents": [],
        "cerfa_pdf": None,
        "cerfa_generated_at": None,
        # Cachet + signature pro apposes automatiquement a la generation du Cerfa
        "messages_admin": [],
        "created_at": datetime.utcnow().isoformat(),
    }
    DOSSIERS[dossier_id] = dossier

    # Reponse avec la liste des docs a deposer (VN et VO presentes)
    return {
        **dossier,
        "message": "Dossier cree ! Deposez vos documents vehicule pour commencer.",
        "instruction": (
            "Le systeme detectera automatiquement s'il s'agit d'un VN ou VO."
        ),
        "docs_attendus": {
            "vn": [
                {"type": "COC", "label": "Certificat de Conformite (COC)", "obligatoire": True},
                {"type": "FACTURE", "label": "Facture de vente", "obligatoire": True},
            ],
            "vo": [
                {"type": "CG_BARREE", "label": "Carte grise barree", "obligatoire": True},
                {"type": "COC", "label": "COC (recommande, complete les infos techniques)", "obligatoire": False},
            ],
        },
    }


@app.get("/api/dossiers")
def list_dossiers():
    return list(DOSSIERS.values())


@app.get("/api/dossiers/{dossier_id}")
def get_dossier(dossier_id: str):
    d = DOSSIERS.get(dossier_id)
    if not d:
        raise HTTPException(404, "Dossier non trouve")
    return d


@app.post("/api/dossiers/{dossier_id}/upload")
async def upload_document(
    dossier_id: str,
    file: UploadFile,
    source: str = "vendeur",
    captured_by_camera: bool = False,
):
    """
    Upload un document. source = 'vendeur' ou 'client'.
    captured_by_camera = True si le doc a ete pris en photo directement (pas un fichier existant).
    Le vendeur depose : COC, CG barree, facture
    Le client depose : CNI, permis, justificatif domicile
    """
    dossier = DOSSIERS.get(dossier_id)
    if not dossier:
        raise HTTPException(404, "Dossier non trouve")

    # Verrou RGPD : le client doit avoir accepte le consentement avant de deposer
    if source == "client" and not dossier.get("client_rgpd_consent"):
        raise HTTPException(403, detail={
            "error": "consentement_requis",
            "message": (
                "Vous devez accepter les conditions de traitement de vos donnees "
                "avant de deposer vos documents."
            ),
        })

    # Verrou CPI : le client doit avoir choisi son mode de reception du CPI
    if source == "client" and not dossier.get("cpi_mode_reception"):
        raise HTTPException(403, detail={
            "error": "choix_cpi_requis",
            "message": (
                "Choisissez d'abord comment vous souhaitez recevoir votre "
                "Certificat d'Immatriculation Provisoire (CPI) : par email ou en main propre."
            ),
        })

    # Verrou cession : si la cession a ete signee mais pas encore telechargee, bloquer les uploads
    if source == "client" and dossier.get("cession_signee_client") and not dossier.get("cession_client_telechargee"):
        raise HTTPException(403, detail={
            "error": "telechargement_cession_requis",
            "message": (
                "Vous devez telecharger votre exemplaire du certificat de cession "
                "avant de pouvoir continuer. Ce document est obligatoire."
            ),
            "telechargement_url": f"/api/client/{dossier.get('client_link_token', '')}/telecharger-cession",
        })

    # Filtrer les fichiers systeme
    fname = file.filename or ""
    if fname.startswith(".") or fname in (".DS_Store", "Thumbs.db", "desktop.ini"):
        raise HTTPException(422, f"Fichier systeme ignore : {fname}")

    file_bytes = await file.read()
    if len(file_bytes) == 0:
        raise HTTPException(422, "Fichier vide")
    if len(file_bytes) > 10 * 1024 * 1024:
        raise HTTPException(422, "Fichier > 10 MB")

    doc_id = str(uuid.uuid4())
    sha = hashlib.sha256(file_bytes).hexdigest()

    # Store
    doc_path = UPLOAD_DIR / dossier_id
    doc_path.mkdir(parents=True, exist_ok=True)
    with open(doc_path / f"{doc_id}_{file.filename}", "wb") as f:
        f.write(file_bytes)

    # OCR : Tesseract puis Google DocAI en fallback si illisible
    # Seuils : < 40% = illisible, < 70% = avertissement, >= 70% = ok
    OCR_SEUIL_ILLISIBLE = 0.40
    OCR_SEUIL_AVERTISSEMENT = 0.70

    raw_text = ""
    ocr_confidence = 0.0
    ocr_provider_used = "none"
    mime = file.content_type or ""

    if mime in ("application/pdf", "image/jpeg", "image/png", "image/tiff", "image/webp"):
        # 1. Tesseract (gratuit, local)
        try:
            tess = _ocr_tesseract(file_bytes, mime)
            raw_text = tess["text"]
            ocr_confidence = tess["confidence"]
            ocr_provider_used = "tesseract"
            logger.info(f"OCR Tesseract: {len(raw_text)} chars, confidence={ocr_confidence:.0%}")
        except Exception as e:
            logger.warning(f"OCR Tesseract echoue: {e}")

        # 2. Si Tesseract illisible ou inutilisable -> Google DocAI
        # Fallback si : confidence < 50% OU texte trop court OU le texte n'est
        # pas classifiable (signe que l'OCR a produit du bruit, pas du vrai texte)
        _test_type, _test_conf, _ = classify_document(raw_text)
        tesseract_unusable = (
            ocr_confidence < 0.50
            or len(raw_text.strip()) < 50
            or (_test_type == "AUTRE" and _test_conf == 0.0)
        )
        if tesseract_unusable:
            try:
                goo = _ocr_google_docai(file_bytes, mime)
                if goo["confidence"] > ocr_confidence:
                    raw_text = goo["text"]
                    ocr_confidence = goo["confidence"]
                    ocr_provider_used = "google_docai"
                    logger.info(f"OCR Google DocAI (fallback): {len(raw_text)} chars, confidence={ocr_confidence:.0%}")
            except Exception as e:
                logger.warning(f"OCR Google DocAI echoue: {e}")
    else:
        try:
            raw_text = file_bytes.decode("utf-8", errors="ignore")
            ocr_confidence = 0.95
            ocr_provider_used = "text"
        except Exception:
            pass

    # Statut qualite (affiche dans l'espace de depot)
    # Compter les tentatives pour ce type de doc (escalade progressive)
    source_docs = dossier.get(f"documents_{source}", [])
    tentatives_type = sum(1 for d in source_docs if d.get("type") == doc_type) if doc_type != "AUTRE" else 0
    via_fichier = not captured_by_camera

    if ocr_confidence < OCR_SEUIL_ILLISIBLE:
        quality_status = "illisible"
        # Escalade progressive selon les tentatives et le mode de depot
        if via_fichier and tentatives_type == 0:
            quality_message = "Document difficile a lire. Essayez de le prendre en photo directement."
        elif via_fichier:
            quality_message = "Le fichier n'est toujours pas lisible. Prenez le document en photo avec un bon eclairage."
        elif tentatives_type <= 1:
            quality_message = "La photo n'est pas assez nette. Assurez-vous que le document est bien eclaire et a plat."
        else:
            quality_message = "Si le probleme persiste, contactez votre vendeur pour trouver une solution."
    elif ocr_confidence < OCR_SEUIL_AVERTISSEMENT:
        quality_status = "avertissement"
        quality_message = (
            f"Qualite moyenne — les donnees ont ete extraites mais des erreurs sont possibles. "
            "Vous pouvez re-deposer un document plus net si vous le souhaitez."
        )
    else:
        quality_status = "ok"
        quality_message = None

    # Classify + extract
    doc_type, confidence, keywords = classify_document(raw_text)
    extracted = extract_data(doc_type, raw_text)

    # Si illisible, marquer comme REJECTED (pas EXTRACTED)
    doc_status = "REJECTED" if quality_status == "illisible" else "EXTRACTED"

    doc = {
        "id": doc_id,
        "filename": file.filename,
        "type": doc_type,
        "source": source,
        "classification_confidence": confidence,
        "matched_keywords": keywords,
        "extracted_data": extracted,
        "ocr_text": raw_text,
        "ocr_confidence": ocr_confidence,
        "ocr_provider": ocr_provider_used,
        "status": doc_status,
        "size_bytes": len(file_bytes),
        "captured_by_camera": captured_by_camera,
        # Feedback qualite temps reel pour l'espace de depot
        "quality": {
            "status": quality_status,
            "confidence": ocr_confidence,
            "message": quality_message,
            "provider": ocr_provider_used,
        },
    }

    # ─── Anti-doublon : si meme type deja present dans la meme source, fusionner ───
    source_list = dossier["documents_client"] if source == "client" else dossier["documents_vendeur"]
    existing = None
    for d_existing in source_list:
        if d_existing["type"] == doc_type:
            existing = d_existing
            break

    if existing:
        # Fusion recto/verso : concatener le texte OCR et re-extraire
        merged_text = existing.get("ocr_text", "") + "\n" + raw_text
        merged_extracted = extract_data(doc_type, merged_text)
        # Garder les valeurs non-vides de chaque cote
        for k, v in merged_extracted.items():
            if v and not existing["extracted_data"].get(k):
                existing["extracted_data"][k] = v
        existing["ocr_text"] = merged_text
        existing["filename"] = f"{existing['filename']} + {file.filename}"
        existing["status"] = "MERGED"
        logger.info(f"Fusion recto/verso: {doc_type} ({existing['filename']})")
        doc = existing  # Retourner le doc fusionne
    else:
        # Nouveau document
        source_list.append(doc)

    # Reconstruire la liste fusionnee (sans doublon)
    dossier["documents"] = dossier["documents_vendeur"] + dossier["documents_client"]

    # ─── Detection auto VN/VO + extraction infos dossier (si upload vendeur) ───
    if source == "vendeur":
        _auto_detect_dossier_type(dossier)
        _auto_extract_dossier_fields(dossier)

    # ─── Checklist temps reel selon la source ───
    if source == "vendeur":
        checklist = _check_pro_docs(dossier)
        doc["pro_docs_checklist"] = checklist

        # Recapitulatif a valider si tout est pret
        if checklist["client_link_ready"]:
            doc["recapitulatif_validation"] = _build_recap_validation(dossier)
    elif source == "client":
        _auto_extract_client_fields(dossier)
        checklist_client = _check_client_docs(dossier)
        doc["client_docs_checklist"] = checklist_client

        # Recapitulatif si tous les docs sont deposes et valides (mais PAS encore envoyes)
        if checklist_client.get("ready_for_diagnostic") and not dossier.get("client_docs_envoyes"):
            nom_commerce = PROFIL_PRO.get("nom_commerce", "votre vendeur")

            # Liste des docs deposes pour le recap
            docs_deposes_recap = []
            for dc in dossier.get("documents_client", []):
                if dc.get("status") in ("EXTRACTED", "MERGED"):
                    docs_deposes_recap.append({
                        "type": dc.get("type"),
                        "filename": dc.get("filename"),
                    })

            # Extraire l'adresse du justificatif de domicile
            adresse_domicile = None
            for dc in dossier.get("documents_client", []):
                if dc.get("type", "").upper() == "DOMICILE":
                    ext_dom = dc.get("extracted_data", {})
                    parts = []
                    if ext_dom.get("adresse_ligne1") or ext_dom.get("nom_titulaire"):
                        parts.append(ext_dom.get("adresse_ligne1", ""))
                    if ext_dom.get("code_postal") and ext_dom.get("ville"):
                        parts.append(f"{ext_dom['code_postal']} {ext_dom['ville']}")
                    if parts:
                        adresse_domicile = ", ".join(p for p in parts if p)
                    break

            doc["recapitulatif_envoi"] = {
                "pret": True,
                "message": (
                    "Tous vos documents sont deposes et valides. "
                    f"Verifiez la liste ci-dessous puis confirmez l'envoi a {nom_commerce}."
                ),
                "documents_deposes": docs_deposes_recap,
                "info_adresse": {
                    "message": (
                        "Votre carte grise definitive sera envoyee par courrier securise "
                        "a l'adresse figurant sur votre justificatif de domicile. "
                        "C'est cette adresse qui sera inscrite sur votre certificat d'immatriculation."
                    ),
                    "adresse_extraite": adresse_domicile,
                    "alerte": (
                        "Si cette adresse n'est pas correcte, remplacez votre "
                        "justificatif de domicile avant de confirmer l'envoi."
                    ) if adresse_domicile else (
                        "L'adresse de votre justificatif de domicile n'a pas pu etre lue. "
                        "Verifiez que le document est lisible."
                    ),
                },
                "confirmation_requise": True,
                "texte_confirmation": (
                    f"Je confirme l'envoi de mes documents a {nom_commerce} "
                    "pour le traitement de ma demande de carte grise."
                ),
                "envoi_auto": False,
            }

    return doc


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
                "AutoDoc Pro est un outil d'aide a la constitution du dossier et ne se "
                "substitue pas a votre obligation de verification."
            ),
            "verification_ocr": (
                "Les donnees extraites automatiquement des documents (OCR) peuvent contenir "
                "des erreurs. Il vous appartient de verifier les informations avant toute "
                "soumission au SIV. AutoDoc Pro ne peut etre tenu responsable des erreurs "
                "d'extraction."
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
                "AutoDoc Pro ne garantit pas l'acceptation du dossier par le SIV. "
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
    Deduit automatiquement VN ou VO a partir des documents deposes par le pro.

    - CG barrée detectee → VO (vehicule occasion)
    - COC + Facture detectes → VN (vehicule neuf)
    - COC seul → indetermine (peut etre VN ou VO)
    """
    doc_types = {d.get("type", "").upper() for d in dossier.get("documents_vendeur", [])}

    if "CG_BARREE" in doc_types:
        dossier["type"] = "VO"
    elif "COC" in doc_types and "FACTURE" in doc_types:
        dossier["type"] = "VN"
    elif "FACTURE" in doc_types:
        # Facture seule → probablement VN (le COC manque encore)
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

        # Nom/prenom client depuis facture (VN) ou CG barree (VO)
        if dtype == "FACTURE":
            if not dossier.get("client_nom") and ext.get("acheteur_nom"):
                dossier["client_nom"] = ext["acheteur_nom"]
            if not dossier.get("client_prenom") and ext.get("acheteur_prenom"):
                dossier["client_prenom"] = ext["acheteur_prenom"]
        elif dtype == "CG_BARREE":
            if not dossier.get("client_nom") and ext.get("titulaire_nom"):
                dossier["client_nom"] = ext["titulaire_nom"]
            if not dossier.get("client_prenom") and ext.get("titulaire_prenom"):
                dossier["client_prenom"] = ext["titulaire_prenom"]


def _auto_extract_client_fields(dossier: dict) -> None:
    """
    Extrait automatiquement les infos du client depuis ses documents :
    - Sexe deduit du prenom (CNI)
    - Detection personne morale (si Kbis uploade)
    """
    for d in dossier.get("documents_client", []):
        ext = d.get("extracted_data", {})
        if not ext:
            continue

        dtype = d.get("type", "").upper()

        # Deduire le sexe depuis le prenom de la CNI
        if dtype in ("CNI", "PASSEPORT") and not dossier.get("client_sexe"):
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
    is_vo = dossier.get("type", "").upper() in ("VO", "OCCASION")
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

        doc_items.append({
            "id": f"doc_{dtype.lower()}",
            "label": dtype,
            "filename": d.get("filename"),
            "status": doc_status,
            "quality": quality,
            "action": action,
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
        "client_link_ready": all_ok,
        "blocages": [
            item for section in [info_items, doc_items, missing_docs]
            for item in section
            if item["status"] in ("manquant", "illisible")
        ],
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

        checklist.append({
            "type": dtype,
            "filename": d.get("filename"),
            "status": doc_status,
            "quality": quality,
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

    # Tous les docs requis presents et lisibles ?
    all_required_ok = all(
        any(c["type"] in (req, "PASSEPORT") and c["status"] == "ok" for c in checklist)
        if req == "CNI"
        else any(c["type"] == req and c["status"] == "ok" for c in checklist)
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

    return {
        "documents_attendus": docs_attendus,
        "documents": checklist,
        "missing": missing,
        "has_illisible": has_illisible,
        "all_required_ok": all_required_ok,
        "ready_for_diagnostic": all_required_ok and not has_illisible,
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

    # Docs pro
    if pro_status["has_illisible"]:
        illisibles = [d["filename"] for d in pro_status["documents"] if d["status"] == "illisible"]
        reasons.append(f"Document(s) vendeur illisible(s) : {', '.join(illisibles)}")
    if pro_status["missing"]:
        manquants = [m["label"] for m in pro_status["missing"] if m["required"]]
        if manquants:
            reasons.append(f"Document(s) vendeur manquant(s) : {', '.join(manquants)}")

    # Docs client
    if client_status["has_illisible"]:
        illisibles = [d["filename"] for d in client_status["documents"] if d["status"] == "illisible"]
        reasons.append(f"Document(s) client illisible(s) : {', '.join(illisibles)}")
    if client_status["missing"]:
        manquants = [m["label"] for m in client_status["missing"] if m["required"]]
        if manquants:
            reasons.append(f"Document(s) client manquant(s) : {', '.join(manquants)}")

    blocked = len(reasons) > 0

    return {
        "blocked": blocked,
        "reasons": reasons,
        "pro_status": pro_status,
        "client_status": client_status,
    }


@app.get("/api/dossiers/{dossier_id}/checklist")
def get_checklist(dossier_id: str):
    """
    Checklist interactive consultable a tout moment par le pro.
    Retourne l'etat complet : profil, info client, documents, blocages.
    """
    dossier = DOSSIERS.get(dossier_id)
    if not dossier:
        raise HTTPException(404, "Dossier non trouve")

    return _check_pro_docs(dossier)


@app.post("/api/dossiers/{dossier_id}/pas-de-cession")
def toggle_pas_de_cession(dossier_id: str):
    """
    Le pro coche 'pas de certificat de cession'.
    Dans ce cas, le systeme generera le certificat de cession
    et le client devra le signer via lien SMS + OTP.
    """
    dossier = DOSSIERS.get(dossier_id)
    if not dossier:
        raise HTTPException(404, "Dossier non trouve")

    dossier["pas_de_certificat_cession"] = True

    return {
        "status": "ok",
        "message": (
            "Le certificat de cession sera genere par le systeme. "
            "Le client devra le signer numeriquement via le lien SMS (signature au doigt + OTP)."
        ),
        "signature_client_requise": True,
    }


class ChoixAssurance(BaseModel):
    assurance_flotte_couvre: bool       # Q1 : votre flotte couvre ce vehicule ?
    demander_client: bool | None = None  # Q2 : demander au client ? (seulement si Q1 = non)


@app.post("/api/dossiers/{dossier_id}/choix-assurance")
def choix_assurance_dossier(dossier_id: str, choix: ChoixAssurance):
    """
    Le pro repond aux questions assurance pour ce dossier.

    Q1 : "Avez-vous une assurance flotte qui couvre le vehicule vendu
          au client en attendant la validation au SIV ?"
    - OUI → pas d'attestation demandee au client

    Q2 (si Q1 = NON) : "Souhaitez-vous que l'on demande a votre client
                         son attestation d'assurance ?"
    - OUI → attestation ajoutee dans la checklist client
    - NON → pas d'attestation dans la checklist client
    """
    dossier = DOSSIERS.get(dossier_id)
    if not dossier:
        raise HTTPException(404, "Dossier non trouve")

    dossier["assurance_flotte_couvre"] = choix.assurance_flotte_couvre
    dossier["choix_assurance_pro"] = True

    if choix.assurance_flotte_couvre:
        dossier["demander_assurance_client"] = False
        return {
            "status": "ok",
            "message": "Votre assurance flotte couvre ce vehicule — pas besoin de demander une attestation au client. Une chose de moins a gerer !",
        }
    else:
        if choix.demander_client is None:
            raise HTTPException(422, "Repondez a la question 2 : souhaitez-vous demander l'attestation au client ?")

        dossier["demander_assurance_client"] = choix.demander_client

        if choix.demander_client:
            return {
                "status": "ok",
                "message": (
                    "C'est note ! L'attestation d'assurance sera demandee a votre client. "
                    "De notre cote, on verifiera que c'est bien une assurance auto "
                    "et que le nom correspond au dossier."
                ),
                "info": (
                    "Pensez a verifier vous-meme que l'assurance couvre bien le vehicule "
                    "avant de soumettre au SIV — c'est un point que vous maitrisez mieux que nous !"
                ),
            }
        else:
            return {
                "status": "ok",
                "message": "Bien note ! Aucune attestation d'assurance ne sera demandee au client — vous gerez ca directement de votre cote.",
            }


@app.post("/api/dossiers/{dossier_id}/confirm-send-link")
def confirm_send_client_link(dossier_id: str):
    """
    Le pro confirme l'envoi du lien securise au client.

    Appele apres que le pro a verifie le recapitulatif et coche la case de validation.
    Le lien ne part JAMAIS automatiquement — c'est toujours une action explicite du pro.
    """
    dossier = DOSSIERS.get(dossier_id)
    if not dossier:
        raise HTTPException(404, "Dossier non trouve")

    # Verifier que les docs pro sont complets et lisibles
    checklist = _check_pro_docs(dossier)
    if not checklist["client_link_ready"]:
        raise HTTPException(422, detail={
            "error": "docs_pro_incomplets",
            "message": "Il nous manque encore quelques documents, ou certains ne sont pas tout a fait lisibles. Un petit ajustement et on est bons !",
            "checklist": checklist,
        })

    # Verifier que le profil pro est configure
    if not PROFIL_PRO.get("nom_commerce"):
        raise HTTPException(422, detail={
            "error": "profil_non_configure",
            "message": "Bienvenue ! Pour demarrer, configurez votre espace en renseignant le nom et l'adresse de votre structure — ca ne prend qu'une minute.",
        })

    # Generer le lien securise pour le client
    import secrets
    client_token = secrets.token_urlsafe(32)
    dossier["client_link_token"] = client_token
    dossier["client_link_sent"] = True
    dossier["client_link_sent_at"] = datetime.utcnow().isoformat()
    dossier["status"] = "ATTENTE_CLIENT"

    client_link = f"/client/{client_token}"

    # Generer le SMS personnalise avec les infos du commerce
    nom_commerce = PROFIL_PRO.get("nom_commerce", "")
    adresse = PROFIL_PRO.get("adresse", "")
    tel_commerce = PROFIL_PRO.get("telephone_commerce", "")
    client_prenom = dossier.get("client_prenom", "")

    sms_message = (
        f"Bonjour{' ' + client_prenom if client_prenom else ''}, "
        f"{nom_commerce} a choisi AutoDoc Pro pour votre carte grise. "
        f"Deposez gratuitement vos documents ici : {{LIEN}} "
        f"Infos & confidentialite : cartegrisepro.fr/confidentialite — "
        f"Contact : {nom_commerce} au {tel_commerce}"
    )

    dossier["sms_message"] = sms_message

    # En prod : envoi SMS via Twilio/OVH + email
    logger.info(
        f"[Lien client] Dossier {dossier_id} — SMS envoye au {dossier.get('client_telephone')}"
    )
    logger.info(f"[SMS] {sms_message.replace('{LIEN}', client_link)}")

    return {
        "status": "lien_envoye",
        "message": (
            f"Le lien securise a ete envoye au {dossier.get('client_telephone', '?')}."
        ),
        "sms_envoye": sms_message.replace("{LIEN}", client_link),
        "client_link": client_link,
        "sent_to": {
            "telephone": dossier.get("client_telephone"),
            "email": dossier.get("client_email"),
        },
        "commerce": {
            "nom": nom_commerce,
            "adresse": adresse,
            "telephone": tel_commerce,
        },
        "sent_at": dossier["client_link_sent_at"],
    }


# ─── Page client (lien securise recu par SMS) ────────────────────────────────

@app.get("/api/client/{token}")
def get_client_upload_page(token: str):
    """
    Page d'upload client accessible via le lien securise SMS.

    Retourne toutes les infos necessaires pour afficher la page :
    - Infos du commerce (pour que le client sache d'ou ca vient)
    - Mentions RGPD completes (article 13 RGPD)
    - Checklist des documents a deposer
    - Statut du consentement
    """
    # Trouver le dossier correspondant au token
    dossier = None
    for d in DOSSIERS.values():
        if d.get("client_link_token") == token:
            dossier = d
            break
    if not dossier:
        raise HTTPException(404, "Lien invalide ou expire")

    # Lien desactive apres generation du Cerfa
    if dossier.get("status") in ("CERFA_GENERE", "SIGNE", "SOUMIS"):
        nom_commerce = PROFIL_PRO.get("nom_commerce", "votre vendeur")
        tel_commerce = PROFIL_PRO.get("telephone_commerce", "")
        return {
            "status": "termine",
            "message": (
                "Merci, vos documents ont bien ete transmis. "
                f"Votre dossier de carte grise est en cours de finalisation par {nom_commerce}."
            ),
            "prochaines_etapes": [
                {
                    "etape": 1,
                    "description": (
                        f"{nom_commerce} va soumettre votre dossier aupres de l'administration (SIV)."
                    ),
                },
                {
                    "etape": 2,
                    "description": (
                        f"{nom_commerce} vous remettra votre Certificat d'Immatriculation "
                        "Provisoire (CPI) en main propre ou par email. "
                        "Ce document vous permet de circuler pendant 1 mois."
                    ),
                },
                {
                    "etape": 3,
                    "description": (
                        "Vous recevrez votre carte grise definitive par courrier securise "
                        "(lettre suivie de l'Imprimerie Nationale) a l'adresse indiquee "
                        "sur votre justificatif de domicile, sous 3 a 7 jours ouvrables."
                    ),
                },
            ],
            "contact": (
                f"Pour toute question sur l'avancement de votre dossier, "
                f"contactez {nom_commerce}"
                + (f" au {tel_commerce}" if tel_commerce else "")
                + "."
            ),
        }

    is_vo = dossier.get("type", "").upper() in ("VO", "OCCASION")

    # Precalcul checklist et docs attendus
    docs_attendus = _get_client_docs_attendus(dossier)
    checklist_client = _check_client_docs(dossier)

    return {
        "dossier_id": dossier["id"],
        "reference": dossier.get("reference"),
        "type": dossier.get("type"),
        # Infos commerce (pour le header de la page)
        "commerce": {
            "nom": PROFIL_PRO.get("nom_commerce"),
            "adresse": PROFIL_PRO.get("adresse"),
            "telephone": PROFIL_PRO.get("telephone_commerce"),
        },
        # Mentions RGPD obligatoires (affichees avant le premier upload)
        "rgpd": {
            "responsable": "AutoDoc Pro",
            "finalite": (
                "Vos documents sont collectes uniquement pour le traitement "
                "de votre demande d'immatriculation vehicule (carte grise) "
                f"initiee par {PROFIL_PRO.get('nom_commerce', 'votre vendeur')}."
            ),
            "base_legale": "Consentement (article 6.1.a du RGPD)",
            "destinataires": (
                f"Vos documents sont transmis a {PROFIL_PRO.get('nom_commerce', 'votre vendeur')} "
                "et traites par AutoDoc Pro pour la preparation du dossier de carte grise."
            ),
            "conservation": (
                "Vos documents sont conserves uniquement le temps de la demarche "
                "et supprimes automatiquement une fois le dossier finalise."
            ),
            "droits": (
                "Vous disposez d'un droit d'acces, de rectification, de suppression, "
                "de portabilite et d'opposition sur vos donnees personnelles. "
                "Pour exercer vos droits : rgpd@cartegrisepro.fr"
            ),
            "contact_dpo": "rgpd@cartegrisepro.fr",
            "politique_complete": "cartegrisepro.fr/confidentialite",
        },
        # Consentement obligatoire (le client doit cocher avant le premier upload)
        "consentement": {
            "requis": True,
            "accepte": dossier.get("client_rgpd_consent", False),
            "texte": (
                "J'accepte que mes documents d'identite soient traites par AutoDoc Pro "
                f"et transmis a {PROFIL_PRO.get('nom_commerce', 'mon vendeur')} "
                "dans le seul but de realiser ma demande de carte grise. "
                "J'ai pris connaissance de la politique de confidentialite."
            ),
        },
        # Mentions legales client
        "mentions_legales": {
            "authenticite": (
                "En deposant vos documents, vous certifiez qu'ils sont authentiques "
                "et vous concernent personnellement. La fourniture de faux documents "
                "constitue un delit passible de sanctions penales "
                "(articles 441-1 et suivants du Code penal)."
            ),
            "exactitude": (
                "Vous certifiez que les informations contenues dans vos documents "
                "sont exactes et a jour. Toute erreur ou omission pourrait entrainer "
                "le rejet de votre demande d'immatriculation."
            ),
            "role_service": (
                "AutoDoc Pro est un service d'aide a la constitution de dossier "
                "de carte grise. Il ne se substitue ni a un conseiller juridique, "
                "ni a l'administration (SIV/ANTS). Les informations reglementaires "
                "affichees sont fournies a titre indicatif."
            ),
            "responsabilite": (
                f"La soumission du dossier aupres de l'administration est effectuee "
                f"par {PROFIL_PRO.get('nom_commerce', 'votre vendeur')} sous sa propre "
                f"responsabilite. AutoDoc Pro ne garantit pas l'acceptation du dossier par le SIV."
            ),
            "conservation": (
                "Vos documents sont conserves uniquement le temps necessaire au traitement "
                "de votre demande et sont supprimes automatiquement une fois le dossier finalise, "
                "conformement a notre politique de confidentialite."
            ),
        },
        # Choix mode de reception du CPI (obligatoire avant upload)
        "choix_cpi": {
            "requis": True,
            "choisi": dossier.get("cpi_mode_reception") is not None,
            "mode": dossier.get("cpi_mode_reception"),  # "email" ou "main_propre"
            "email_client": dossier.get("cpi_email"),
            "options": [
                {
                    "id": "main_propre",
                    "label": "Je recupererai mon CPI en main propre aupres de "
                             + PROFIL_PRO.get("nom_commerce", "mon vendeur"),
                },
                {
                    "id": "email",
                    "label": "Je souhaite recevoir mon CPI par email",
                    "champ_email_requis": True,
                },
            ],
        },
        # Signature cession (VO, si pas de cession deposee par le pro)
        "cession": {
            "signature_requise": bool(
                dossier.get("pas_de_certificat_cession")
                and dossier.get("type", "").upper() in ("VO", "OCCASION")
            ),
            "signee": dossier.get("cession_signee_client", False),
            "telechargee": dossier.get("cession_client_telechargee", False),
        },
        # Documents a deposer
        "documents_attendus": docs_attendus,
        # Intro checklist
        "intro_checklist": (
            f"Voici les documents dont nous avons besoin. Ca prend 2-3 minutes."
        ),
        # Checklist actuelle
        "checklist": checklist_client,
        # Reprise de session
        "session": _build_session_message(dossier, checklist_client),
    }


@app.post("/api/client/{token}/consent")
def accept_rgpd_consent(token: str):
    """
    Le client accepte le consentement RGPD.
    Doit etre appele AVANT le premier upload de document.
    """
    dossier = None
    for d in DOSSIERS.values():
        if d.get("client_link_token") == token:
            dossier = d
            break
    if not dossier:
        raise HTTPException(404, "Lien invalide ou expire")

    dossier["client_rgpd_consent"] = True
    dossier["client_rgpd_consent_at"] = datetime.utcnow().isoformat()

    return {
        "status": "ok",
        "message": "Merci pour votre consentement ! Vous pouvez maintenant deposer vos documents en toute tranquillite.",
        "consent_at": dossier["client_rgpd_consent_at"],
    }


@app.delete("/api/client/{token}/document/{doc_type}")
def supprimer_document_client(token: str, doc_type: str):
    """
    Le client supprime un document depose pour le remplacer.
    Le document est retire de la liste et le client peut en deposer un nouveau.
    Bloque si les documents ont deja ete envoyes (confirmes).
    """
    dossier = None
    for d in DOSSIERS.values():
        if d.get("client_link_token") == token:
            dossier = d
            break
    if not dossier:
        raise HTTPException(404, "Lien invalide ou expire")

    # Bloquer si deja envoye
    if dossier.get("client_docs_envoyes"):
        raise HTTPException(422, detail={
            "error": "docs_deja_envoyes",
            "message": "Vos documents ont bien ete transmis, tout est en ordre de ce cote. Pour toute modification, n'hesitez pas a contacter votre vendeur.",
        })

    # Trouver et supprimer le document
    docs_client = dossier.get("documents_client", [])
    doc_type_upper = doc_type.upper()
    found = False

    for i, dc in enumerate(docs_client):
        if dc.get("type", "").upper() == doc_type_upper:
            docs_client.pop(i)
            found = True
            break

    if not found:
        raise HTTPException(404, f"Document de type '{doc_type}' non trouve.")

    # Recalculer les flags du dossier apres suppression
    # Si Kbis supprime → on garde le flag personne_morale (c'est le client qui l'a coche)
    # Le Kbis sera re-demande dans la checklist tant que personne_morale = True
    # Seul le SIREN/raison sociale extraits sont reinitialises
    if doc_type_upper == "KBIS":
        dossier.pop("siren", None)
        dossier.pop("raison_sociale", None)

    # Si CNI/passeport supprime → sexe deduit reset
    if doc_type_upper in ("CNI", "PASSEPORT"):
        dossier["client_sexe"] = None

    # Reconstruire la liste fusionnee
    dossier["documents"] = dossier.get("documents_vendeur", []) + docs_client

    # Recalculer la checklist (les docs attendus changent peut-etre)
    checklist = _check_client_docs(dossier)

    return {
        "status": "ok",
        "message": f"Le document '{doc_type}' a bien ete supprime. Vous pouvez en deposer un nouveau des que vous etes pret.",
        "checklist": checklist,
        "documents_attendus": _get_client_docs_attendus(dossier),
    }


@app.post("/api/client/{token}/confirmer-envoi")
def confirmer_envoi_documents(token: str):
    """
    Le client confirme l'envoi de ses documents au vendeur.

    Appele apres que le client a verifie le recapitulatif et coche la confirmation.
    Les documents ne sont PAS transmis automatiquement — c'est une action explicite.
    """
    dossier = None
    for d in DOSSIERS.values():
        if d.get("client_link_token") == token:
            dossier = d
            break
    if not dossier:
        raise HTTPException(404, "Lien invalide ou expire")

    # Verifier que tous les docs sont prets
    checklist = _check_client_docs(dossier)
    if not checklist.get("ready_for_diagnostic"):
        raise HTTPException(422, detail={
            "error": "docs_incomplets",
            "message": "Tous les documents ne sont pas encore deposes ou valides.",
            "checklist": checklist,
        })

    # Marquer comme envoye
    dossier["client_docs_envoyes"] = True
    dossier["client_docs_envoyes_at"] = datetime.utcnow().isoformat()

    nom_commerce = PROFIL_PRO.get("nom_commerce", "votre vendeur")
    tel_commerce = PROFIL_PRO.get("telephone_commerce", "")
    cpi_mode = dossier.get("cpi_mode_reception", "main_propre")

    if cpi_mode == "email":
        cpi_message = (
            f"{nom_commerce} vous enverra votre Certificat d'Immatriculation Provisoire (CPI) "
            f"par email a l'adresse {dossier.get('cpi_email', '')} "
            "une fois qu'il aura finalise le dossier aupres du SIV."
        )
    else:
        cpi_message = (
            f"{nom_commerce} vous contactera directement "
            "une fois qu'il aura finalise le dossier aupres du SIV "
            "pour que vous puissiez recuperer votre "
            "Certificat d'Immatriculation Provisoire (CPI) en main propre."
        )

    return {
        "status": "envoye",
        "message": (
            f"Merci ! Vos documents ont bien ete transmis a {nom_commerce}. "
            "Votre dossier de carte grise va etre finalise."
        ),
        "prochaines_etapes": [
            f"{nom_commerce} va verifier votre dossier et soumettre la demande aupres du SIV.",
            f"{cpi_message} Ce document vous permettra de circuler pendant 1 mois.",
            (
                "Votre carte grise definitive vous sera envoyee par courrier securise "
                "(Imprimerie Nationale) a l'adresse figurant sur le justificatif de domicile "
                "que vous avez depose — c'est cette adresse qui sera inscrite sur votre "
                "certificat d'immatriculation. Delai : 3 a 7 jours ouvrables."
            ),
        ],
        "contact": (
            f"Pour toute question, contactez {nom_commerce}"
            + (f" au {tel_commerce}" if tel_commerce else "")
            + "."
        ),
    }


class ChoixCPI(BaseModel):
    mode: str  # "email" ou "main_propre"
    email: str | None = None  # Obligatoire si mode = "email"


@app.post("/api/client/{token}/choix-cpi")
def choisir_mode_cpi(token: str, choix: ChoixCPI):
    """
    Le client choisit comment il veut recevoir son CPI.
    Cette etape est obligatoire AVANT de pouvoir deposer des documents.
    """
    dossier = None
    for d in DOSSIERS.values():
        if d.get("client_link_token") == token:
            dossier = d
            break
    if not dossier:
        raise HTTPException(404, "Lien invalide ou expire")

    if choix.mode not in ("email", "main_propre"):
        raise HTTPException(422, "Mode invalide. Choisissez 'email' ou 'main_propre'.")

    if choix.mode == "email":
        if not choix.email or "@" not in choix.email:
            raise HTTPException(422, "Adresse email requise pour la reception par email.")
        dossier["cpi_email"] = choix.email

    dossier["cpi_mode_reception"] = choix.mode
    dossier["cpi_choix_at"] = datetime.utcnow().isoformat()

    nom_commerce = PROFIL_PRO.get("nom_commerce", "votre vendeur")

    if choix.mode == "email":
        message = f"Votre CPI vous sera envoye par email a {choix.email} des que {nom_commerce} aura finalise la demarche."
    else:
        message = f"Votre CPI sera a recuperer aupres de {nom_commerce}."

    return {
        "status": "ok",
        "message": message,
        "upload_debloque": True,
    }


@app.post("/api/client/{token}/signer-cession")
def signer_cession_client(token: str, signature_data: dict | None = None):
    """
    Le client signe le certificat de cession (VO uniquement, si pas de cession deposee par le pro).

    Etapes :
    1. Le client voit le certificat de cession pre-rempli
    2. Il signe au doigt (canvas HTML5)
    3. Il confirme par code OTP SMS
    4. Le PDF final est genere (vendeur + client)
    5. Le client DOIT telecharger son exemplaire avant de pouvoir continuer
    """
    dossier = None
    for d in DOSSIERS.values():
        if d.get("client_link_token") == token:
            dossier = d
            break
    if not dossier:
        raise HTTPException(404, "Lien invalide ou expire")

    if not dossier.get("pas_de_certificat_cession"):
        raise HTTPException(422, "Le certificat de cession a ete depose par le vendeur — pas de signature requise.")

    # Enregistrer la signature
    dossier["cession_signee_client"] = True
    dossier["cession_signee_client_at"] = datetime.utcnow().isoformat()
    dossier["cession_client_telechargee"] = False  # Le client n'a PAS encore telecharge

    # En prod : generer le PDF final ici (signature vendeur auto + signature client canvas)

    return {
        "status": "cession_signee",
        "message": (
            "Votre signature a ete enregistree. "
            "Vous devez maintenant telecharger votre exemplaire du certificat de cession. "
            "Ce document est obligatoire — conservez-le precieusement."
        ),
        "telechargement_obligatoire": True,
        "telechargement_url": f"/api/client/{token}/telecharger-cession",
        "upload_bloque": True,  # Les uploads suivants sont bloques tant que pas telecharge
    }


@app.get("/api/client/{token}/telecharger-cession")
def telecharger_cession_client(token: str):
    """
    Le client telecharge son exemplaire du certificat de cession signe.
    Ce telechargement est OBLIGATOIRE — les uploads suivants sont bloques tant
    que le client n'a pas telecharge.
    """
    dossier = None
    for d in DOSSIERS.values():
        if d.get("client_link_token") == token:
            dossier = d
            break
    if not dossier:
        raise HTTPException(404, "Lien invalide ou expire")

    if not dossier.get("cession_signee_client"):
        raise HTTPException(422, "Le certificat de cession n'a pas encore ete signe.")

    # Marquer comme telecharge → debloquer les uploads
    dossier["cession_client_telechargee"] = True
    dossier["cession_client_telechargee_at"] = datetime.utcnow().isoformat()

    # En prod : retourner le PDF reel
    # Pour la demo, on retourne un placeholder
    return {
        "status": "ok",
        "message": (
            "Certificat de cession telecharge. "
            "Conservez ce document precieusement. "
            "Vous pouvez maintenant continuer le depot de vos documents."
        ),
        "upload_debloque": True,
    }


# ─── Reglementation permis / vehicule ────────────────────────────────────────
#
# Categorie L (deux/trois-roues motorises) — reglementation francaise :
#
# | Categorie vehicule | Puissance max   | Permis requis           | Alternative permis B         |
# |--------------------|-----------------|-------------------------|------------------------------|
# | L1e (cyclomoteur)  | ≤ 4 kW          | AM (ou BSR)             | B suffit (AM inclus)         |
# | L3e ≤ 125cc        | ≤ 11 kW         | A1                      | B + formation 7h (si B ≥ 2 ans) |
# | L3e > 125cc        | ≤ 35 kW         | A2                      | Non                          |
# | L3e puissant       | > 35 kW         | A (2 ans A2 + formation)| Non                          |
# | L5e (tricycle)     | ≤ 15 kW         | A1                      | B + formation 7h (si B ≥ 2 ans) |
# | L5e puissant       | > 15 kW         | A                       | B + formation 7h (si B ≥ 2 ans + age ≥ 21) |
#
# Moto electrique : memes seuils de puissance (kW), pas de cylindree.
# La puissance est extraite du COC (champ P.2 = puissance nette max en kW).
#
# Regle formation 7h (art. R221-1 code de la route) :
# - Permis B obtenu depuis ≥ 2 ans
# - Formation 7h en moto-ecole agreee
# - Attestation de suivi de formation delivree
# - Valable uniquement pour vehicules ≤ 11 kW (L3e 125cc) et tricycles L5e


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
    is_vo = dossier.get("type", "").upper() in ("VO", "OCCASION")

    docs = []

    if is_pm:
        docs.append({"type": "KBIS", "label": "Kbis de la societe", "obligatoire": True})
        docs.append({"type": "CNI", "label": "CNI du representant legal", "obligatoire": True})
        docs.append({"type": "DOMICILE", "label": "Justificatif de domicile du siege", "obligatoire": True})
    else:
        docs.append({"type": "CNI", "label": "CNI ou Passeport (recto + verso)", "obligatoire": True})
        docs.append({"type": "PERMIS", "label": "Permis de conduire (recto + verso)", "obligatoire": True})
        docs.append({"type": "DOMICILE", "label": "Justificatif de domicile", "obligatoire": True})

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

    # Assurance — uniquement si le pro a demande la collecte aupres du client
    if dossier.get("demander_assurance_client"):
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
        if dtype not in ("CNI", "PASSEPORT"):
            continue

        ext = d.get("extracted_data", {})
        date_exp_str = ext.get("date_expiration")
        type_id = ext.get("type_identite", dtype)

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

    # ─── 4. Nom acheteur sur CG barree ↔ CNI client ───
    # La CG barree contient le nom de l'acheteur inscrit sur la barre horizontale.
    # Ce nom doit correspondre au nom sur la CNI du client.
    for d in dossier.get("documents_vendeur", []):
        if d.get("type", "").upper() == "CG_BARREE":
            ext_cg = d.get("extracted_data", {})
            nom_acheteur_barre = (ext_cg.get("acheteur_nom_barre") or "").upper().strip()

            if nom_acheteur_barre and nom_id and len(nom_acheteur_barre) > 1:
                if (nom_acheteur_barre != nom_id
                        and nom_acheteur_barre not in nom_id
                        and nom_id not in nom_acheteur_barre):
                    problems.append(_make_incoherence_problem(
                        "INCOHERENCE_NOM_CG_BARREE",
                        "Nom acheteur sur CG barree different de la CNI",
                        (
                            f"Nom acheteur inscrit sur la CG barree : '{nom_acheteur_barre}' — "
                            f"Nom sur la CNI/passeport : '{nom_id}'. "
                            "Le nom sur la barre de la CG doit correspondre a l'acheteur."
                        ),
                        dossier, ["CNI", "PASSEPORT", "CG_BARREE"],
                    ))
            break

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

    if dossier.get("client_docs_envoyes"):
        return {
            "message": "Vos documents ont deja ete transmis. Tout est en ordre !",
            "retour": True,
        }

    if docs_deposes == 0:
        # Premiere visite
        return {
            "message": (
                "Vous pouvez fermer cette page a tout moment. "
                "Vos documents seront sauvegardes. "
                "Reouvrez le lien recu par SMS pour reprendre."
            ),
            "premiere_visite": True,
        }
    else:
        # Retour apres interruption
        return {
            "message": (
                f"Bon retour ! Vous avez deja depose {docs_deposes} document(s). "
                + (f"Il en reste {docs_manquants} a deposer." if docs_manquants > 0
                   else "Tous vos documents sont deposes — plus qu'a confirmer l'envoi !")
            ),
            "retour": True,
            "docs_deposes": docs_deposes,
            "docs_manquants": docs_manquants,
        }


def _build_rappel_assurance(dossier: dict) -> dict | None:
    """
    Rappel assurance cote pro.
    Affiche l'etat du choix assurance pour ce dossier.
    """
    if dossier.get("type") is None:
        return None

    choix_fait = dossier.get("choix_assurance_pro")

    if not choix_fait:
        return {
            "status": "choix_requis",
            "message": "Plus qu'une petite etape : repondez aux questions sur l'assurance pour finaliser ce dossier.",
        }

    if dossier.get("assurance_flotte_couvre"):
        return {
            "status": "couvert",
            "message": "Votre assurance flotte couvre ce vehicule.",
        }

    if dossier.get("demander_assurance_client"):
        return {
            "status": "demande_client",
            "message": "L'attestation d'assurance sera demandee a votre client.",
        }

    return {
        "status": "gere_par_pro",
        "message": "Vous gerez l'assurance directement avec votre client.",
    }


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

@app.post("/api/dossiers/{dossier_id}/run-pipeline")
def run_pipeline(dossier_id: str):
    dossier = DOSSIERS.get(dossier_id)
    if not dossier:
        raise HTTPException(404, "Dossier non trouve")

    # Verrou : bloquer le diagnostic si docs incomplets ou illisibles
    blocages = _check_cerfa_blocages(dossier)
    if blocages["blocked"]:
        raise HTTPException(422, detail={
            "error": "diagnostic_bloque",
            "message": "Pour lancer le diagnostic, on a besoin que tous les documents soient deposes et bien lisibles. Verifiez les pieces manquantes et on avance ensemble !",
            "blocages": blocages["reasons"],
            "pro_docs": blocages["pro_status"],
            "client_docs": blocages["client_status"],
        })

    result = run_diagnostic(dossier)

    dossier["status"] = "DIAGNOSTIC"
    dossier["diagnostic"] = result["diagnostic"]
    dossier["blocages"] = result["blocages"]
    dossier["warnings"] = result["warnings"]
    dossier["infos"] = result.get("infos", [])
    dossier["tax_estimate"] = result["tax_estimate"]

    return result


@app.get("/api/dossiers/{dossier_id}/cerfa")
def generate_cerfa(dossier_id: str):
    """Genere le Cerfa 13750 officiel via Playwright sur service-public.gouv.fr."""
    from engine.cerfa_automation.cerfa_filler import CerfaFiller

    dossier = DOSSIERS.get(dossier_id)
    if not dossier:
        raise HTTPException(404, "Dossier non trouve")

    # ─── Verrou : bloquer la generation si docs incomplets ou illisibles ───
    blocages = _check_cerfa_blocages(dossier)
    if blocages["blocked"]:
        raise HTTPException(422, detail={
            "error": "generation_bloquee",
            "message": "On y est presque ! Pour generer le Cerfa, assurez-vous que tous les documents sont bien deposes et lisibles.",
            "blocages": blocages["reasons"],
            "pro_docs": blocages["pro_status"],
            "client_docs": blocages["client_status"],
        })

    # Construire les donnees pour le CerfaFiller
    data = CerfaFiller.build_data_from_dossier(dossier)
    dossier_type = dossier.get("type", "VO")  # VN ou VO

    # Generer le PDF via Playwright (service-public.gouv.fr)
    filler = CerfaFiller(headless=True)
    pdf_bytes = filler.fill_and_download(data, dossier_type=dossier_type)

    # Stocker le Cerfa dans le dossier (espace admin)
    import base64
    dossier["cerfa_pdf"] = base64.b64encode(pdf_bytes).decode()
    dossier["cerfa_generated_at"] = datetime.utcnow().isoformat()
    dossier["status"] = "CERFA_GENERE"

    # Messages admin : verification manuelle si attestation formation presente
    # Messages admin apres generation Cerfa
    dossier["messages_admin"] = []  # Reset messages

    # Attestation formation → verification manuelle
    has_attestation = any(d["type"] == "ATTESTATION_FORMATION" for d in dossier["documents"])
    has_permis = any(d["type"] == "PERMIS" for d in dossier["documents"])
    if has_attestation:
        dossier["messages_admin"].append({
            "type": "VERIFICATION_MANUELLE",
            "priority": "HAUTE",
            "message": "Attestation de suivi de formation detectee - verifier la coherence avec le permis (categorie, date obtention B, n. permis)",
            "documents_concernes": ["ATTESTATION_FORMATION", "PERMIS"],
            "created_at": datetime.utcnow().isoformat(),
        })

    # Attestation assurance → si fournie, message verification (pas de coherence auto)
    has_assurance = any(d["type"] == "ASSURANCE" for d in dossier["documents"])
    if has_assurance:
        dossier["messages_admin"].append({
            "type": "VERIFICATION_MANUELLE",
            "priority": "NORMALE",
            "message": "Attestation d'assurance fournie - verifier la validite et la coherence avec le vehicule",
            "documents_concernes": ["ASSURANCE"],
            "created_at": datetime.utcnow().isoformat(),
        })
    else:
        dossier["messages_admin"].append({
            "type": "DOCUMENT_MANQUANT",
            "priority": "INFO",
            "message": "Attestation d'assurance non fournie par le client - a suivre",
            "documents_concernes": ["ASSURANCE"],
            "created_at": datetime.utcnow().isoformat(),
        })

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="cerfa_{dossier["reference"]}.pdf"'},
    )


@app.get("/api/dossiers/{dossier_id}/admin")
def admin_view(dossier_id: str):
    """
    Vue admin complete du dossier :
    - Tous les docs vendeur + client (sans doublon)
    - Le Cerfa genere
    - Le diagnostic
    - Les messages admin (verifications manuelles)
    """
    dossier = DOSSIERS.get(dossier_id)
    if not dossier:
        raise HTTPException(404, "Dossier non trouve")

    # Resume docs par source
    docs_vendeur = []
    for d in dossier["documents_vendeur"]:
        docs_vendeur.append({
            "type": d["type"],
            "filename": d["filename"],
            "status": d["status"],
            "extracted_fields": len([k for k, v in d.get("extracted_data", {}).items() if v and k != "dates_detectees"]),
        })

    docs_client = []
    for d in dossier["documents_client"]:
        docs_client.append({
            "type": d["type"],
            "filename": d["filename"],
            "status": d["status"],
            "extracted_fields": len([k for k, v in d.get("extracted_data", {}).items() if v and k != "dates_detectees"]),
        })

    return {
        "reference": dossier["reference"],
        "type": dossier["type"],
        "status": dossier["status"],
        "diagnostic": dossier["diagnostic"],
        "client_nom": dossier.get("client_nom"),
        "client_prenom": dossier.get("client_prenom"),
        "is_personne_morale": dossier.get("is_personne_morale"),
        "documents_vendeur": docs_vendeur,
        "documents_client": docs_client,
        "total_documents": len(docs_vendeur) + len(docs_client),
        "cerfa_genere": dossier.get("cerfa_pdf") is not None,
        "cerfa_generated_at": dossier.get("cerfa_generated_at"),
        "blocages": dossier.get("blocages", []),
        "warnings": dossier.get("warnings", []),
        "infos": dossier.get("infos", []),
        "tax_estimate": dossier.get("tax_estimate"),
        "messages_admin": dossier.get("messages_admin", []),
        "created_at": dossier.get("created_at"),
    }


@app.get("/api/dossiers/{dossier_id}/admin/cerfa")
def admin_download_cerfa(dossier_id: str):
    """Telecharge le Cerfa stocke dans l'espace admin."""
    import base64
    dossier = DOSSIERS.get(dossier_id)
    if not dossier:
        raise HTTPException(404, "Dossier non trouve")
    if not dossier.get("cerfa_pdf"):
        raise HTTPException(404, "Cerfa pas encore genere")

    pdf_bytes = base64.b64decode(dossier["cerfa_pdf"])
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="cerfa_{dossier["reference"]}.pdf"'},
    )


# ─── Ancien flux signature manuelle — SUPPRIME ──────────────────────────────
# Le cachet et la signature du pro sont apposes automatiquement par le systeme
# lors de la generation du Cerfa. Le pro recoit le Cerfa pret a soumettre.
# Le client ne signe jamais le Cerfa (il signe uniquement la cession en VO
# si le certificat de cession n'a pas ete depose par le pro).


@app.delete("/api/dossiers/{dossier_id}")
def delete_dossier(dossier_id: str):
    if dossier_id in DOSSIERS:
        del DOSSIERS[dossier_id]
    return {"ok": True}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

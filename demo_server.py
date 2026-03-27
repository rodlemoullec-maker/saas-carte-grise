"""
Serveur demo v2 - moteur adapte au projet reel.

Logique :
- Le pro uploade les docs qu'il a (pas de liste rigide obligatoire)
- Le moteur classifie, extrait, croise ce qui est disponible
- Diagnostic : VERT si tout est coherent, ORANGE si warnings, ROUGE si incoherence detectee
- Pas d'exigence assurance vehicule
- Pas d'exigence Cerfa (le pro le fournit mais ce n'est pas un pre-requis diagnostic)
- Le Cerfa n'est pas genere - il est fourni par le pro

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
    "KBIS": [
        ("kbis", 1.0), ("extrait du registre", 0.9), ("greffe", 0.7),
        ("tribunal de commerce", 0.7), ("commerce et des societes", 0.6),
        ("raison sociale", 0.5), ("siren", 0.4),
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


def _ocr_tesseract(file_bytes: bytes, mime_type: str) -> str:
    """Extrait le texte d'un PDF ou image via Tesseract OCR (local, gratuit)."""
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
                return text  # PDF avec texte — pas besoin d'OCR
        except Exception:
            pass

        # PDF scan → convertir en images
        try:
            from pdf2image import convert_from_bytes
            images = convert_from_bytes(file_bytes, dpi=300)
        except Exception:
            # pdf2image necessite poppler — fallback
            logger.warning("pdf2image echoue (poppler manquant?) — texte vide")
            return ""
    else:
        # Image directe (JPG, PNG, TIFF)
        images = [Image.open(io.BytesIO(file_bytes))]

    # OCR Tesseract sur chaque image
    text = ""
    for img in images:
        t = pytesseract.image_to_string(img, lang="fra")
        text += t + "\n"

    return text.strip()


def _ocr_google_docai(file_bytes: bytes, mime_type: str) -> str:
    """Fallback OCR via Google Document AI (payant, pour docs que Tesseract ne gere pas)."""
    from integrations.ocr_providers.google_docai import GoogleDocAIProvider

    creds = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "")
    if not creds:
        for f_cred in Path(".").glob("**/gen-lang-client*.json"):
            creds = str(f_cred)
            break
    if not creds:
        return ""

    ocr = GoogleDocAIProvider(credentials_path=creds)
    result = ocr.process_sync(file_bytes, mime_type)
    return result.full_text


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
        m = re.search(r"[Nn]om\s*(?:de\s*naissance)?\s*[:\s]*([A-Z\- ]{2,40})", text)
        if m: data["nom"] = m.group(1).strip()
        m = re.search(r"[Pp]r[eé]noms?\s*[:\s]*([A-Za-zÀ-ÿ\- ]{2,60})", text)
        if m: data["prenoms"] = m.group(1).strip()
        m = re.search(r"[Ll]ieu\s*(?:de\s*naissance)?\s*[:\s]*([A-Za-zÀ-ÿ\- ]{2,40})", text)
        if m: data["lieu_naissance"] = m.group(1).strip()
        m = re.search(r"[Nn]ationalit[eé]\s*[:\s]*([A-Za-zÀ-ÿ\- ]{2,30})", text)
        if m: data["nationalite"] = m.group(1).strip()
        # Format Google DocAI CNI (champs sur lignes separees)
        if not data.get("nom"):
            m = re.search(r"C\.?1\s+([A-Z]{2,30})", text)
            if m: data["nom"] = m.group(1).strip()
        if not data.get("prenoms"):
            # Chercher prenom apres le nom (ligne suivante)
            nom = data.get("nom", "")
            if nom:
                m = re.search(re.escape(nom) + r"\s*\n\s*([A-Z][a-zÀ-ÿ]{1,20})", text)
                if m: data["prenoms"] = m.group(1).strip()
        # MRZ extraction (CARIAN<<HADRIEN)
        m = re.search(r"([A-Z]{2,20})<<([A-Z]{2,20})<", text)
        if m:
            if not data.get("nom"): data["nom"] = m.group(1)
            if not data.get("prenoms"): data["prenoms"] = m.group(2)
        # Adresse depuis Google DocAI
        m = re.search(r"(\d+\s+(?:RUE|AVENUE|BOULEVARD|PLACE|IMPASSE|CHEMIN|ALLEE)\s+[A-Z\- ]{2,40})", text)
        if m: data["adresse_cni"] = m.group(1).strip()
        m = re.search(r"(\d{5})\s+([A-Z][A-Z ]{2,30})", text)
        if m:
            data["code_postal_cni"] = m.group(1)
            data["ville_cni"] = m.group(2).strip()
        m = re.search(r"(?:n[eé]e?\s*le|[Dd]ate\s*de\s*naissance)\s*[:\s]*(\d{2}[./]\d{2}[./]\d{4})", text)
        if m: data["date_naissance"] = m.group(1)
        m = re.search(r"(?:expir|valid)\S*\s*[:\s]*(\d{2}[./]\d{2}[./]\d{4})", text, re.IGNORECASE)
        if m: data["date_expiration"] = m.group(1)

    elif doc_type == "PERMIS":
        m = re.search(r"1\.\s*([A-Z\-\s]{2,40})", text)
        if m: data["nom"] = m.group(1).strip()
        m = re.search(r"2\.\s*([A-Za-zÀ-ÿ\-\s]{2,40})", text)
        if m: data["prenom"] = m.group(1).strip()
        cats = re.findall(r"\b(AM|A1|A2|A|BE|B|CE|C|D)\b", text.upper())
        if cats: data["categories"] = list(dict.fromkeys(cats))

    elif doc_type == "COC":
        m = re.search(r"[Mm]arque\s*[:\s]*([A-Z][A-Za-z\-]{1,20})", text)
        if m: data["marque"] = m.group(1).strip()
        m = re.search(r"[Dd]enomination\s*(?:commerciale)?\s*[:\s]*(.{2,50})", text)
        if m: data["modele"] = m.group(1).strip()
        m = re.search(r"[Cc]arburant\s*[:\s]*([A-Za-z]{2,20})", text)
        if m:
            data["energie"] = m.group(1).strip()
        else:
            m = re.search(r"[Ee]nergie\s*[:\s]*([A-Za-z]{2,20})", text)
            if m: data["energie"] = m.group(1).strip()
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
        m = re.search(r"(?:P\.?2|[Pp]uissance\s*nette\s*maximale)\s*[:\s]*(\d+)\s*kW", text, re.IGNORECASE)
        if m: data["puissance_nette_p2"] = m.group(1)
        # Champs supplementaires pour Cerfa complet
        m = re.search(r"(?:F\.?3|[Mm]asse\s*(?:en\s*charge)?\s*maxi?\s*(?:de\s*l)?\s*ensemble)\s*[:\s]*(\d+)\s*kg", text, re.IGNORECASE)
        if m: data["masse_f3"] = m.group(1)
        m = re.search(r"(?:G\.?1|[Pp]oids\s*a\s*vide\s*national)\s*[:\s]*(\d+)\s*kg", text, re.IGNORECASE)
        if m: data["poids_vide_g1"] = m.group(1)
        m = re.search(r"(?:J\b|[Cc]ategorie(?:\s*vehicule)?)\s*[:\s]*(M\d|N\d|L\d)", text)
        if m: data["categorie_j"] = m.group(1)
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

    Resultat → Cerfa pre-rempli si VERT ou ORANGE.
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
    required_vo = {"CG_BARREE": "Carte grise barree"}
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

class DossierCreate(BaseModel):
    type: str  # VN ou VO
    vin: str | None = None
    immatriculation: str | None = None
    client_nom: str | None = None
    client_prenom: str | None = None
    client_sexe: str | None = None  # M ou F
    is_personne_morale: bool = False
    co_titulaire_nom: str | None = None
    co_titulaire_prenom: str | None = None


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.get("/api/health")
def health():
    return {"status": "ok", "version": "0.3.0", "dossiers": len(DOSSIERS)}


@app.post("/api/dossiers")
def create_dossier(req: DossierCreate):
    dossier_id = str(uuid.uuid4())
    ref = f"CG-2026-{len(DOSSIERS) + 1:05d}"
    dossier = {
        "id": dossier_id,
        "reference": ref,
        "type": req.type,
        "vin": req.vin,
        "immatriculation": req.immatriculation,
        "client_nom": req.client_nom,
        "client_prenom": req.client_prenom,
        "client_sexe": req.client_sexe,
        "is_personne_morale": req.is_personne_morale,
        "co_titulaire_nom": req.co_titulaire_nom,
        "co_titulaire_prenom": req.co_titulaire_prenom,
        "status": "PENDING",
        "diagnostic": None,
        "blocages": [],
        "warnings": [],
        "infos": [],
        "tax_estimate": None,
        "documents_vendeur": [],    # Docs deposes par le pro (COC, CG barree, facture)
        "documents_client": [],     # Docs deposes par le client (CNI, permis, domicile)
        "documents": [],            # Fusion des deux (pour le diagnostic + cerfa)
        "cerfa_pdf": None,          # Cerfa genere (bytes stockes)
        "cerfa_generated_at": None,
        "messages_admin": [],       # Messages pour l'admin (verifications manuelles)
        "created_at": datetime.utcnow().isoformat(),
    }
    DOSSIERS[dossier_id] = dossier
    return dossier


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
async def upload_document(dossier_id: str, file: UploadFile, source: str = "vendeur"):
    """
    Upload un document. source = 'vendeur' ou 'client'.
    Le vendeur depose : COC, CG barree, facture
    Le client depose : CNI, permis, justificatif domicile
    """
    dossier = DOSSIERS.get(dossier_id)
    if not dossier:
        raise HTTPException(404, "Dossier non trouve")

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

    # OCR : Tesseract d'abord, Google Document AI en fallback si echec
    raw_text = ""
    mime = file.content_type or ""
    if mime in ("application/pdf", "image/jpeg", "image/png", "image/tiff", "image/webp"):
        # 1. Tesseract (gratuit, local)
        try:
            raw_text = _ocr_tesseract(file_bytes, mime)
            logger.info(f"OCR Tesseract: {len(raw_text)} chars")
        except Exception as e:
            logger.warning(f"OCR Tesseract echoue: {e}")

        # 2. Si Tesseract n'a rien donne (<50 chars) → Google Document AI
        if len(raw_text.strip()) < 50:
            try:
                raw_text_google = _ocr_google_docai(file_bytes, mime)
                if len(raw_text_google.strip()) > len(raw_text.strip()):
                    raw_text = raw_text_google
                    logger.info(f"OCR Google DocAI (fallback): {len(raw_text)} chars")
            except Exception as e:
                logger.warning(f"OCR Google DocAI echoue: {e}")
    else:
        try:
            raw_text = file_bytes.decode("utf-8", errors="ignore")
        except Exception:
            pass

    # Classify + extract
    doc_type, confidence, keywords = classify_document(raw_text)
    extracted = extract_data(doc_type, raw_text)

    doc = {
        "id": doc_id,
        "filename": file.filename,
        "type": doc_type,
        "source": source,
        "classification_confidence": confidence,
        "matched_keywords": keywords,
        "extracted_data": extracted,
        "ocr_text": raw_text,  # Texte brut OCR (pour fusion recto/verso)
        "status": "EXTRACTED",
        "size_bytes": len(file_bytes),
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

    return doc


@app.post("/api/dossiers/{dossier_id}/run-pipeline")
def run_pipeline(dossier_id: str):
    dossier = DOSSIERS.get(dossier_id)
    if not dossier:
        raise HTTPException(404, "Dossier non trouve")

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
    has_attestation = any(d["type"] == "ATTESTATION_FORMATION" for d in dossier["documents"])
    has_permis = any(d["type"] == "PERMIS" for d in dossier["documents"])
    if has_attestation:
        msg = {
            "type": "VERIFICATION_MANUELLE",
            "priority": "HAUTE",
            "message": "Attestation de suivi de formation detectee — verifier la coherence avec le permis de conduire (categorie, date obtention B, n. permis)",
            "documents_concernes": ["ATTESTATION_FORMATION", "PERMIS"],
            "permis_present": has_permis,
            "created_at": datetime.utcnow().isoformat(),
        }
        dossier["messages_admin"].append(msg)
        logger.info(f"Message admin: verification attestation formation")

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


@app.delete("/api/dossiers/{dossier_id}")
def delete_dossier(dossier_id: str):
    if dossier_id in DOSSIERS:
        del DOSSIERS[dossier_id]
    return {"ok": True}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

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
        ("tva", 0.4), ("vehicule neuf", 0.6),
    ],
    "DOMICILE": [
        ("edf", 0.6), ("engie", 0.6), ("electricite", 0.5),
        ("quittance", 0.5), ("avis d'imposition", 0.7),
        ("attestation d'hebergement", 0.7), ("impot", 0.4),
    ],
    "CG_BARREE": [
        ("certificat d'immatriculation", 0.6), ("carte grise", 0.6),
        ("vendu le", 0.9), ("formule", 0.3), ("titulaire", 0.3),
    ],
}


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
        m = re.search(r"(?:PTAC|[Mm]asse\s*en\s*charge|F\.?2)\s*[:\s]*(\d+)\s*kg", text, re.IGNORECASE)
        if m: data["ptac_kg"] = int(m.group(1))
        m = re.search(r"(?:S\.?1|[Pp]laces)\s*[:\s]*(\d+)", text)
        if m: data["places"] = int(m.group(1))

    elif doc_type == "FACTURE":
        m = re.search(r"[Aa]cheteur|[Cc]lient\s*[:\s]*([A-Za-zÀ-ÿ\-\s]{2,60})", text)
        if m: data["acheteur"] = m.group(1).strip()
        m = re.search(r"SIRET\s*[:\s]*([\d\s]{14,18})", text)
        if m: data["siret_vendeur"] = re.sub(r"\s", "", m.group(1))
        m = re.search(r"[Tt]otal\s*TTC\s*[:\s]*([\d\s.,]+)\s*EUR", text)
        if m: data["prix_ttc"] = m.group(1).strip()
        m = re.search(r"[Mm]arque\s*[:\s]*([A-Za-zÀ-ÿ\-\s]{2,30})", text)
        if m: data["marque"] = m.group(1).strip()

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
        m = re.search(r"(?:C\.?1|[Tt]itulaire)\s*[:\s]*([A-Za-zÀ-ÿ\-\s]{2,60})", text)
        if m: data["titulaire"] = m.group(1).strip()
        m = re.search(r"[Vv]endu\s*le\s*[:\s]*(\d{2}[./]\d{2}[./]\d{4})", text)
        if m: data["date_vente"] = m.group(1)
        data["barre_diagonale"] = bool(re.search(r"barr[eé]|diagonale|vendu le", text, re.IGNORECASE))

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

    # ─── 1. Pieces presentes / manquantes ─────────────────────────────────
    required_common = {
        "CNI": "Piece d'identite (CNI ou passeport)",
        "DOMICILE": "Justificatif de domicile",
        "PERMIS": "Permis de conduire",
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
        "documents": [],
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
async def upload_document(dossier_id: str, file: UploadFile):
    dossier = DOSSIERS.get(dossier_id)
    if not dossier:
        raise HTTPException(404, "Dossier non trouve")

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

    # Decode text
    raw_text = ""
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
        "classification_confidence": confidence,
        "matched_keywords": keywords,
        "extracted_data": extracted,
        "status": "EXTRACTED",
        "size_bytes": len(file_bytes),
    }
    dossier["documents"].append(doc)

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
    """Genere le vrai Cerfa 13749 officiel pre-rempli avec les donnees extraites."""
    from fpdf import FPDF
    from pypdf import PdfReader, PdfWriter
    import io

    dossier = DOSSIERS.get(dossier_id)
    if not dossier:
        raise HTTPException(404, "Dossier non trouve")

    # Collecter les donnees
    d: dict[str, str] = {}
    d["nom"] = dossier.get("client_nom") or ""
    d["prenom"] = dossier.get("client_prenom") or ""
    d["vin"] = dossier.get("vin") or ""
    d["immat"] = dossier.get("immatriculation") or ""

    for doc in dossier["documents"]:
        ext = doc.get("extracted_data", {})
        if doc["type"] in ("CNI", "PASSEPORT"):
            d["nom"] = ext.get("nom") or d["nom"]
            d["prenoms"] = ext.get("prenoms") or d.get("prenoms", d["prenom"])
            d["date_naissance"] = ext.get("date_naissance") or ""
        elif doc["type"] == "COC":
            d["marque"] = ext.get("marque") or ""
            d["modele"] = ext.get("modele") or ""
            d["energie"] = ext.get("energie") or ""
            d["puissance_cv"] = str(ext.get("puissance_cv") or "")
            d["cnit"] = ext.get("cnit") or ""
            d["co2"] = str(ext.get("co2_wltp") or "")
            d["places"] = str(ext.get("places") or "")
            d["ptac"] = str(ext.get("ptac_kg") or "")
            d["vin"] = ext.get("vin") or d["vin"]
        elif doc["type"] == "DOMICILE":
            d["adresse"] = ext.get("adresse") or ""
            d["cp"] = ext.get("code_postal") or ""
            d["ville"] = ext.get("ville") or ""
        elif doc["type"] == "FACTURE":
            d["vin"] = ext.get("vin") or d["vin"]
        elif doc["type"] == "CG_BARREE":
            d["immat"] = ext.get("immatriculation") or d["immat"]

    # ─── Generer un Cerfa propre from scratch ────────────────────────────
    is_vn = dossier["type"] == "VN"
    cerfa_num = "13749*06" if is_vn else "13750*07"
    is_pm = dossier.get("is_personne_morale", False)
    sexe = dossier.get("client_sexe") or ""
    has_co_tit = bool(dossier.get("co_titulaire_nom"))

    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=False)

    # ─── Helpers ──────────────────────────────────────────────────────
    def title(y, text):
        pdf.set_xy(10, y)
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_fill_color(200, 210, 230)
        pdf.cell(190, 6, f"  {text}", fill=True, border=1)

    def label(x, y, text, w=45):
        pdf.set_xy(x, y)
        pdf.set_font("Helvetica", "", 7)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(w, 4, text)
        pdf.set_text_color(0, 0, 0)

    def value(x, y, text, w=100, h=6, border=1):
        pdf.set_xy(x, y)
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(w, h, str(text or ""), border=border)

    def checkbox(x, y, checked=False):
        pdf.rect(x, y, 4, 4)
        if checked:
            pdf.set_font("Helvetica", "B", 8)
            pdf.set_xy(x + 0.3, y - 0.5)
            pdf.cell(4, 4, "X")

    def boxed_chars(x, y, text, count=10, box_w=5.5):
        for i in range(count):
            pdf.rect(x + i * box_w, y, box_w, 6)
            if i < len(str(text or "")):
                pdf.set_font("Courier", "B", 10)
                pdf.set_xy(x + i * box_w + 0.8, y)
                pdf.cell(box_w - 1, 6, str(text)[i])

    # ─── EN-TETE ──────────────────────────────────────────────────────
    pdf.set_fill_color(0, 0, 100)
    pdf.rect(0, 0, 210, 18, "F")
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_xy(10, 3)
    pdf.cell(140, 6, "DEMANDE DE CERTIFICAT D'IMMATRICULATION")
    pdf.set_font("Helvetica", "", 8)
    pdf.set_xy(10, 9)
    sub = "VEHICULE NEUF" if is_vn else "VEHICULE D'OCCASION"
    pdf.cell(140, 5, f"{sub} - Articles R. 322-1 et suivants du code de la route")
    pdf.set_xy(155, 3)
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(45, 6, f"CERFA {cerfa_num}", align="R")
    pdf.set_text_color(0, 0, 0)

    # ─── VEHICULE ─────────────────────────────────────────────────────
    y = 22
    title(y, "VEHICULE")
    y += 8

    label(10, y, "Marque (D.1)"); value(55, y, d.get("marque", ""), w=60)
    label(120, y, "CNIT (D.2.1)"); value(150, y, d.get("cnit", ""), w=50)
    y += 8
    label(10, y, "VIN (E)"); value(55, y, d.get("vin", ""), w=145)
    y += 8
    label(10, y, "Denomination (D.3)"); value(55, y, (d.get("modele") or "")[:40], w=145)
    y += 8
    label(10, y, "Energie (P.3)"); value(55, y, d.get("energie", ""), w=40)
    label(100, y, "Puissance (P.6)"); value(140, y, f"{d.get('puissance_cv', '')} CV" if d.get("puissance_cv") else "", w=25)
    label(168, y, "Places (S.1)"); value(192, y, d.get("places", ""), w=8)
    y += 8
    if d.get("co2"):
        label(10, y, "CO2 WLTP (V.7)"); value(55, y, f"{d['co2']} g/km", w=40)
    if d.get("ptac"):
        label(100, y, "PTAC (F.2)"); value(140, y, f"{d['ptac']} kg", w=30)
    y += 10

    # ─── DEMANDEUR ────────────────────────────────────────────────────
    title(y, "DEMANDEUR")
    y += 8

    pdf.set_font("Helvetica", "", 8)
    pdf.set_xy(10, y)
    pdf.cell(30, 5, "Personne physique")
    checkbox(42, y + 0.5, not is_pm)
    pdf.set_xy(50, y)
    pdf.cell(30, 5, "Personne morale")
    checkbox(82, y + 0.5, is_pm)

    if not is_pm:
        pdf.set_xy(95, y)
        pdf.cell(15, 5, "Sexe :")
        pdf.cell(5, 5, "M")
        checkbox(116, y + 0.5, sexe.upper() == "M")
        pdf.cell(8, 5, "")
        pdf.cell(5, 5, "F")
        checkbox(132, y + 0.5, sexe.upper() == "F")

    if has_co_tit:
        pdf.set_xy(145, y)
        pdf.set_font("Helvetica", "", 7)
        pdf.cell(40, 5, "Nb titulaires (C.4.1) : 2")
    y += 8

    # Titulaire
    title(y, "TITULAIRE")
    y += 8
    nom_complet = f"{d.get('nom', '')} {d.get('prenoms', d.get('prenom', ''))}".strip()
    label(10, y, "Nom et prenom"); value(55, y, nom_complet, w=145)
    y += 8

    label(10, y, "Ne(e) le")
    ddn = d.get("date_naissance", "")
    if ddn:
        digits = ddn.replace("/", "").replace(".", "")
        boxed_chars(55, y, digits, count=8, box_w=6)
    y += 10

    # Co-titulaire
    if has_co_tit:
        title(y, "CO-TITULAIRE")
        y += 8
        co = f"{dossier.get('co_titulaire_nom', '')} {dossier.get('co_titulaire_prenom', '')}".strip()
        label(10, y, "Nom et prenom"); value(55, y, co, w=145)
        y += 10

    # ─── DOMICILE ─────────────────────────────────────────────────────
    title(y, "DOMICILE")
    y += 8
    label(10, y, "Adresse"); value(55, y, d.get("adresse", ""), w=145)
    y += 8
    label(10, y, "Code postal")
    cp = d.get("cp", "")
    if cp:
        boxed_chars(55, y, cp, count=5, box_w=6)
    label(95, y, "Commune"); value(120, y, d.get("ville", ""), w=80)
    y += 12

    # ─── TAXES ESTIMEES ───────────────────────────────────────────────
    tax = dossier.get("tax_estimate")
    if tax:
        title(y, "ESTIMATION DES TAXES (indicatif - montant final = SIV)")
        y += 8
        pdf.set_font("Helvetica", "", 8)
        for k, lbl in [("y1_taxe_regionale", "Y1 Taxe regionale"), ("y3_malus_co2", "Y3 Malus CO2"),
                        ("y4_taxe_gestion", "Y4 Gestion"), ("y5_redevance", "Y5 Redevance"),
                        ("y6_malus_poids", "Y6 Malus poids")]:
            v = tax.get(k, 0)
            if v:
                pdf.set_xy(15, y); pdf.cell(60, 5, lbl)
                pdf.set_font("Courier", "B", 9)
                pdf.cell(30, 5, f"{v:.2f} EUR", align="R")
                pdf.set_font("Helvetica", "", 8)
                y += 5
        pdf.set_xy(15, y)
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(60, 6, "TOTAL ESTIME")
        pdf.set_font("Courier", "B", 10)
        pdf.cell(30, 6, f"{tax.get('total', 0):.2f} EUR", align="R")
        y += 10

    # ─── SIGNATURE ────────────────────────────────────────────────────
    title(y, "SIGNATURE")
    y += 8
    pdf.set_font("Helvetica", "", 8)
    pdf.set_xy(10, y)
    pdf.cell(50, 5, "Fait a : ........................")
    pdf.cell(50, 5, "Le : ........................")
    y += 8
    pdf.set_xy(10, y)
    pdf.cell(50, 5, "Signature du titulaire :")
    pdf.rect(10, y + 6, 60, 20)
    y += 30

    # ─── PIED DE PAGE ─────────────────────────────────────────────────
    pdf.set_font("Helvetica", "I", 6)
    pdf.set_text_color(120, 120, 120)
    pdf.set_xy(10, 280)
    pdf.cell(190, 4, f"Document pre-rempli par Carte Grise Pro - {dossier['reference']} - A imprimer et signer", align="C")
    pdf.set_text_color(0, 0, 0)

    pdf_bytes = bytes(pdf.output())

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

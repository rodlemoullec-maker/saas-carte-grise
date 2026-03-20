"""Dashboard Streamlit - Interface operateur carte grise."""

import json
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.pipeline.orchestrator import (
    get_dossiers_by_status,
    get_dossier,
    get_documents_for_dossier,
    update_dossier_status,
    update_dossier_data,
    search_dossiers,
    get_all_dossiers,
    delete_dossier,
)
from src.taxes.calculator import calculer_taxes, get_regions
from src.cerfa.filler import fill_cerfa_from_dossier

# --- Configuration page ---
st.set_page_config(
    page_title="Carte Grise Auto",
    page_icon="car",
    layout="wide",
)

# --- Sidebar : Navigation ---
st.sidebar.title("Carte Grise Auto")

page = st.sidebar.radio("Navigation", [
    "Deposer des documents",
    "Dossiers clients",
    "Parametres",
])


# =============================================
# FONCTIONS UTILITAIRES
# =============================================
def _get_documents_requis(genre: str, is_occasion: bool = True) -> dict:
    """Retourne la liste des documents a scanner selon le type de demande."""
    docs = {}

    if is_occasion:
        docs["carte_grise_vendeur"] = {
            "label": "Ancienne carte grise du vendeur",
            "description": "Carte grise barree avec mention 'vendu le...' -- permet d'identifier le vehicule (CNIT)",
        }
        docs["certificat_cession"] = {
            "label": "Certificat de cession (CERFA 15776)",
            "description": "Immatriculation, VIN, date de vente, nom vendeur et acheteur",
        }

    docs["cni"] = {
        "label": "Piece d'identite de l'acheteur",
        "description": (
            "CNI, passeport ou permis de conduire en cours de validite. "
            "Doit comporter : nom, prenom, date de naissance, date de validite"
        ),
    }
    docs["justificatif_domicile"] = {
        "label": "Justificatif de domicile de l'acheteur (moins de 6 mois)",
        "description": (
            "Acceptes : facture electricite/gaz/eau/telephone/internet, "
            "avis d'imposition, taxe fonciere/habitation, "
            "attestation assurance habitation, "
            "quittance de loyer (agence RCS uniquement). "
            "Refuses : quittance manuscrite, bail, fiche de paie, RIB"
        ),
    }

    return docs


def _analyser_document(doc_key: str, fichier, vehicle: dict | None = None) -> dict:
    """Analyse profonde d'un document.

    Strategie rapide :
    1. PDF avec texte -> extraction directe (instant) + modele texte (~30s)
    2. Image ou PDF scan -> modele vision (plus lent, ~3min)

    Args:
        vehicle: vehicule selectionne, pour verification de coherence (cession).
    """
    import tempfile
    import json
    import ollama
    from config.settings import MODEL_TEXT, MODEL_VISION

    PROMPTS = {
        "carte_grise_vendeur": (
            "Voici le texte d'une carte grise (certificat d'immatriculation) francaise. "
            "Extrais les donnees en JSON strict. Les champs importants sont : "
            "A = immatriculation, B = date de premiere immatriculation, "
            "I = date du certificat d'immatriculation actuel, "
            "D.1 = marque, D.2 = type variante version (TVV), "
            "D.2.1 = CNIT (code national d'identification du type), "
            "D.3 = denomination commerciale, E = VIN, J.1 = genre, P.3 = energie, "
            "P.6 = puissance fiscale. "
            "Reponds UNIQUEMENT avec le JSON :\n"
            '{"A_immatriculation":"","B_date_premiere_immat":"JJ/MM/AAAA",'
            '"I_date_immatriculation":"JJ/MM/AAAA",'
            '"D1_marque":"","D2_tvv":"","D2_1_cnit":"",'
            '"D3_denomination":"","E_vin":"","J1_genre":"","P1_cylindree":"",'
            '"P3_energie":"","P6_puissance_fiscale":"","V7_co2":""}'
        ),
        "cni": (
            "Voici le texte d'une piece d'identite (CNI, passeport ou permis de conduire). "
            "Extrais les donnees en JSON strict. "
            "Pour type_document, indique : cni, passeport ou permis_conduire. "
            "Pour sexe, indique M ou F uniquement si le document le mentionne explicitement. "
            "Reponds UNIQUEMENT avec le JSON :\n"
            '{"type_document":"","nom":"","prenom":"","sexe":"M ou F",'
            '"date_naissance":"JJ/MM/AAAA","lieu_naissance":"","lieu_naissance_departement":"numero du departement","date_validite":"JJ/MM/AAAA","numero":""}'
        ),
        "certificat_cession": (
            "Voici le texte d'un certificat de cession de vehicule. "
            "Extrais les donnees en JSON strict. "
            "Reponds UNIQUEMENT avec le JSON :\n"
            '{"immatriculation":"","marque":"","type":"","vin":"","date_cession":"JJ/MM/AAAA",'
            '"vendeur_nom":"","vendeur_prenom":"","acheteur_nom":"","acheteur_prenom":""}'
        ),
        "justificatif_domicile": (
            "Voici le texte d'un justificatif de domicile. "
            "Identifie le type parmi : facture_electricite, facture_gaz, facture_eau, "
            "facture_telephone, facture_internet, avis_imposition, taxe_fonciere, "
            "taxe_habitation, attestation_assurance_habitation, quittance_loyer_agence, "
            "quittance_loyer_particulier, bail, fiche_paie, autre. "
            "Reponds UNIQUEMENT avec le JSON :\n"
            '{"type_justificatif":"","nom_titulaire":"","prenom_titulaire":"",'
            '"adresse_numero":"numero de rue uniquement",'
            '"adresse_type_voie":"RUE ou AVENUE ou BOULEVARD ou CHEMIN ou PLACE ou ALLEE etc",'
            '"adresse_nom_voie":"nom de la voie sans le numero ni le type",'
            '"adresse_code_postal":"","adresse_ville":"",'
            '"date_document":"JJ/MM/AAAA","fournisseur":""}'
        ),
    }

    PROMPTS_VISION = {
        "carte_grise_vendeur": (
            "Lis cette carte grise francaise et extrais en JSON strict. "
            "Champs : A=immatriculation, D.1=marque, D.2=TVV, D.2.1=CNIT, "
            "D.3=denomination, E=VIN, J.1=genre, P.3=energie, P.6=puissance fiscale. "
            "Reponds UNIQUEMENT avec le JSON :\n"
            '{"A_immatriculation":"","B_date_premiere_immat":"JJ/MM/AAAA",'
            '"I_date_immatriculation":"JJ/MM/AAAA",'
            '"D1_marque":"","D2_tvv":"","D2_1_cnit":"",'
            '"D3_denomination":"","E_vin":"","J1_genre":"","P1_cylindree":"",'
            '"P3_energie":"","P6_puissance_fiscale":"","V7_co2":""}'
        ),
        "cni": (
            "Lis cette piece d'identite (CNI, passeport ou permis de conduire) "
            "et extrais les donnees en JSON strict. "
            "Pour type_document, indique : cni, passeport ou permis_conduire. "
            "Pour sexe, indique M ou F uniquement si le document le mentionne explicitement. "
            "Reponds UNIQUEMENT avec le JSON :\n"
            '{"type_document":"","nom":"","prenom":"","sexe":"M ou F",'
            '"date_naissance":"JJ/MM/AAAA","lieu_naissance":"","lieu_naissance_departement":"numero du departement","date_validite":"JJ/MM/AAAA","numero":""}'
        ),
        "certificat_cession": (
            "Lis ce certificat de cession et extrais en JSON strict. "
            "Reponds UNIQUEMENT avec le JSON :\n"
            '{"immatriculation":"","marque":"","type":"","vin":"","date_cession":"JJ/MM/AAAA",'
            '"vendeur_nom":"","vendeur_prenom":"","acheteur_nom":"","acheteur_prenom":""}'
        ),
        "justificatif_domicile": (
            "Lis ce justificatif de domicile et extrais en JSON strict. "
            "Decompose l'adresse : numero de rue seul, type de voie (RUE/AVENUE/etc), nom de voie sans numero ni type. "
            "Reponds UNIQUEMENT avec le JSON :\n"
            '{"type_justificatif":"","nom_titulaire":"","prenom_titulaire":"",'
            '"adresse_numero":"","adresse_type_voie":"","adresse_nom_voie":"",'
            '"adresse_code_postal":"","adresse_ville":"",'
            '"date_document":"JJ/MM/AAAA","fournisseur":""}'
        ),
    }

    with tempfile.NamedTemporaryFile(
        suffix=Path(fichier.name).suffix, delete=False
    ) as tmp:
        tmp.write(fichier.getbuffer())
        tmp_path = tmp.name

    try:
        text = ""
        is_pdf = Path(tmp_path).suffix.lower() == ".pdf"

        # 1. Essayer extraction texte directe (PDF uniquement, instantane)
        if is_pdf:
            try:
                import pypdfium2 as pdfium
                pdf = pdfium.PdfDocument(tmp_path)
                page = pdf[0]
                text = page.get_textpage().get_text_range()
                pdf.close()
            except Exception:
                text = ""

        # 2. Si on a du texte -> modele texte (rapide ~30s)
        if text and len(text.strip()) > 20:
            prompt = PROMPTS.get(doc_key, "Extrais les informations en JSON.")
            response = ollama.chat(
                model=MODEL_TEXT,
                messages=[{
                    "role": "user",
                    "content": prompt + "\n\nTexte du document :\n" + text[:3000],
                }],
            )
        else:
            # 3. Sinon -> modele vision (lent mais necessaire pour images/scans)
            if is_pdf:
                from src.ocr.engine import _pdf_to_png
                image_data = _pdf_to_png(Path(tmp_path))
            else:
                with open(tmp_path, "rb") as f:
                    image_data = f.read()

            prompt = PROMPTS_VISION.get(doc_key, "Extrais les informations en JSON.")
            response = ollama.chat(
                model=MODEL_VISION,
                messages=[{
                    "role": "user",
                    "content": prompt,
                    "images": [image_data],
                }],
            )

        raw = response["message"]["content"].strip()

        # Parser le JSON
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start >= 0 and end > start:
            extracted = json.loads(raw[start:end])
        else:
            extracted = {"_error": f"Pas de JSON: {raw[:200]}"}

        validite = _verifier_document(doc_key, extracted, vehicle=vehicle)

        return {
            "fichier": fichier.name,
            "donnees": extracted,
            "validite": validite,
        }
    except Exception as e:
        return {
            "fichier": fichier.name,
            "donnees": {},
            "validite": {"valide": False, "motif": f"Erreur d'analyse : {e}"},
        }
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def _verifier_document(doc_key: str, donnees: dict, vehicle: dict | None = None) -> dict:
    """Verifie la validite d'un document extrait."""
    from datetime import date, datetime

    if doc_key == "carte_grise_vendeur":
        cnit = donnees.get("D2_1_cnit", "") or donnees.get("D2_tvv", "")
        marque = donnees.get("D1_marque", "")
        immat = donnees.get("A_immatriculation", "")
        vin = donnees.get("E_vin", "")

        if not cnit and not marque:
            return {"valide": False, "motif": "CNIT et marque non detectes sur la carte grise"}

        # Chercher le vehicule dans la base via CNIT
        if cnit:
            from src.vehicle.types_mines import search_by_cnit, search_by_tvv
            vehicule_base = search_by_cnit(cnit)
            if not vehicule_base:
                vehicule_base = search_by_tvv(cnit)

            if vehicule_base:
                details = (
                    f"Vehicule identifie : {vehicule_base.get('marque', '')} "
                    f"{vehicule_base.get('denomination_commerciale', '')} "
                    f"| {vehicule_base.get('energie', '')} "
                    f"| {vehicule_base.get('puissance_fiscale', '')} CV "
                    f"(CNIT: {cnit})"
                )
                if immat:
                    details += f" -- Immat: {immat}"
                return {"valide": True, "details": details, "vehicule_base": vehicule_base}
            else:
                return {
                    "valide": False,
                    "motif": (
                        f"CNIT '{cnit}' non trouve dans la base. "
                        f"Marque: {marque}, Immat: {immat}. "
                        "Le vehicule devra etre selectionne manuellement."
                    ),
                }
        else:
            return {
                "valide": True,
                "details": f"Carte grise lue : {marque} {immat} (CNIT non detecte, selection manuelle necessaire)",
            }

    elif doc_key == "cni":
        # Verifier la piece d'identite (CNI, passeport ou permis)
        type_doc = donnees.get("type_document", "piece d'identite")
        date_validite = donnees.get("date_validite", "")
        nom = donnees.get("nom", "")
        prenom = donnees.get("prenom", "")
        date_naissance = donnees.get("date_naissance", "")

        TYPES_ACCEPTES = {"cni", "passeport", "permis_conduire", "permis de conduire"}
        if type_doc and type_doc.lower() not in TYPES_ACCEPTES and type_doc.lower() not in ("", "null"):
            return {"valide": False, "motif": f"Document '{type_doc}' non accepte. Acceptes : CNI, passeport, permis de conduire"}

        if not nom and not prenom:
            return {"valide": False, "motif": "Nom et prenom non detectes sur la piece d'identite"}

        if not date_naissance or date_naissance.lower() == "null":
            return {"valide": False, "motif": f"Date de naissance non detectee ({nom} {prenom})"}

        label = type_doc.upper() if type_doc else "Piece d'identite"

        if date_validite and date_validite.lower() != "null":
            d = _parse_date_simple(date_validite)
            if d and d < date.today():
                return {"valide": False, "motif": f"{label} expiree depuis le {date_validite} ({nom} {prenom})"}
            elif d:
                return {"valide": True, "details": f"{label} valide -- {nom} {prenom}, ne(e) le {date_naissance}, expire le {date_validite}"}

        return {"valide": True, "details": f"{label} reconnu(e) -- {nom} {prenom}, ne(e) le {date_naissance}"}

    elif doc_key == "justificatif_domicile":
        # Verifier le type et la date
        type_justif = donnees.get("type_justificatif", "")
        date_doc = donnees.get("date_document", "")
        adresse = donnees.get("adresse_complete", "")

        TYPES_REFUSES = {"quittance_loyer_particulier", "bail", "fiche_paie", "rib", "autre"}
        if type_justif in TYPES_REFUSES:
            return {
                "valide": False,
                "motif": (
                    f"Type '{type_justif}' non accepte par l'ANTS. "
                    "Acceptes : facture electricite/gaz/eau/telephone/internet, "
                    "avis d'imposition, attestation assurance habitation"
                ),
            }

        justif_valide = donnees.get("justificatif_valide")
        if justif_valide is False:
            return {"valide": False, "motif": donnees.get("justificatif_motif_refus", "Type non accepte")}

        if date_doc:
            d = _parse_date_simple(date_doc)
            if d:
                age_jours = (date.today() - d).days
                if age_jours > 180:
                    return {"valide": False, "motif": f"Justificatif trop ancien : {age_jours} jours (max 180)"}
                else:
                    msg = f"Justificatif valide ({age_jours} jours)"
                    if type_justif:
                        msg += f" -- type : {type_justif}"
                    if adresse:
                        msg += f" -- {adresse}"
                    return {"valide": True, "details": msg}

        msg = "Justificatif reconnu"
        if adresse:
            msg += f" -- {adresse}"
        if type_justif:
            msg += f" -- type : {type_justif}"
        return {"valide": True, "details": msg}

    elif doc_key == "certificat_cession":
        # Verifier les champs essentiels
        immat = donnees.get("immatriculation", "")
        date_cession = donnees.get("date_cession", "")
        vendeur = donnees.get("vendeur_nom", "")
        acheteur = donnees.get("acheteur_nom", "")
        marque_cession = donnees.get("marque", "") or donnees.get("type", "")
        vin_cession = donnees.get("vin", "")

        problemes = []
        if not immat:
            problemes.append("immatriculation non detectee")
        if not date_cession:
            problemes.append("date de cession non detectee")
        if not vendeur and not acheteur:
            problemes.append("vendeur et acheteur non detectes")

        # Verification de coherence avec le vehicule selectionne
        if vehicle and immat:
            # Comparer la marque si presente sur la cession
            marque_selectionnee = (vehicle.get("marque") or "").upper()
            if marque_cession and marque_selectionnee:
                if marque_selectionnee not in marque_cession.upper() and marque_cession.upper() not in marque_selectionnee:
                    problemes.append(
                        f"Marque incoherente : cession '{marque_cession}' "
                        f"vs vehicule selectionne '{vehicle.get('marque', '')}'"
                    )

        # Verification du VIN : le constructeur doit correspondre a la marque
        if vehicle and vin_cession and len(vin_cession) == 17:
            from src.vehicle.vin_decoder import decode_vin
            vin_info = decode_vin(vin_cession)
            constructeur_vin = (vin_info.get("constructeur") or "").upper()
            marque_selectionnee = (vehicle.get("marque") or "").upper()

            if constructeur_vin and constructeur_vin != "INCONNU":
                if marque_selectionnee not in constructeur_vin and constructeur_vin not in marque_selectionnee:
                    problemes.append(
                        f"VIN {vin_cession} = constructeur '{constructeur_vin}' "
                        f"mais vehicule selectionne = '{vehicle.get('marque', '')}'"
                    )

        if problemes:
            return {"valide": False, "motif": " | ".join(problemes)}

        details = f"Cession du {date_cession}"
        if immat:
            details += f" -- {immat}"
        if marque_cession:
            details += f" -- {marque_cession}"
        if vin_cession:
            details += f" -- VIN: {vin_cession}"
        if vendeur:
            details += f" -- vendeur : {vendeur}"
        if acheteur:
            details += f" -- acheteur : {acheteur}"
        if vehicle:
            from src.vehicle.vin_decoder import decode_vin as _dv
            if vin_cession and len(vin_cession) == 17:
                vi = _dv(vin_cession)
                details += f" (VIN verifie : {vi.get('constructeur', '?')}, {vi.get('pays_origine', '?')})"
        return {"valide": True, "details": details}

    return {"valide": True, "details": "Document reconnu"}


def _save_session_state():
    """Sauvegarde l'etat de la session sur disque pour persistance."""
    import json as _json
    if "dossier_travail" not in st.session_state:
        return
    state_file = Path(st.session_state.dossier_travail) / "_state.json"
    state = {
        "fichiers_sauves": st.session_state.get("fichiers_sauves", {}),
        "analyse_docs": st.session_state.get("analyse_docs", {}),
        "selected_vehicle": st.session_state.get("selected_vehicle"),
        "dossier_reference": st.session_state.get("dossier_reference", ""),
    }
    try:
        state_file.write_text(_json.dumps(state, ensure_ascii=False, default=str))
    except Exception:
        pass


def _parse_date_simple(date_str: str):
    """Parse une date en formats courants."""
    from datetime import datetime
    for fmt in ["%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d.%m.%Y"]:
        try:
            return datetime.strptime(date_str.strip(), fmt).date()
        except ValueError:
            continue
    return None


def _render_dossier_detail(dossier: dict):
    """Affiche le detail d'un dossier avec documents, taxes, CERFA et actions."""
    dossier_id = dossier["id"]

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Informations")
        st.write(f"**Reference :** {dossier['reference']}")
        st.write(f"**Statut :** {dossier['statut']}")
        st.write(f"**Client :** {dossier.get('client_nom', '--')}")
        st.write(f"**Immatriculation :** {dossier.get('immatriculation', '--')}")
        st.write(f"**VIN :** {dossier.get('vin', '--')}")
        st.write(f"**Cree le :** {dossier.get('created_at', '--')}")

    with col2:
        donnees = dossier.get("donnees_extraites")
        if donnees:
            if isinstance(donnees, str):
                donnees = json.loads(donnees)
            st.subheader("Donnees extraites")
            st.json(donnees)

    documents = get_documents_for_dossier(dossier_id)
    if documents:
        st.subheader(f"Pieces justificatives ({len(documents)})")
        for doc in documents:
            doc_col1, doc_col2, doc_col3 = st.columns([1, 1, 2])
            doc_col1.write(f"**{doc['type_document']}**")
            doc_col2.write(f"Confiance : {doc.get('confidence', 0):.0%}")
            doc_data = doc.get("donnees_json")
            if doc_data:
                if isinstance(doc_data, str):
                    doc_data = json.loads(doc_data)
                with doc_col3.expander("Donnees"):
                    st.json(doc_data)

    taxes = dossier.get("taxes")
    if taxes:
        if isinstance(taxes, str):
            taxes = json.loads(taxes)
        st.subheader("Taxes")
        tax_cols = st.columns(6)
        tax_cols[0].metric("Y1 Regionale", f"{taxes.get('Y1_taxe_regionale', 0):.2f} EUR")
        tax_cols[1].metric("Y3 Formation", f"{taxes.get('Y3_taxe_formation', 0):.2f} EUR")
        tax_cols[2].metric("Y4 CO2", f"{taxes.get('Y4_malus_co2', 0):.2f} EUR")
        tax_cols[3].metric("Y5 Masse", f"{taxes.get('Y5_malus_masse', 0):.2f} EUR")
        tax_cols[4].metric("Y6 Fixe", f"{taxes.get('Y6_taxe_fixe', 0):.2f} EUR")
        tax_cols[5].metric("TOTAL", f"{taxes.get('total', 0):.2f} EUR")

    cerfa_path = dossier.get("cerfa_path", "")
    if cerfa_path and Path(cerfa_path).exists():
        st.subheader("CERFA genere")
        with open(cerfa_path, "rb") as f:
            st.download_button(
                "Telecharger le CERFA 13750",
                data=f.read(),
                file_name=Path(cerfa_path).name,
                mime="application/pdf",
                key=f"dl_cerfa_{dossier_id}",
            )

    st.subheader("Actions")
    action_cols = st.columns(4)

    if dossier["statut"] == "pret":
        if action_cols[0].button("Valider le dossier", key=f"validate_{dossier_id}"):
            update_dossier_status(dossier_id, "valide")
            st.success("Dossier valide !")
            st.rerun()

    if dossier["statut"] == "valide":
        if action_cols[0].button("Marquer comme envoye", key=f"send_{dossier_id}"):
            update_dossier_status(dossier_id, "envoye")
            st.success("Dossier marque comme envoye.")
            st.rerun()

    if action_cols[1].button("Remettre en attente", key=f"reset_{dossier_id}"):
        update_dossier_status(dossier_id, "nouveau")
        st.rerun()

    if action_cols[2].button("Supprimer", key=f"delete_{dossier_id}"):
        st.session_state[f"confirm_delete_{dossier_id}"] = True

    if st.session_state.get(f"confirm_delete_{dossier_id}"):
        st.warning("Etes-vous sur de vouloir supprimer ce dossier ?")
        col_yes, col_no = st.columns(2)
        if col_yes.button("Oui, supprimer", key=f"confirm_yes_{dossier_id}"):
            from src.pipeline.orchestrator import delete_dossier
            delete_dossier(dossier_id)
            st.session_state.pop(f"confirm_delete_{dossier_id}", None)
            st.rerun()
        if col_no.button("Annuler", key=f"confirm_no_{dossier_id}"):
            st.session_state.pop(f"confirm_delete_{dossier_id}", None)
            st.rerun()


# =============================================
# PAGE : DEPOSER DES DOCUMENTS
# =============================================
if page == "Deposer des documents":

    from src.vehicle.types_mines import search_by_marque_modele

    st.title("Nouveau dossier carte grise")

    # Dossier de travail en cours (sauvegarde les fichiers sur disque)
    if "dossier_travail" not in st.session_state:
        from datetime import datetime
        from config.settings import DOSSIERS_DIR
        ref = f"CG-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        work_dir = DOSSIERS_DIR / ref
        work_dir.mkdir(parents=True, exist_ok=True)
        st.session_state.dossier_travail = str(work_dir)
        st.session_state.dossier_reference = ref

    if st.button("Reinitialiser -- Nouveau dossier"):
        for key in ["selected_vehicle", "analyse_docs", "_search_results",
                     "_search_query", "_search_results_occasion",
                     "dossier_travail", "dossier_reference", "fichiers_sauves"]:
            st.session_state.pop(key, None)
        st.rerun()

    # Fichiers deja sauves sur disque — persister dans un fichier JSON
    import json as _json
    _state_file = Path(st.session_state.dossier_travail) / "_state.json"

    if "fichiers_sauves" not in st.session_state:
        # Essayer de charger l'etat sauve
        if _state_file.exists():
            try:
                _saved = _json.loads(_state_file.read_text())
                st.session_state.fichiers_sauves = _saved.get("fichiers_sauves", {})
                st.session_state.analyse_docs = _saved.get("analyse_docs", {})
                if _saved.get("selected_vehicle"):
                    st.session_state.selected_vehicle = _saved["selected_vehicle"]
                if _saved.get("dossier_reference"):
                    st.session_state.dossier_reference = _saved["dossier_reference"]
            except Exception:
                st.session_state.fichiers_sauves = {}
        else:
            st.session_state.fichiers_sauves = {}

    # Type de demande
    type_demande = st.radio(
        "Type de demande",
        ["Achat occasion", "Vehicule neuf"],
        horizontal=True,
    )

    st.divider()

    # Initialiser la session
    if "selected_vehicle" not in st.session_state:
        st.session_state.selected_vehicle = None
    if "analyse_docs" not in st.session_state:
        st.session_state.analyse_docs = {}

    is_occasion = (type_demande == "Achat occasion")
    docs_requis = _get_documents_requis("VP", is_occasion)

    # =======================================================
    # FLUX OCCASION : documents d'abord, vehicule auto-detecte
    # =======================================================
    if is_occasion:

        # --- ETAPE 1 : Depot des documents ---
        st.header("1. Deposer les documents du client")

        nb_fournis = 0
        nb_total = len(docs_requis)
        fichiers_deposes = {}
        work_dir = Path(st.session_state.dossier_travail)

        # Detecter les fichiers deja sur disque au demarrage
        if not st.session_state.fichiers_sauves and work_dir.exists():
            existing = [f for f in work_dir.iterdir() if f.is_file() and f.suffix.lower() in {".pdf", ".jpg", ".jpeg", ".png", ".tif", ".tiff"}]
            if existing:
                # Essayer de re-associer les fichiers aux types de documents
                # (on ne peut pas deviner, mais on garde les noms)
                pass

        for doc_key, doc_info in docs_requis.items():
            deja_depose = doc_key in st.session_state.fichiers_sauves
            fname_sauve = st.session_state.fichiers_sauves.get(doc_key, "")
            fpath_sauve = work_dir / fname_sauve if fname_sauve else None

            st.write(f"**{doc_info['label']}**")
            st.caption(doc_info["description"])

            if deja_depose and fpath_sauve and fpath_sauve.exists():
                # Fichier deja sur disque — pas besoin de re-deposer
                st.write(f"Fichier : *{fname_sauve}* (deja depose)")
                fichiers_deposes[doc_key] = None
                nb_fournis += 1

                # Bouton pour remplacer le fichier
                if st.checkbox(f"Remplacer {fname_sauve}", key=f"replace_{doc_key}"):
                    fichier = st.file_uploader(
                        f"Nouveau fichier pour {doc_info['label']}",
                        type=["pdf", "jpg", "jpeg", "png", "tif", "tiff"],
                        key=f"upload_replace_{doc_key}",
                        label_visibility="collapsed",
                    )
                    if fichier:
                        filepath = work_dir / fichier.name
                        with open(filepath, "wb") as out:
                            out.write(fichier.getbuffer())
                        # Supprimer l'ancien
                        if fpath_sauve.exists() and fpath_sauve.name != fichier.name:
                            fpath_sauve.unlink()
                        st.session_state.fichiers_sauves[doc_key] = fichier.name
                        st.session_state.analyse_docs.pop(doc_key, None)
                        fichiers_deposes[doc_key] = fichier
                        st.rerun()
            else:
                # Pas encore depose — afficher l'uploader
                fichier = st.file_uploader(
                    f"Deposer : {doc_info['label']}",
                    type=["pdf", "jpg", "jpeg", "png", "tif", "tiff"],
                    key=f"upload_{doc_key}",
                    label_visibility="collapsed",
                )
                if fichier:
                    filepath = work_dir / fichier.name
                    if not filepath.exists():
                        with open(filepath, "wb") as out:
                            out.write(fichier.getbuffer())
                    st.session_state.fichiers_sauves[doc_key] = fichier.name
                    _save_session_state()
                    fichiers_deposes[doc_key] = fichier
                    nb_fournis += 1

            # Afficher resultat d'analyse si disponible
            analyse = st.session_state.analyse_docs.get(doc_key)
            if analyse:
                validite = analyse.get("validite", {})
                if validite.get("valide", True):
                    st.success(validite.get("details", "Document valide"))
                else:
                    st.error(validite.get("motif", "Probleme detecte"))

                donnees = analyse.get("donnees", {})
                donnees_utiles = {
                    k: val for k, val in donnees.items()
                    if not k.startswith("_") and val is not None
                    and str(val).strip() and str(val).strip().lower() != "null"
                }
                if donnees_utiles:
                    with st.expander(f"Donnees extraites"):
                        for k, val in donnees_utiles.items():
                            st.write(f"**{k}** : {val}")
            elif deja_depose and not analyse:
                st.info(f"{fname_sauve} -- cliquez 'Verifier' ci-dessous")

        # Bouton de verification
        docs_a_verifier = [
            k for k in fichiers_deposes
            if k not in st.session_state.analyse_docs
            and (fichiers_deposes[k] is not None or k in st.session_state.fichiers_sauves)
        ]

        if docs_a_verifier:
            if st.button("Verifier les documents", type="primary"):
                for i, doc_key in enumerate(docs_a_verifier):
                    fichier = fichiers_deposes.get(doc_key)
                    label = docs_requis[doc_key]["label"]
                    with st.spinner(f"Verification {i+1}/{len(docs_a_verifier)} : {label}..."):
                        if fichier and hasattr(fichier, 'getbuffer'):
                            analyse = _analyser_document(doc_key, fichier, vehicle=st.session_state.selected_vehicle)
                        elif doc_key in st.session_state.fichiers_sauves:
                            # Fichier deja sur disque, creer un objet fichier temporaire
                            work_dir = Path(st.session_state.dossier_travail)
                            fpath = work_dir / st.session_state.fichiers_sauves[doc_key]
                            if fpath.exists():
                                from io import BytesIO
                                class FakeFile:
                                    def __init__(self, path):
                                        self.name = path.name
                                        self._data = path.read_bytes()
                                    def getbuffer(self):
                                        return self._data
                                analyse = _analyser_document(doc_key, FakeFile(fpath), vehicle=st.session_state.selected_vehicle)
                            else:
                                continue
                        else:
                            continue
                        st.session_state.analyse_docs[doc_key] = analyse
                _save_session_state()
                st.rerun()

        # Verifications croisees entre documents
        analyse_cg = st.session_state.analyse_docs.get("carte_grise_vendeur", {})
        analyse_cession = st.session_state.analyse_docs.get("certificat_cession", {})
        analyse_cni = st.session_state.analyse_docs.get("cni", {})

        st.subheader("Verifications croisees")
        has_cross_check = False

        # VIN carte grise vs VIN cession
        if analyse_cg.get("donnees") and analyse_cession.get("donnees"):
            vin_cg = (analyse_cg["donnees"].get("E_vin") or "").upper().strip()
            vin_cession = (analyse_cession["donnees"].get("vin") or "").upper().strip()
            if vin_cg and vin_cession:
                has_cross_check = True
                if vin_cg == vin_cession:
                    st.success(f"VIN coherent : carte grise et cession = **{vin_cg}**")
                else:
                    st.error(f"VIN incoherent : carte grise **{vin_cg}** != cession **{vin_cession}**")

            # Immatriculation carte grise vs cession
            immat_cg = (analyse_cg["donnees"].get("A_immatriculation") or "").upper().replace("-", "").replace(" ", "")
            immat_cession = (analyse_cession["donnees"].get("immatriculation") or "").upper().replace("-", "").replace(" ", "")
            if immat_cg and immat_cession:
                has_cross_check = True
                if immat_cg == immat_cession:
                    st.success(f"Immatriculation coherente : **{analyse_cg['donnees'].get('A_immatriculation', '')}**")
                else:
                    st.error(
                        f"Immatriculation incoherente : carte grise **{analyse_cg['donnees'].get('A_immatriculation', '')}** "
                        f"!= cession **{analyse_cession['donnees'].get('immatriculation', '')}**"
                    )

        # CNI vs cession (nom acheteur)
        if analyse_cni.get("donnees") and analyse_cession.get("donnees"):
            cni_nom = (analyse_cni["donnees"].get("nom") or "").upper().strip()
            cession_acheteur = (analyse_cession["donnees"].get("acheteur_nom") or "").upper().strip()
            if cni_nom and cession_acheteur:
                has_cross_check = True
                match = cni_nom in cession_acheteur or cession_acheteur in cni_nom
                if match:
                    st.success(f"Nom coherent : CNI **{cni_nom}** = acheteur **{cession_acheteur}**")
                else:
                    st.error(f"Nom incoherent : CNI **{cni_nom}** != acheteur cession **{cession_acheteur}**")

        # Documents vs vehicule selectionne dans la base
        if st.session_state.selected_vehicle and (analyse_cg.get("donnees") or analyse_cession.get("donnees")):
            v_base = st.session_state.selected_vehicle
            marque_base = (v_base.get("marque") or "").upper()

            # Marque carte grise vs base
            if analyse_cg.get("donnees"):
                marque_cg = (analyse_cg["donnees"].get("D1_marque") or "").upper()
                if marque_cg and marque_base:
                    has_cross_check = True
                    if marque_base in marque_cg or marque_cg in marque_base:
                        st.success(f"Marque coherente : carte grise **{marque_cg}** = base **{marque_base}**")
                    else:
                        st.error(f"Marque incoherente : carte grise **{marque_cg}** != base **{marque_base}**")

                # Energie carte grise vs base
                energie_cg = (analyse_cg["donnees"].get("P3_energie") or "").upper()
                energie_base = (v_base.get("energie") or "").upper()
                if energie_cg and energie_base:
                    has_cross_check = True
                    if energie_cg == energie_base:
                        st.success(f"Energie coherente : **{energie_base}**")
                    else:
                        st.error(f"Energie incoherente : carte grise **{energie_cg}** != base **{energie_base}**")

            # VIN cession vs constructeur base
            if analyse_cession.get("donnees"):
                vin = (analyse_cession["donnees"].get("vin") or "").upper()
                if vin and len(vin) == 17 and marque_base:
                    has_cross_check = True
                    from src.vehicle.vin_decoder import decode_vin
                    vin_info = decode_vin(vin)
                    constructeur_vin = (vin_info.get("constructeur") or "").upper()
                    if constructeur_vin and constructeur_vin != "INCONNU":
                        if marque_base in constructeur_vin or constructeur_vin in marque_base:
                            st.success(f"VIN **{vin}** = constructeur **{constructeur_vin}** = base **{marque_base}**")
                        else:
                            st.error(f"VIN **{vin}** = constructeur **{constructeur_vin}** != base **{marque_base}**")

        if not has_cross_check:
            st.info("Les verifications croisees apparaitront une fois les documents analyses.")

        # Bilan documents
        nb_manquants = nb_total - nb_fournis
        st.divider()
        if nb_fournis == 0:
            st.info("Deposez vos documents ci-dessus.")
        elif nb_manquants == 0:
            st.success(f"Documents complets ({nb_fournis}/{nb_total})")
        else:
            manquants = [info["label"] for key, info in docs_requis.items() if key not in fichiers_deposes]
            st.warning(f"{nb_fournis}/{nb_total} documents. Manquant(s) : {', '.join(manquants)}")

        # --- ETAPE 2 : Selection du vehicule (auto-detecte depuis la carte grise vendeur) ---
        st.header("2. Vehicule")

        analyse_cg = st.session_state.analyse_docs.get("carte_grise_vendeur", {})

        if analyse_cg.get("donnees") and analyse_cg.get("validite", {}).get("vehicule_base"):
            # Vehicule trouve automatiquement via CNIT
            if st.session_state.selected_vehicle is None:
                vehicule_base = analyse_cg["validite"]["vehicule_base"]
                st.session_state.selected_vehicle = vehicule_base

        elif analyse_cg.get("donnees") and st.session_state.selected_vehicle is None:
            # CNIT non trouve — fallback recherche manuelle par marque/modele
            cg_data = analyse_cg["donnees"]
            marque_cg = cg_data.get("D1_marque", "")
            denom_cg = cg_data.get("D3_denomination", "")

            if marque_cg:
                st.write(f"CNIT non trouve dans la base. Vehicule detecte : **{marque_cg} {denom_cg}**")
                st.write("Selectionnez la bonne version :")

                resultats = search_by_marque_modele(marque_cg, denom_cg)
                if resultats:
                    options = [
                        f"{v.get('marque', '')} {v.get('denomination_commerciale', '')} "
                        f"| {v.get('energie', '')} | {v.get('puissance_fiscale', '')} CV "
                        f"| {v.get('cylindree', '')} cm3 | CO2: {v.get('co2', '--')} g/km"
                        for v in resultats
                    ]
                    choix = st.selectbox("Selectionnez :", options)
                    idx = options.index(choix)
                    if st.button("Valider ce vehicule", type="primary"):
                        st.session_state.selected_vehicle = resultats[idx]
                        st.rerun()
                else:
                    st.warning(f"Aucun vehicule trouve pour '{marque_cg} {denom_cg}'.")
                    col_m, col_mod = st.columns(2)
                    search_m = col_m.text_input("Marque", value=marque_cg, key="manual_marque")
                    search_mod = col_mod.text_input("Modele", value=denom_cg, key="manual_modele")
                    if st.button("Rechercher"):
                        st.session_state._search_results_occasion = search_by_marque_modele(search_m, search_mod)
                        st.rerun()
                    if "_search_results_occasion" in st.session_state and st.session_state._search_results_occasion:
                        res = st.session_state._search_results_occasion
                        opts = [
                            f"{v.get('marque', '')} {v.get('denomination_commerciale', '')} "
                            f"| {v.get('energie', '')} | {v.get('puissance_fiscale', '')} CV"
                            for v in res
                        ]
                        choix2 = st.selectbox("Selectionnez :", opts, key="manual_select")
                        idx2 = opts.index(choix2)
                        if st.button("Valider", key="manual_validate"):
                            st.session_state.selected_vehicle = res[idx2]
                            st.session_state.pop("_search_results_occasion", None)
                            st.rerun()

        elif "carte_grise_vendeur" in fichiers_deposes and "carte_grise_vendeur" not in st.session_state.analyse_docs:
            st.info("Cliquez 'Verifier les documents' pour identifier le vehicule depuis la carte grise.")
        elif "carte_grise_vendeur" not in fichiers_deposes:
            st.info("Deposez l'ancienne carte grise du vendeur pour identifier le vehicule.")

        # Afficher le vehicule selectionne
        if st.session_state.selected_vehicle:
            v = st.session_state.selected_vehicle
            st.success(
                f"Vehicule : **{v.get('marque', '')} {v.get('denomination_commerciale', '')}** "
                f"| {v.get('energie', '')} | {v.get('puissance_fiscale', '')} CV "
                f"| {v.get('cylindree', '')} cm3"
            )
            with st.expander("Fiche technique complete", expanded=False):
                tc = st.columns(3)
                tc[0].write(f"**Marque :** {v.get('marque', '')}")
                tc[0].write(f"**Denomination :** {v.get('denomination_commerciale', '')}")
                tc[0].write(f"**Genre :** {v.get('genre', '')}")
                tc[0].write(f"**CNIT :** {v.get('cnit', '')}")
                tc[1].write(f"**Energie :** {v.get('energie', '')}")
                tc[1].write(f"**Cylindree :** {v.get('cylindree', '')} cm3")
                tc[1].write(f"**Puissance fiscale :** {v.get('puissance_fiscale', '')} CV")
                tc[1].write(f"**Puissance kW :** {v.get('puissance_kw', '')}")
                tc[2].write(f"**CO2 :** {v.get('co2', '--')} g/km")
                tc[2].write(f"**Nb places :** {v.get('nb_places', '')}")
                tc[2].write(f"**Poids vide :** {v.get('poids_vide', '')} kg")

            if st.button("Changer de vehicule"):
                st.session_state.selected_vehicle = None
                st.rerun()

        st.divider()

    # =======================================================
    # FLUX NEUF : selection vehicule d'abord
    # =======================================================
    else:

        # --- ETAPE 1 : Recherche du vehicule ---
        st.header("1. Rechercher le vehicule")
        st.write("Tapez la marque et/ou le modele du vehicule neuf.")

        if st.session_state.selected_vehicle is None:
            col_marque, col_modele, col_btn = st.columns([2, 2, 1])
            search_marque = col_marque.text_input("Marque", placeholder="Ex : Peugeot, Renault, BMW...")
            search_modele = col_modele.text_input("Modele", placeholder="Ex : 308, Clio, Serie 3...")
            col_btn.write("")
            col_btn.write("")
            do_search = col_btn.button("Rechercher", type="primary")

            if do_search and search_marque:
                resultats = search_by_marque_modele(search_marque, search_modele)
                st.session_state._search_results = resultats
                st.session_state._search_query = f"{search_marque} {search_modele}"

            resultats = st.session_state.get("_search_results", [])
            query = st.session_state.get("_search_query", "")

            if query and not resultats:
                st.warning(f"Aucun vehicule trouve pour '{query}'.")
            elif resultats:
                st.write(f"**{len(resultats)} resultat(s) :**")
                options = [
                    f"{v.get('marque', '')} {v.get('denomination_commerciale', '')} "
                    f"| {v.get('energie', '')} | {v.get('puissance_fiscale', '')} CV "
                    f"| {v.get('cylindree', '')} cm3 | CO2: {v.get('co2', '--')} g/km"
                    for v in resultats
                ]
                choix = st.selectbox("Selectionnez le vehicule :", options)
                idx = options.index(choix)

                if st.button("Valider ce vehicule", type="primary"):
                    st.session_state.selected_vehicle = resultats[idx]
                    st.session_state.pop("_search_results", None)
                    st.session_state.pop("_search_query", None)
                    st.rerun()
        else:
            st.info("Commencez par rechercher le vehicule.")

        if st.session_state.selected_vehicle:
            v = st.session_state.selected_vehicle
            st.success(
                f"Vehicule : **{v.get('marque', '')} {v.get('denomination_commerciale', '')}** "
                f"| {v.get('energie', '')} | {v.get('puissance_fiscale', '')} CV"
            )
            if st.button("Changer de vehicule"):
                st.session_state.selected_vehicle = None
                st.rerun()

            st.divider()

            # --- ETAPE 2 : Documents ---
            st.header("2. Deposer les documents du client")

            nb_fournis = 0
            nb_total = len(docs_requis)
            fichiers_deposes = {}

            for doc_key, doc_info in docs_requis.items():
                st.write(f"**{doc_info['label']}**")
                st.caption(doc_info["description"])
                fichier = st.file_uploader(
                    f"Deposer : {doc_info['label']}",
                    type=["pdf", "jpg", "jpeg", "png", "tif", "tiff"],
                    key=f"upload_{doc_key}",
                    label_visibility="collapsed",
                )
                if fichier:
                    fichiers_deposes[doc_key] = fichier
                    nb_fournis += 1

                    analyse = st.session_state.analyse_docs.get(doc_key)
                    if analyse and analyse.get("fichier") == fichier.name:
                        validite = analyse.get("validite", {})
                        if validite.get("valide", True):
                            st.success(validite.get("details", "Document valide"))
                        else:
                            st.error(validite.get("motif", "Probleme detecte"))
                    else:
                        st.info(f"{fichier.name} depose -- cliquez 'Verifier' ci-dessous")
                else:
                    st.session_state.analyse_docs.pop(doc_key, None)

            if fichiers_deposes:
                docs_non = [k for k, f in fichiers_deposes.items()
                            if k not in st.session_state.analyse_docs
                            or st.session_state.analyse_docs[k].get("fichier") != f.name]
                if docs_non and st.button("Verifier les documents", type="primary"):
                    for i, dk in enumerate(docs_non):
                        with st.spinner(f"Verification {i+1}/{len(docs_non)}..."):
                            st.session_state.analyse_docs[dk] = _analyser_document(dk, fichiers_deposes[dk], vehicle=v)
                    st.rerun()

            nb_manquants = nb_total - nb_fournis
            st.divider()

    # =======================================================
    # ETAPE FINALE : Lancer le traitement (commun aux 2 flux)
    # =======================================================
    if st.session_state.selected_vehicle and nb_fournis > 0:
        st.header("Lancer le traitement")

        # Couleur du vehicule (saisie manuelle)
        couleurs = ["", "Noir", "Blanc", "Gris", "Bleu", "Rouge", "Vert",
                     "Jaune", "Orange", "Marron", "Beige"]
        col_couleur, col_teinte = st.columns(2)
        couleur = col_couleur.selectbox("Couleur du vehicule", couleurs)
        teinte = col_teinte.selectbox("Teinte", ["", "Clair", "Fonce"])

        if nb_manquants > 0:
            st.info("Vous pouvez lancer meme avec des documents manquants.")

        if st.button("Lancer le traitement", type="primary", key="btn_traitement"):
            # Utiliser le dossier de travail existant (fichiers deja sauves)
            dossier_path = Path(st.session_state.dossier_travail)
            reference = st.session_state.dossier_reference

            # Sauvegarder les fichiers qui ne le sont pas encore
            for doc_key in docs_requis:
                fichier = fichiers_deposes.get(doc_key)
                if fichier and hasattr(fichier, 'getbuffer'):
                    filepath = dossier_path / fichier.name
                    if not filepath.exists():
                        with open(filepath, "wb") as out:
                            out.write(fichier.getbuffer())

            with st.spinner("Traitement en cours (validation, taxes, CERFA)..."):
                from src.pipeline.orchestrator import process_dossier

                pre_extracted = {}
                for doc_key, analyse in st.session_state.analyse_docs.items():
                    if analyse.get("donnees"):
                        pre_extracted[doc_key] = analyse["donnees"]

                try:
                    vehicle_data = dict(st.session_state.selected_vehicle)
                    vehicle_data["couleur"] = couleur.lower() if couleur else ""
                    vehicle_data["teinte"] = teinte.lower() if teinte else ""

                    result = process_dossier(
                        dossier_path,
                        vehicle_override=vehicle_data,
                        pre_extracted=pre_extracted if pre_extracted else None,
                    )
                    if result.get("status") == "pret":
                        st.success(
                            f"Dossier {reference} traite avec succes ! "
                            f"Vehicule : {result['vehicule']['marque']} "
                            f"{result['vehicule']['denomination']} "
                            f"({result.get('immatriculation', '')})"
                        )
                        st.info("Retrouvez le dossier dans l'onglet **Dossiers clients**.")
                        if st.button("Cloturer et nouveau dossier"):
                            for key in ["selected_vehicle", "analyse_docs", "_search_results",
                                         "_search_query", "_search_results_occasion",
                                         "dossier_travail", "dossier_reference", "fichiers_sauves"]:
                                st.session_state.pop(key, None)
                            st.rerun()
                    elif result.get("status") == "documents_manquants":
                        st.warning("Dossier incomplet.")
                        validation = result.get("validation", {})
                        for err in validation.get("errors", []):
                            st.error(err)
                    else:
                        st.error(f"Erreur : {result.get('error', 'inconnue')}")
                except Exception as e:
                    st.error(f"Erreur : {e}")


# =============================================
# PAGE : DOSSIERS CLIENTS
# =============================================
elif page == "Dossiers clients":
    st.title("Dossiers clients")

    # Recherche par nom, reference ou immatriculation
    search_query = st.text_input(
        "Rechercher un dossier",
        placeholder="Nom du client, reference ou immatriculation...",
    )

    # Filtre par statut
    col_filtre, col_info = st.columns([2, 3])
    statuts = ["tous", "nouveau", "en_cours", "documents_manquants", "pret", "valide", "envoye"]
    labels = {
        "tous": "Tous les dossiers",
        "nouveau": "Nouveaux",
        "en_cours": "En cours",
        "documents_manquants": "Incomplets",
        "pret": "A valider",
        "valide": "Valides",
        "envoye": "Envoyes",
    }
    selected_statut = col_filtre.selectbox(
        "Statut",
        statuts,
        format_func=lambda x: labels.get(x, x),
    )

    # Recuperer les dossiers
    if search_query:
        dossiers = search_dossiers(search_query)
        if selected_statut != "tous":
            dossiers = [d for d in dossiers if d.get("statut") == selected_statut]
    elif selected_statut == "tous":
        dossiers = get_all_dossiers()
    else:
        dossiers = get_dossiers_by_status(selected_statut)

    col_info.write(f"**{len(dossiers)} dossier(s)**")

    if not dossiers:
        if search_query:
            st.info(f"Aucun dossier trouve pour '{search_query}'.")
        else:
            st.info("Aucun dossier.")
    else:
        for dossier in dossiers:
            client = dossier.get("client_nom") or "Client inconnu"
            immat = dossier.get("immatriculation") or "?"
            statut = dossier.get("statut", "")
            ref = dossier.get("reference", "")

            with st.expander(
                f"**{client}** -- {immat} -- {ref} ({labels.get(statut, statut)})",
                expanded=False,
            ):
                _render_dossier_detail(dossier)


# =============================================
# PAGE : PARAMETRES
# =============================================
elif page == "Parametres":
    st.title("Parametres")

    # --- Expediteurs autorises ---
    st.header("Expediteurs autorises")
    st.write(
        "Seuls les emails provenant de ces adresses seront traites. "
        "Ajoutez les adresses des personnes habilitees."
    )

    from config.settings import EXPEDITEURS_AUTORISES_FILE

    expediteurs = []
    if EXPEDITEURS_AUTORISES_FILE.exists():
        with open(EXPEDITEURS_AUTORISES_FILE, "r") as f:
            expediteurs = [
                line.strip() for line in f
                if line.strip() and not line.strip().startswith("#")
            ]

    if not expediteurs:
        st.warning(
            "Aucun expediteur configure. Le systeme ignorera TOUS les emails recus. "
            "Ajoutez au moins une adresse ci-dessous."
        )
    else:
        st.write(f"**{len(expediteurs)} expediteur(s) configure(s) :**")
        for i, exp in enumerate(expediteurs):
            cols = st.columns([4, 1])
            cols[0].write(f"**{exp}**")
            if cols[1].button("Supprimer", key=f"del_exp_{i}"):
                expediteurs.pop(i)
                with open(EXPEDITEURS_AUTORISES_FILE, "w") as f:
                    f.write("# Expediteurs autorises - une adresse email par ligne\n")
                    for e in expediteurs:
                        f.write(f"{e}\n")
                st.success(f"{exp} supprime.")
                st.rerun()

    new_email = st.text_input("Ajouter un expediteur (adresse email)")

    if st.button("Ajouter"):
        if new_email and "@" in new_email:
            new_email = new_email.strip().lower()
            if new_email in [e.lower() for e in expediteurs]:
                st.warning("Cette adresse est deja dans la liste.")
            else:
                if not EXPEDITEURS_AUTORISES_FILE.exists():
                    EXPEDITEURS_AUTORISES_FILE.parent.mkdir(parents=True, exist_ok=True)
                    with open(EXPEDITEURS_AUTORISES_FILE, "w") as f:
                        f.write("# Expediteurs autorises - une adresse email par ligne\n")

                with open(EXPEDITEURS_AUTORISES_FILE, "a") as f:
                    f.write(f"{new_email}\n")
                st.success(f"{new_email} ajoute !")
                st.rerun()
        else:
            st.error("Adresse email invalide.")

    # --- Gestion stock (optionnel) ---
    st.divider()
    st.header("Options")
    show_stock = st.checkbox(
        "Activer la gestion de stock vehicules",
        value=False,
        help="Uniquement si vous gerez un stock de vehicules propre.",
    )

    if show_stock:
        st.subheader("Stock vehicules")
        from src.vehicle.stock import list_stock, add_vehicle

        tab_list, tab_add = st.tabs(["Liste du stock", "Ajouter un vehicule"])

        with tab_list:
            statut_stock = st.selectbox("Statut", ["en_stock", "vendu", "reserve", "en_cours_cg"])
            vehicules = list_stock(statut_stock)

            if not vehicules:
                st.info(f"Aucun vehicule avec le statut '{statut_stock}'.")
            else:
                st.write(f"**{len(vehicules)} vehicule(s)**")
                for v in vehicules:
                    cols = st.columns([2, 2, 2, 1, 1])
                    cols[0].write(f"**{v['marque']}** {v['modele']}")
                    cols[1].write(v["immatriculation"] or "--")
                    cols[2].write(v["vin"])
                    cols[3].write(f"{v['km'] or 0} km")
                    cols[4].write(f"{v['prix_vente'] or 0} EUR")

        with tab_add:
            with st.form("add_vehicle"):
                col1, col2 = st.columns(2)
                vin = col1.text_input("VIN (17 caracteres)", max_chars=17)
                immat = col2.text_input("Immatriculation")
                marque = col1.text_input("Marque")
                modele = col2.text_input("Modele")
                km = col1.number_input("Kilometrage", min_value=0, value=0)
                prix = col2.number_input("Prix de vente (EUR)", min_value=0.0, value=0.0)

                if st.form_submit_button("Ajouter au stock"):
                    if vin and marque:
                        try:
                            vid = add_vehicle(vin=vin, immatriculation=immat, marque=marque, modele=modele, km=km, prix_vente=prix)
                            st.success(f"Vehicule ajoute (id={vid})")
                        except Exception as e:
                            st.error(f"Erreur : {e}")
                    else:
                        st.warning("VIN et marque sont obligatoires.")



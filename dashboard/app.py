"""Dashboard Streamlit — Interface opérateur validation dossiers carte grise."""

import json
import sys
from pathlib import Path

import streamlit as st

# Ajouter le répertoire racine au path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.pipeline.orchestrator import (
    get_dossiers_by_status,
    get_dossier,
    get_documents_for_dossier,
    update_dossier_status,
    update_dossier_data,
)
from src.taxes.calculator import calculer_taxes, get_regions
from src.cerfa.filler import fill_cerfa_from_dossier

# --- Configuration page ---
st.set_page_config(
    page_title="Carte Grise Auto",
    page_icon="🚗",  # noqa
    layout="wide",
)

# --- Sidebar : Navigation ---
st.sidebar.title("Carte Grise Auto")

# Option stock véhicule (désactivé par défaut — on est intermédiaire)
show_stock = st.sidebar.checkbox("Activer gestion stock", value=False,
    help="Activer uniquement si vous gérez un stock de véhicules propre.")

pages = ["Dossiers", "Nouveau traitement"]
if show_stock:
    pages.append("Stock véhicules")

page = st.sidebar.radio("Navigation", pages)


# =============================================
# PAGE : DOSSIERS
# =============================================
if page == "Dossiers":
    st.title("Dossiers carte grise")

    # Filtres par statut
    col_filters = st.columns(6)
    statuts = ["nouveau", "en_cours", "documents_manquants", "pret", "valide", "envoye"]
    labels = {
        "nouveau": "Nouveaux",
        "en_cours": "En cours",
        "documents_manquants": "Incomplets",
        "pret": "A valider",
        "valide": "Validés",
        "envoye": "Envoyés",
    }

    selected_statut = st.selectbox(
        "Filtrer par statut",
        statuts,
        format_func=lambda x: labels.get(x, x),
        index=3,  # "pret" par défaut
    )

    # Liste des dossiers
    dossiers = get_dossiers_by_status(selected_statut)

    if not dossiers:
        st.info(f"Aucun dossier avec le statut '{labels[selected_statut]}'.")
    else:
        st.write(f"**{len(dossiers)} dossier(s)**")

        for dossier in dossiers:
            with st.expander(
                f"**{dossier['reference']}** — {dossier.get('immatriculation', '?')} — "
                f"{dossier.get('client_nom', 'Client inconnu')}",
                expanded=False,
            ):
                _render_dossier_detail(dossier)


# =============================================
# PAGE : NOUVEAU TRAITEMENT
# =============================================
elif page == "Nouveau traitement":
    st.title("Traiter un nouveau dossier")
    st.write("Importez les documents d'un dossier pour lancer le traitement automatique.")

    uploaded_files = st.file_uploader(
        "Documents du dossier (carte grise, CNI, cession, justificatif...)",
        type=["pdf", "jpg", "jpeg", "png", "tif", "tiff"],
        accept_multiple_files=True,
    )

    if uploaded_files and st.button("Lancer le traitement"):
        # Sauvegarder les fichiers dans un dossier temporaire
        from datetime import datetime
        from config.settings import DOSSIERS_DIR

        reference = f"CG-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        dossier_path = DOSSIERS_DIR / reference
        dossier_path.mkdir(parents=True, exist_ok=True)

        for f in uploaded_files:
            filepath = dossier_path / f.name
            with open(filepath, "wb") as out:
                out.write(f.getbuffer())

        st.info(f"Dossier {reference} créé avec {len(uploaded_files)} fichier(s).")
        st.write(f"Chemin : `{dossier_path}`")

        # Lancer le traitement
        with st.spinner("Traitement en cours (classification, OCR, extraction, validation)..."):
            from src.pipeline.orchestrator import process_dossier

            try:
                result = process_dossier(dossier_path)
                if result.get("status") == "pret":
                    st.success(
                        f"Dossier traité avec succès ! "
                        f"Véhicule : {result['vehicule']['marque']} {result['vehicule']['denomination']} "
                        f"({result.get('immatriculation', '')})"
                    )
                    st.json(result)
                elif result.get("status") == "documents_manquants":
                    st.warning("Dossier incomplet ou incohérent.")
                    st.json(result.get("validation", {}))
                else:
                    st.error("Erreur de traitement.")
                    st.json(result)
            except Exception as e:
                st.error(f"Erreur : {e}")


# =============================================
# PAGE : STOCK VEHICULES
# =============================================
elif page == "Stock véhicules":
    st.title("Stock véhicules")

    from src.vehicle.stock import list_stock, add_vehicle, update_status

    tab_list, tab_add = st.tabs(["Liste du stock", "Ajouter un véhicule"])

    with tab_list:
        statut_stock = st.selectbox("Statut", ["en_stock", "vendu", "reserve", "en_cours_cg"])
        vehicules = list_stock(statut_stock)

        if not vehicules:
            st.info(f"Aucun véhicule avec le statut '{statut_stock}'.")
        else:
            st.write(f"**{len(vehicules)} véhicule(s)**")
            for v in vehicules:
                cols = st.columns([2, 2, 2, 1, 1])
                cols[0].write(f"**{v['marque']}** {v['modele']}")
                cols[1].write(v["immatriculation"] or "—")
                cols[2].write(v["vin"])
                cols[3].write(f"{v['km'] or 0} km")
                cols[4].write(f"{v['prix_vente'] or 0} EUR")

    with tab_add:
        with st.form("add_vehicle"):
            col1, col2 = st.columns(2)
            vin = col1.text_input("VIN (17 caractères)", max_chars=17)
            immat = col2.text_input("Immatriculation")
            marque = col1.text_input("Marque")
            modele = col2.text_input("Modèle")
            km = col1.number_input("Kilométrage", min_value=0, value=0)
            prix = col2.number_input("Prix de vente (EUR)", min_value=0.0, value=0.0)

            if st.form_submit_button("Ajouter au stock"):
                if vin and marque:
                    try:
                        vid = add_vehicle(vin=vin, immatriculation=immat, marque=marque, modele=modele, km=km, prix_vente=prix)
                        st.success(f"Véhicule ajouté (id={vid})")
                    except Exception as e:
                        st.error(f"Erreur : {e}")
                else:
                    st.warning("VIN et marque sont obligatoires.")


# =============================================
# FONCTION : Détail d'un dossier
# =============================================
def _render_dossier_detail(dossier: dict):
    """Affiche le détail d'un dossier avec possibilité de validation."""
    dossier_id = dossier["id"]

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Informations")
        st.write(f"**Référence :** {dossier['reference']}")
        st.write(f"**Statut :** {dossier['statut']}")
        st.write(f"**Expéditeur :** {dossier.get('email_source', '—')}")
        st.write(f"**Client :** {dossier.get('client_nom', '—')}")
        st.write(f"**Immatriculation :** {dossier.get('immatriculation', '—')}")
        st.write(f"**VIN :** {dossier.get('vin', '—')}")
        st.write(f"**Créé le :** {dossier.get('created_at', '—')}")

    with col2:
        # Données extraites
        donnees = dossier.get("donnees_extraites")
        if donnees:
            if isinstance(donnees, str):
                donnees = json.loads(donnees)
            st.subheader("Données extraites")
            st.json(donnees)

    # Documents
    documents = get_documents_for_dossier(dossier_id)
    if documents:
        st.subheader(f"Documents ({len(documents)})")
        for doc in documents:
            doc_col1, doc_col2, doc_col3 = st.columns([1, 1, 2])
            doc_col1.write(f"**{doc['type_document']}**")
            doc_col2.write(f"Confiance : {doc.get('confidence', 0):.0%}")

            doc_data = doc.get("donnees_json")
            if doc_data:
                if isinstance(doc_data, str):
                    doc_data = json.loads(doc_data)
                with doc_col3.expander("Données"):
                    st.json(doc_data)

            # Afficher l'image du document
            filepath = doc.get("fichier_path", "")
            if filepath and Path(filepath).exists():
                ext = Path(filepath).suffix.lower()
                if ext in {".jpg", ".jpeg", ".png", ".bmp"}:
                    st.image(filepath, caption=doc["type_document"], width=400)

    # Taxes
    taxes = dossier.get("taxes")
    if taxes:
        if isinstance(taxes, str):
            taxes = json.loads(taxes)
        st.subheader("Taxes")
        tax_cols = st.columns(6)
        tax_cols[0].metric("Y1 Régionale", f"{taxes.get('Y1_taxe_regionale', 0):.2f} EUR")
        tax_cols[1].metric("Y3 Formation", f"{taxes.get('Y3_taxe_formation', 0):.2f} EUR")
        tax_cols[2].metric("Y4 CO2", f"{taxes.get('Y4_malus_co2', 0):.2f} EUR")
        tax_cols[3].metric("Y5 Masse", f"{taxes.get('Y5_malus_masse', 0):.2f} EUR")
        tax_cols[4].metric("Y6 Fixe", f"{taxes.get('Y6_taxe_fixe', 0):.2f} EUR")
        tax_cols[5].metric("TOTAL", f"{taxes.get('total', 0):.2f} EUR")

    # CERFA
    cerfa_path = dossier.get("cerfa_path", "")
    if cerfa_path and Path(cerfa_path).exists():
        st.subheader("CERFA généré")
        with open(cerfa_path, "rb") as f:
            st.download_button(
                "Télécharger le CERFA 13750",
                data=f.read(),
                file_name=Path(cerfa_path).name,
                mime="application/pdf",
            )

    # Actions
    st.subheader("Actions")
    action_cols = st.columns(4)

    if dossier["statut"] == "pret":
        if action_cols[0].button("Valider le dossier", key=f"validate_{dossier_id}"):
            update_dossier_status(dossier_id, "valide")
            st.success("Dossier validé !")
            st.rerun()

    if dossier["statut"] == "valide":
        if action_cols[0].button("Marquer comme envoyé", key=f"send_{dossier_id}"):
            update_dossier_status(dossier_id, "envoye")
            st.success("Dossier marqué comme envoyé.")
            st.rerun()

    if action_cols[1].button("Remettre en attente", key=f"reset_{dossier_id}"):
        update_dossier_status(dossier_id, "nouveau")
        st.rerun()

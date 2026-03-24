"""
Application Streamlit principale — Interface agent habilité.

Accès restreint : agent habilité uniquement (authentification requise).

Pages :
  01_dossiers      → vue globale de tous les dossiers
  02_review_queue  → file d'attente de validation manuelle
  03_analytics     → métriques et KPIs
  04_settings      → paramètres compte

TODO: implémenter l'authentification Streamlit (st.experimental_user ou custom auth).
"""
import streamlit as st

st.set_page_config(
    page_title="SaaS Carte Grise — Agent",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("SaaS Carte Grise")
st.caption("Interface Agent Habilité")

# TODO: vérifier l'authentification avant d'afficher quoi que ce soit
st.info("Interface en cours de développement.")

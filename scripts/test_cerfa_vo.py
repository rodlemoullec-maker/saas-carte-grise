"""Génère un Cerfa VO 13750 de test — personne morale."""
from engine.cerfa.cerfa_image_annotator import annotate_cerfa_vo

annotate_cerfa_vo(
    image_path="site/assets/cerfa_vo_page1_blank.png",
    output_path="/tmp/cerfa_vo_test.png",
    type_demande="certificat",
    # Véhicule
    immatriculation_a="AB-123-CD",
    date_achat="20/03/2026",
    date_certificat="15/06/2018",
    date_premiere_immat="15/06/2018",
    numero_formule="2018BX12345",
    marque_d1="RENAULT",
    denomination_d3="MEGANE IV ESTATE",
    type_variante_d2="MEGAN-E",
    vin_e="VF1RFB00X61234567",
    genre_j1="VP",
    # Couleur
    couleur="gris",
    couleur_nuance="fonce",
    # Titulaire — PERSONNE MORALE
    personne_type="morale",
    titulaire_nom="TRANSPORTS LEFEVRE SAS",
    siret="98765432100018",
    # Adresse
    adresse_num_voie="125",
    adresse_type_voie="AVENUE",
    adresse_nom_voie="DES CHAMPS-ELYSEES",
    adresse_code_postal="75008",
    adresse_commune="PARIS",
)
print("OK → /tmp/cerfa_vo_test.png")

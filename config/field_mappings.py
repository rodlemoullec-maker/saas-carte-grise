# Mapping des données extraites vers les champs AcroForm du CERFA 13750
# Les noms de champs seront à ajuster après inspection du PDF officiel

CERFA_13750_FIELDS = {
    # Cadre A — Demandeur
    "demandeur_nom": "Toidentify_NomPrenom",
    "demandeur_prenom": "Toidentify_Prenom",
    "demandeur_date_naissance": "Toidentify_DateNaissance",
    "demandeur_lieu_naissance": "Toidentify_LieuNaissance",
    "demandeur_adresse": "Toidentify_Adresse",
    "demandeur_code_postal": "Toidentify_CP",
    "demandeur_ville": "Toidentify_Ville",

    # Cadre B — Véhicule
    "A_immatriculation": "Toidentify_Immat",
    "D1_marque": "Toidentify_Marque",
    "D2_type_variante_version": "Toidentify_TVV",
    "D3_denomination_commerciale": "Toidentify_Denomination",
    "E_vin": "Toidentify_VIN",
    "J1_genre_national": "Toidentify_Genre",
    "J2_carrosserie_ce": "Toidentify_CarrosserieCE",
    "P1_cylindree": "Toidentify_Cylindree",
    "P6_puissance_fiscale": "Toidentify_PuissanceFiscale",
    "P3_energie": "Toidentify_Energie",
    "S1_nb_places_assises": "Toidentify_Places",

    # Cadre taxes
    "Y1_taxe_regionale": "Toidentify_Y1",
    "Y3_taxe_formation": "Toidentify_Y3",
    "Y4_taxe_co2": "Toidentify_Y4",
    "Y6_taxe_fixe": "Toidentify_Y6",
    "total_taxes": "Toidentify_Total",
}

# Les valeurs "Toidentify_*" seront remplacées par les vrais noms
# de champs après inspection du PDF CERFA avec :
# from fillpdf import fillpdfs
# fillpdfs.get_form_fields("templates/cerfa_13750_07.pdf")

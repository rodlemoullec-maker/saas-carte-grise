"""
Génère le Cerfa 13749 (VN) de démo avec toutes les données Honda CB125R.
Usage: python scripts/generate_demo_cerfa.py
"""
from engine.cerfa_automation.cerfa_filler import CerfaFiller

DEMO_DATA = {
    "vehicule": {
        "soussigne": "HONDA MOTOR EUROPE LTD",
        "date_reception": "",
        "numero_k": "",
        "marque": "HONDA",
        "type_variante_version": "MH01-01-001-0",
        "cnit": "JM2KECW105SJ08739",
        "numero_identification": "JM2KECW105SJ08739",
        "denomination_commerciale": "CB125R",
        "genre_national": "MTL",
        "categorie_j": "L3e-A1E",
        "carrosserie_j2": "",
        "carrosserie_j3": "SOLO",
        "energie": "essence",
        "puissance_cv": "11",
        "puissance_nette_p2": "11",
        "cylindree_p1": "124",
        "co2_wltp": "",
        "places": "2",
        "places_debout_s2": "",
        "masse_f1": "291",
        "ptac_kg": "",
        "masse_f3": "",
        "masse_g": "130",
        "poids_vide_g1": "130",
        "niveau_sonore_u1": "78",
        "vitesse_moteur_u2": "5500",
        "classe_env": "EURO5",
        "couleur": "noir",
        "couleur_nuance": "fonce",
        "vendeur_nom": "MOTO CENTER PARIS",
        "date_achat": "01/03/2026",
        "immatriculation": "",
    },
    "titulaire": {
        "type": "physique",
        "civilite": "M",
        "nom_naissance": "DUPONT",
        "prenom": "Marie",
        "date_naissance": "15/06/1992",
        "lieu_naissance": "PARIS",
        "numero_voie": "114",
        "type_voie": "RUE",
        "nom_voie": "DE LA CONVENTION",
        "code_postal": "75015",
        "ville": "PARIS",
        "pays": "FRANCE",
    },
    "cotitulaire": {},
}


if __name__ == "__main__":
    import sys

    headless = "--visible" not in sys.argv
    filler = CerfaFiller(headless=headless)

    print("Génération du Cerfa VN de démo...")
    print(f"Mode: {'headless' if headless else 'visible'}")

    try:
        pdf_bytes = filler.fill_and_download(
            DEMO_DATA,
            output_path="data/cerfa_demo_vn.pdf",
            dossier_type="VN",
        )
        print(f"PDF généré: {len(pdf_bytes)} bytes → data/cerfa_demo_vn.pdf")

        # Extraire page 1 en PNG
        from pdf2image import convert_from_path
        images = convert_from_path("data/cerfa_demo_vn.pdf", first_page=1, last_page=1, dpi=200)
        images[0].save("site/assets/cerfa_vn_page1_blank.png", "PNG")
        print(f"Page 1 extraite: {images[0].size}")

        # Annoter avec cachet + signature
        from engine.cerfa.cerfa_image_annotator import annotate_cerfa_vn
        annotate_cerfa_vn(
            "site/assets/cerfa_vn_page1_blank.png",
            vendeur_nom="MOTO CENTER PARIS - 123 rue de la Moto, 75011 Paris",
            date_vente="01/03/2026",
            cachet_nom="MOTO CENTER PARIS",
            cachet_adresse="123 rue de la Moto, 75011",
            cachet_siret="123 456 789 00012",
            output_path="site/assets/cerfa_vn_page1.png",
        )
        print("Image annotée: site/assets/cerfa_vn_page1.png")
        print("DONE!")

    except Exception as e:
        print(f"ERREUR: {e}")
        import traceback
        traceback.print_exc()

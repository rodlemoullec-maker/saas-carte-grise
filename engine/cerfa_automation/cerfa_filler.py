"""
CerfaFiller — Génération locale 100% PIL des Cerfa 13749 (VN) et 13750 (VO).

Aucune dépendance externe : ni Playwright, ni service-public.gouv.fr,
ni connexion internet. Tout est généré sur la machine de l'agent à partir
des images vierges des Cerfa et des positions pixel des champs.

Usage :
    from engine.cerfa_automation.cerfa_filler import CerfaFiller
    pdf_bytes = CerfaFiller().fill_and_download(data, dossier_type="VN")
"""
from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class CerfaFiller:
    """Génère les Cerfa 13749 (VN) et 13750 (VO) en local via PIL."""

    def __init__(self, headless: bool = True):
        # `headless` conservé pour compat — n'a aucun effet, tout est local
        self.headless = headless

    def fill_and_download(self, data: dict, output_path: str | None = None, dossier_type: str = "VO") -> bytes:
        """
        Génère le Cerfa PDF rempli, 100% en local via PIL.

        Args:
            data: dict avec vehicule, titulaire, cotitulaire, metadata
            output_path: si fourni, sauve le PDF à ce chemin
            dossier_type: "VN" ou "VO"

        Returns:
            bytes du PDF généré
        """
        if dossier_type == "VN":
            return self._generate_vn_pil(data, output_path)

        return self._generate_vo_pil(data, output_path)

    def _generate_vn_pil(self, data: dict, output_path: str | None = None) -> bytes:
        """Génère le Cerfa 13749 VN entièrement via PIL (zéro Playwright)."""
        import io
        from engine.cerfa.cerfa_image_annotator import annotate_cerfa_vn

        v = data.get("vehicule", {})
        t = data.get("titulaire", {})
        a = t.get("adresse", {})
        metadata = data.get("metadata", {})

        # Déterminer l'image vierge
        blank_path = str(Path(__file__).parent.parent.parent / "site" / "assets" / "cerfa_vn_page1_blank.png")
        if not Path(blank_path).exists():
            blank_path = str(Path(__file__).parent.parent.parent / "data" / "cerfa_vn_blank.png")

        logger.info(f"[CerfaFiller VN] Génération PIL depuis {blank_path}")

        # Construire le nom du vendeur
        vendeur_nom = v.get("vendeur_nom", "")

        # Déterminer source constructeur/représentant
        certificat_source = ""
        soussigne = v.get("soussigne", "")
        if soussigne:
            # Heuristique : si le soussigné contient "Ltd", "GmbH", "Europe", "France" → représentant
            lower = soussigne.lower()
            if any(kw in lower for kw in ("ltd", "gmbh", "europe", "france", "sa", "sas")):
                certificat_source = "representant"
            else:
                certificat_source = "constructeur"

        # Déterminer origine hors UE via marque
        marque = v.get("marque", "").upper()
        marques_hors_ue = {"HONDA", "YAMAHA", "SUZUKI", "KAWASAKI", "TOYOTA", "NISSAN",
                           "MAZDA", "MITSUBISHI", "SUBARU", "LEXUS", "INFINITI", "ACURA",
                           "HYUNDAI", "KIA", "GENESIS", "FORD", "CHEVROLET", "TESLA",
                           "JEEP", "DODGE", "RAM", "CHRYSLER", "CADILLAC", "GMC"}
        origine_hors_ue = marque in marques_hors_ue

        # Co-titulaire
        cotitulaires = metadata.get("cotitulaires", [])
        cotitulaire_nom = ""
        if cotitulaires:
            cot = cotitulaires[0]
            if cot.get("type") == "morale":
                cotitulaire_nom = cot.get("raison_sociale", "")
            else:
                cotitulaire_nom = f"{cot.get('nom', '')} {cot.get('prenom', '')}".strip()

        # Sexe
        sexe = t.get("sexe", "")
        if not sexe:
            sexe = metadata.get("client_sexe", "")

        # Type personne
        personne_type = "morale" if t.get("type") == "morale" else "physique"

        # Nom titulaire
        titulaire_nom = f"{t.get('nom_naissance', '')} {t.get('prenom', '')}".strip()

        out_path = output_path or str(Path(__file__).parent / "cerfa_vn_generated.png")

        annotate_cerfa_vn(
            image_path=blank_path,
            vendeur_nom=vendeur_nom,
            date_vente=v.get("date_achat", ""),
            cachet_nom=v.get("cachet_nom", vendeur_nom.split(" - ")[0] if " - " in vendeur_nom else vendeur_nom),
            cachet_adresse=v.get("cachet_adresse", ""),
            cachet_siret=v.get("cachet_siret", ""),
            certificat_source=certificat_source,
            date_reception=v.get("date_reception", ""),
            numero_k=v.get("numero_k", ""),
            origine_hors_ue=origine_hors_ue,
            marque_d1=v.get("marque", ""),
            type_variante_d2=v.get("type_variante_version", ""),
            denomination_d3=v.get("denomination_commerciale", ""),
            cnit_d21=v.get("cnit", ""),
            vin_e=v.get("numero_identification", ""),
            masse_f1=str(v.get("masse_f1") or ""),
            masse_f2=str(v.get("ptac_kg") or ""),
            masse_f3=str(v.get("masse_f3") or ""),
            masse_g=str(v.get("masse_g") or ""),
            poids_vide_g1=str(v.get("poids_vide_g1") or ""),
            categorie_j=v.get("categorie_j", ""),
            genre_j1=v.get("genre_national", ""),
            carrosserie_j2=v.get("carrosserie_j2", ""),
            carrosserie_j3=v.get("carrosserie_j3", ""),
            cylindree_p1=str(v.get("cylindree_p1") or ""),
            puissance_nette_p2=str(v.get("puissance_nette_p2") or ""),
            energie_p3=v.get("energie", ""),
            puissance_admin_p6=str(v.get("puissance_cv") or ""),
            rapport_puiss_masse=str(v.get("rapport_puiss_masse") or ""),
            places_s1=str(v.get("places") or ""),
            places_s2=str(v.get("places_debout_s2") or ""),
            niveau_sonore_u1=str(v.get("niveau_sonore_u1") or ""),
            vitesse_moteur_u2=str(v.get("vitesse_moteur_u2") or ""),
            co2_v7=str(v.get("co2_wltp") or ""),
            classe_env_v9=v.get("classe_env", ""),
            usage="oui",
            couleur=v.get("couleur", ""),
            couleur_nuance=v.get("couleur_nuance", ""),
            personne_type=personne_type,
            sexe=sexe,
            titulaire_nom=titulaire_nom,
            titulaire_nom_usage=t.get("nom_usage", ""),
            titulaire_date_naissance=t.get("date_naissance", ""),
            titulaire_lieu_naissance=t.get("commune_naissance", ""),
            titulaire_dpt_naissance=t.get("departement_naissance", ""),
            titulaire_pays_naissance=t.get("pays_naissance", "FRANCE"),
            multi_propriete=str(metadata.get("nombre_titulaires", 1)),
            cotitulaire_nom=cotitulaire_nom,
            adresse_num_voie=a.get("numero_voie", ""),
            adresse_extension=a.get("extension", ""),
            adresse_type_voie=a.get("type_voie", ""),
            adresse_nom_voie=a.get("libelle_voie", ""),
            adresse_code_postal=a.get("code_postal", ""),
            adresse_commune=a.get("commune", ""),
            output_path=out_path,
        )

        # Convertir PNG en PDF
        from PIL import Image
        img = Image.open(out_path)
        pdf_bytes_io = io.BytesIO()
        img.save(pdf_bytes_io, "PDF", resolution=200)
        pdf_bytes = pdf_bytes_io.getvalue()

        if output_path:
            pdf_path = output_path.replace(".png", ".pdf") if output_path.endswith(".png") else output_path
            Path(pdf_path).write_bytes(pdf_bytes)
            logger.info(f"[CerfaFiller VN] PDF sauvé : {pdf_path} ({len(pdf_bytes)} bytes)")

        logger.info(f"[CerfaFiller VN] Cerfa généré : {len(pdf_bytes)} bytes — 100% PIL, zéro Playwright")
        return pdf_bytes

    def _generate_vo_pil(self, data: dict, output_path: str | None = None) -> bytes:
        """Génère le Cerfa 13750 VO entièrement via PIL (zéro Playwright)."""
        import io
        from engine.cerfa.cerfa_image_annotator import annotate_cerfa_vo

        v = data.get("vehicule", {})
        t = data.get("titulaire", {})
        a = t.get("adresse", {})
        metadata = data.get("metadata", {})

        # Image vierge
        blank_path = str(Path(__file__).parent.parent.parent / "site" / "assets" / "cerfa_vo_page1_blank.png")
        if not Path(blank_path).exists():
            blank_path = str(Path(__file__).parent.parent.parent / "data" / "cerfa_vo_blank.png")

        logger.info(f"[CerfaFiller VO] Génération PIL depuis {blank_path}")

        # Type personne
        personne_type = "morale" if t.get("type") == "morale" else "physique"
        titulaire_nom = f"{t.get('nom_naissance', '')} {t.get('prenom', '')}".strip()
        if personne_type == "morale":
            titulaire_nom = t.get("raison_sociale", "")

        # Sexe
        sexe = t.get("sexe", "") or metadata.get("client_sexe", "")

        # Co-titulaire
        cotitulaires = metadata.get("cotitulaires", [])
        cotitulaire_nom = ""
        cotitulaire_nom_usage = ""
        cotitulaire_siret = ""
        if cotitulaires:
            cot = cotitulaires[0]
            if cot.get("type") == "morale":
                cotitulaire_nom = cot.get("raison_sociale", "")
                cotitulaire_siret = cot.get("siren", "")
            else:
                cotitulaire_nom = f"{cot.get('nom', '')} {cot.get('prenom', '')}".strip()
                cotitulaire_nom_usage = cot.get("nom_usage", "")

        out_path = output_path or str(Path(__file__).parent / "cerfa_vo_generated.png")

        annotate_cerfa_vo(
            image_path=blank_path,
            type_demande="certificat",
            immatriculation_a=v.get("immatriculation", ""),
            date_achat=v.get("date_achat", ""),
            date_certificat=v.get("date_certificat", ""),
            date_premiere_immat=v.get("date_premiere_immatriculation", ""),
            numero_formule=v.get("numero_formule", ""),
            marque_d1=v.get("marque", ""),
            denomination_d3=v.get("denomination_commerciale", ""),
            type_variante_d2=v.get("type_variante_version", ""),
            vin_e=v.get("numero_identification", ""),
            genre_j1=v.get("genre_national", ""),
            num_exploitation_agricole=v.get("num_exploitation_agricole", ""),
            couleur=v.get("couleur", ""),
            couleur_nuance=v.get("couleur_nuance", ""),
            personne_type=personne_type,
            sexe=sexe,
            titulaire_nom=titulaire_nom,
            titulaire_nom_usage=t.get("nom_usage", ""),
            titulaire_date_naissance=t.get("date_naissance", ""),
            titulaire_lieu_naissance=t.get("commune_naissance", ""),
            titulaire_dpt_naissance=t.get("departement_naissance", ""),
            titulaire_pays_naissance=t.get("pays_naissance", "FRANCE"),
            adresse_num_voie=a.get("numero_voie", ""),
            adresse_extension=a.get("extension", ""),
            adresse_type_voie=a.get("type_voie", ""),
            adresse_nom_voie=a.get("libelle_voie", ""),
            adresse_code_postal=a.get("code_postal", ""),
            adresse_commune=a.get("commune", ""),
            multi_propriete=str(metadata.get("nombre_titulaires", 1)),
            cotitulaire_nom=cotitulaire_nom,
            cotitulaire_nom_usage=cotitulaire_nom_usage,
            cotitulaire_siret=cotitulaire_siret,
            siret=t.get("siren", "") if personne_type == "morale" else "",
            output_path=out_path,
        )

        # Convertir PNG en PDF
        from PIL import Image
        img = Image.open(out_path)
        pdf_bytes_io = io.BytesIO()
        img.save(pdf_bytes_io, "PDF", resolution=200)
        pdf_bytes = pdf_bytes_io.getvalue()

        if output_path:
            pdf_path = output_path.replace(".png", ".pdf") if output_path.endswith(".png") else output_path
            Path(pdf_path).write_bytes(pdf_bytes)
            logger.info(f"[CerfaFiller VO] PDF sauvé : {pdf_path} ({len(pdf_bytes)} bytes)")

        logger.info(f"[CerfaFiller VO] Cerfa généré : {len(pdf_bytes)} bytes — 100% PIL, zéro Playwright")
        return pdf_bytes

    @staticmethod
    def build_data_from_dossier(dossier: dict) -> dict:
        """
        Construit le dict de donnees pour le CerfaFiller a partir
        des donnees extraites du dossier (demo_server format).
        """
        docs = dossier.get("documents", [])
        d: dict = {
            "vehicule": {},
            "titulaire": {"adresse": {}},
        }

        # Vehicule
        d["demarche"] = "Certificat"
        d["vehicule"]["immatriculation"] = dossier.get("immatriculation") or ""
        d["vehicule"]["genre_national"] = "VP"

        # Depuis les documents extraits
        for doc in docs:
            ext = doc.get("extracted_data", {})
            dtype = doc.get("type", "")

            if dtype == "COC":
                d["vehicule"]["marque"] = ext.get("marque", "")
                d["vehicule"]["denomination_commerciale"] = ext.get("denomination") or ext.get("modele", "")
                d["vehicule"]["numero_identification"] = ext.get("vin") or dossier.get("vin", "")
                d["vehicule"]["type_variante_version"] = ext.get("type_variante_version", "")
                d["vehicule"]["cnit"] = ext.get("cnit", "")
                d["vehicule"]["genre_national"] = ext.get("genre_national", "VP")
                d["vehicule"]["soussigne"] = ext.get("soussigne", "")
                d["vehicule"]["date_reception"] = ext.get("date_reception", "")
                d["vehicule"]["numero_k"] = ext.get("numero_k", "")
                d["vehicule"]["energie"] = ext.get("energie", "")
                d["vehicule"]["puissance_cv"] = str(ext.get("puissance_cv") or "")
                d["vehicule"]["co2_wltp"] = str(ext.get("co2_wltp") or "")
                d["vehicule"]["places"] = str(ext.get("places_assises") or ext.get("places") or "")
                d["vehicule"]["ptac_kg"] = str(ext.get("ptac_kg") or ext.get("masse_f2") or "")
                d["vehicule"]["classe_env"] = ext.get("classe_env", "")
                d["vehicule"]["masse_f1"] = str(ext.get("masse_f1") or ext.get("masse_kg") or "")
                d["vehicule"]["masse_g"] = str(ext.get("masse_g") or "")
                d["vehicule"]["masse_f3"] = str(ext.get("masse_f3") or "")
                d["vehicule"]["poids_vide_g1"] = str(ext.get("poids_vide_g1") or "")
                d["vehicule"]["cylindree_p1"] = str(ext.get("cylindree_p1") or ext.get("cylindree_cc") or "")
                d["vehicule"]["puissance_nette_p2"] = str(ext.get("puissance_nette_p2") or ext.get("puissance_kw") or "")
                d["vehicule"]["categorie_j"] = ext.get("categorie_j", "")
                d["vehicule"]["carrosserie_j2"] = ext.get("carrosserie_j2", "")
                d["vehicule"]["carrosserie_j3"] = ext.get("carrosserie_j3", "")
                d["vehicule"]["niveau_sonore_u1"] = str(ext.get("niveau_sonore_u1") or "")
                d["vehicule"]["vitesse_moteur_u2"] = str(ext.get("vitesse_moteur_u2") or "")
                d["vehicule"]["places_debout_s2"] = str(ext.get("places_debout_s2") or "")

            elif dtype == "FACTURE":
                d["vehicule"]["numero_identification"] = ext.get("vin") or d["vehicule"].get("numero_identification", "")
                d["vehicule"]["vendeur_nom"] = ext.get("nom_vendeur", "")
                d["vehicule"]["date_achat"] = ext.get("date_vente") or d["vehicule"].get("date_achat", "")
                # Couleur depuis la facture
                couleur_raw = ext.get("couleur", "")
                if couleur_raw:
                    parts = couleur_raw.lower().split()
                    couleur_map = {"noir":"noir","marron":"marron","rouge":"rouge","orange":"orange",
                                   "jaune":"jaune","vert":"vert","bleu":"bleu","beige":"beige",
                                   "gris":"gris","blanc":"blanc"}
                    for p in parts:
                        if p in couleur_map:
                            d["vehicule"]["couleur"] = couleur_map[p]
                    if "fonce" in couleur_raw.lower():
                        d["vehicule"]["couleur_nuance"] = "fonce"
                    elif "clair" in couleur_raw.lower():
                        d["vehicule"]["couleur_nuance"] = "clair"

            elif dtype == "CG_BARREE":
                d["vehicule"]["immatriculation"] = ext.get("immatriculation") or d["vehicule"]["immatriculation"]
                d["vehicule"]["numero_identification"] = ext.get("vin") or d["vehicule"].get("numero_identification", "")
                d["vehicule"]["marque"] = ext.get("marque") or d["vehicule"].get("marque", "")
                d["vehicule"]["denomination_commerciale"] = ext.get("denomination") or d["vehicule"].get("denomination_commerciale", "")
                d["vehicule"]["date_premiere_immatriculation"] = ext.get("date_premiere_immat", "")
                d["vehicule"]["date_certificat"] = ext.get("date_certificat", "")
                d["vehicule"]["numero_formule"] = ext.get("numero_formule", "")
                d["vehicule"]["genre_national"] = ext.get("genre_national") or d["vehicule"].get("genre_national", "VP")
                d["vehicule"]["date_achat"] = ext.get("date_vente", "")

            elif dtype in ("CNI", "PASSEPORT"):
                d["titulaire"]["nom_naissance"] = ext.get("nom", "")
                d["titulaire"]["prenom"] = ext.get("prenoms", "")
                d["titulaire"]["date_naissance"] = ext.get("date_naissance", "")
                d["titulaire"]["commune_naissance"] = ext.get("lieu_naissance", "")
                nat = ext.get("nationalite", "")
                if nat.lower() in ("francaise", "francais"):
                    d["titulaire"]["pays_naissance"] = "FRANCE"
                else:
                    d["titulaire"]["pays_naissance"] = nat.upper()

            elif dtype == "PERMIS":
                if not d["titulaire"].get("nom_naissance"):
                    d["titulaire"]["nom_naissance"] = ext.get("nom", "")
                    d["titulaire"]["prenom"] = ext.get("prenom", "")

            elif dtype == "DOMICILE":
                d["titulaire"]["adresse"]["code_postal"] = ext.get("code_postal", "")
                d["titulaire"]["adresse"]["commune"] = ext.get("ville", "")
                # Decomposer l'adresse
                adresse = ext.get("adresse", "")
                if adresse:
                    parts = adresse.split(" ", 1)
                    if len(parts) == 2 and parts[0].isdigit():
                        d["titulaire"]["adresse"]["numero_voie"] = parts[0]
                        rest = parts[1]
                        for voie in ["rue", "avenue", "boulevard", "bd", "place", "impasse", "chemin", "allee"]:
                            if rest.lower().startswith(voie):
                                d["titulaire"]["adresse"]["type_voie"] = voie.upper()
                                d["titulaire"]["adresse"]["libelle_voie"] = rest[len(voie):].strip().upper()
                                break
                        else:
                            d["titulaire"]["adresse"]["libelle_voie"] = rest.upper()

            elif dtype == "KBIS":
                # Kbis = personne morale detectee automatiquement
                d["titulaire"]["type"] = "morale"
                d["titulaire"]["siren"] = ext.get("siren", "")
                d["titulaire"]["raison_sociale"] = ext.get("raison_sociale") or ext.get("nom_vendeur", "")

        # Detection auto personne morale si Kbis present
        has_kbis = any(doc.get("type") == "KBIS" for doc in docs)
        if has_kbis:
            d["titulaire"]["type"] = "morale"

        # Departement depuis CP ou lieu naissance
        cp = d["titulaire"]["adresse"].get("code_postal", "")
        lieu = d["titulaire"].get("commune_naissance", "").upper()
        dept_map = {"PARIS": "75", "LYON": "69", "MARSEILLE": "13", "TOULOUSE": "31",
                    "NICE": "06", "NANTES": "44", "BORDEAUX": "33", "LILLE": "59"}
        d["titulaire"]["departement_naissance"] = dept_map.get(lieu, cp[:2] if cp else "")

        # Sexe et type (Kbis override si detecte)
        d["titulaire"]["sexe"] = dossier.get("client_sexe") or "M"
        if not has_kbis:
            d["titulaire"]["type"] = "morale" if dossier.get("is_personne_morale") else "physique"

        # Fallback nom/prenom depuis le dossier
        if not d["titulaire"].get("nom_naissance"):
            d["titulaire"]["nom_naissance"] = dossier.get("client_nom", "")
        if not d["titulaire"].get("prenom"):
            d["titulaire"]["prenom"] = dossier.get("client_prenom", "")

        # VIN fallback
        if not d["vehicule"].get("numero_identification"):
            d["vehicule"]["numero_identification"] = dossier.get("vin", "")

        return d

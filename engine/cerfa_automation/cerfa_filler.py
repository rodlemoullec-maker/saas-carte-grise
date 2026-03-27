"""
CerfaFiller - Remplissage automatique du Cerfa 13750*07 via Playwright.

Utilise le formulaire officiel sur service-public.gouv.fr pour generer
un PDF parfaitement rempli par le site lui-meme.

URL : https://www.service-public.gouv.fr/simulateur/calcul/13750

Usage :
    from engine.cerfa_automation.cerfa_filler import CerfaFiller
    pdf_bytes = CerfaFiller().fill_and_download(data)
"""
from __future__ import annotations

import logging
import time
from pathlib import Path

logger = logging.getLogger(__name__)

CERFA_URL = "https://www.service-public.gouv.fr/simulateur/calcul/13750"
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


class CerfaFiller:
    """Remplit le Cerfa 13750*07 sur service-public.fr et telecharge le PDF."""

    def __init__(self, headless: bool = True):
        self.headless = headless

    def fill_and_download(self, data: dict, output_path: str | None = None) -> bytes:
        """
        Remplit le formulaire 4 etapes et telecharge le PDF.

        Args:
            data: dict avec vehicule, titulaire, cotitulaire
            output_path: si fourni, sauve le PDF a ce chemin

        Returns:
            bytes du PDF genere
        """
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.headless)
            ctx = browser.new_context(user_agent=USER_AGENT, accept_downloads=True)
            page = ctx.new_page()
            page.set_default_timeout(30000)

            try:
                logger.info("Ouverture formulaire Cerfa 13750")
                page.goto(CERFA_URL, wait_until="networkidle")

                # Cookies
                try:
                    page.click("button:has-text('Accepter')", timeout=3000)
                except Exception:
                    pass

                # ═══ PAGE 1 : VEHICULE ═══
                self._fill_page1(page, data)
                page.click("text=Suivant")
                time.sleep(2)
                logger.info("Page 1 (vehicule) OK")

                # ═══ PAGE 2 : TITULAIRE ═══
                self._fill_page2(page, data)
                page.click("text=Suivant")
                time.sleep(2)
                logger.info("Page 2 (titulaire) OK")

                # ═══ PAGE 3 : LOUEUR/LOCATAIRE (skip) ═══
                page.click("text=Suivant")
                time.sleep(2)
                logger.info("Page 3 (loueur) skip")

                # ═══ PAGE 4 : TELECHARGER ═══
                # Le bouton est un <button type="submit" class="btn btn-primary">
                with page.expect_download(timeout=30000) as dl_info:
                    page.click("button.btn-primary[type='submit']", timeout=10000)
                download = dl_info.value

                if output_path:
                    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                    download.save_as(output_path)
                    logger.info(f"PDF sauve : {output_path}")

                pdf_bytes = Path(download.path()).read_bytes()
                logger.info(f"PDF genere : {len(pdf_bytes)} bytes")
                return pdf_bytes

            except Exception as e:
                logger.error(f"Erreur CerfaFiller : {e}")
                try:
                    page.screenshot(path="cerfa_error.png")
                except Exception:
                    pass
                raise
            finally:
                browser.close()

    def _fill_page1(self, page, data: dict):
        """Page 1 : demarche + vehicule."""
        # Demarche (dropdown custom)
        page.click("[role='button']")
        time.sleep(0.5)
        demarche = data.get("demarche", "Certificat")
        page.click(f"li:has-text('{demarche}')")
        time.sleep(1)

        v = data.get("vehicule", {})
        self._fill(page, "#valeurNumeroImma", v.get("immatriculation"))
        self._fill(page, "#Jour1_concat", v.get("date_achat"))
        self._fill(page, "#Jour2_concat", v.get("date_certificat"))
        self._fill(page, "#Jour3_concat", v.get("date_premiere_immatriculation"))
        self._fill(page, "#Newformatimma", v.get("numero_formule"))
        self._fill(page, "#Marque", v.get("marque"))
        self._fill(page, "#DenominationCommerciale", v.get("denomination_commerciale"))
        self._fill(page, "#TypeVarianteVersion", v.get("type_variante_version"))
        self._fill(page, "#NumeroIdentificationVehicule", v.get("numero_identification"))
        self._fill(page, "#GenreNational", v.get("genre_national"))

        # Couleur
        nuance = v.get("couleur_nuance", "")
        if nuance == "clair":
            page.check("#nuance_1")
        elif nuance == "fonce":
            page.check("#nuance_2")

        couleur_map = {
            "noir": "1", "marron": "2", "rouge": "3", "orange": "4",
            "jaune": "5", "vert": "6", "bleu": "7", "beige": "8",
            "gris": "9", "blanc": "10",
        }
        cid = couleur_map.get((v.get("couleur") or "").lower(), "")
        if cid:
            page.check(f"#couleur_{cid}_{cid}")

    def _fill_page2(self, page, data: dict):
        """Page 2 : titulaire + domicile."""
        t = data.get("titulaire", {})
        is_pm = t.get("type", "physique") == "morale"

        if is_pm:
            page.check("#Personne_2")
        else:
            page.check("#Personne_1")
            time.sleep(0.5)
            if t.get("sexe", "M") == "M":
                page.check("#Sexe_1")
            else:
                page.check("#Sexe_2")

        # Nom prenom
        nom_prenom = f"{t.get('nom_naissance', '')} {t.get('prenom', '')}".strip()
        self._fill(page, "#NomPrenomTitulaire", nom_prenom)
        self._fill(page, "#Name", t.get("nom_usage"))

        # Naissance
        self._fill(page, "#Jour4_concat", t.get("date_naissance"))
        self._fill(page, "#CityName1", t.get("commune_naissance"))
        self._fill(page, "#DPT", t.get("departement_naissance"))
        self._fill(page, "#Pays", t.get("pays_naissance"))

        # Adresse
        a = t.get("adresse", {})
        self._fill(page, "#Adresse", a.get("etage"))
        self._fill(page, "#Adresse_1_", a.get("immeuble"))
        self._fill(page, "#BuildingNumber", a.get("numero_voie"))
        self._fill(page, "#BlockName", a.get("extension"))
        self._fill(page, "#RoadType", a.get("type_voie"))
        self._fill(page, "#StreetName", a.get("libelle_voie"))
        self._fill(page, "#Adresse_2_", a.get("lieu_dit"))
        self._fill(page, "#Postcode", a.get("code_postal"))
        self._fill(page, "#CityName2", a.get("commune"))

        # Contact
        self._fill(page, "#telPorTitulaire", t.get("telephone"))
        self._fill(page, "#mailTitulaire", t.get("email"))

        # Multi-propriete
        if data.get("cotitulaire"):
            page.check("#mutlipropriete_1")  # Oui
        else:
            page.check("#mutlipropriete_2")  # Non

    def _fill(self, page, selector: str, value: str | None):
        if not value:
            return
        try:
            page.fill(selector, str(value))
        except Exception as e:
            logger.warning(f"Champ {selector} : {e}")

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
                d["vehicule"]["denomination_commerciale"] = ext.get("modele", "")
                d["vehicule"]["numero_identification"] = ext.get("vin") or dossier.get("vin", "")

            elif dtype == "FACTURE":
                d["vehicule"]["numero_identification"] = ext.get("vin") or d["vehicule"].get("numero_identification", "")

            elif dtype == "CG_BARREE":
                d["vehicule"]["immatriculation"] = ext.get("immatriculation") or d["vehicule"]["immatriculation"]
                d["vehicule"]["numero_identification"] = ext.get("vin") or d["vehicule"].get("numero_identification", "")

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

        # Departement depuis CP ou lieu naissance
        cp = d["titulaire"]["adresse"].get("code_postal", "")
        lieu = d["titulaire"].get("commune_naissance", "").upper()
        dept_map = {"PARIS": "75", "LYON": "69", "MARSEILLE": "13", "TOULOUSE": "31",
                    "NICE": "06", "NANTES": "44", "BORDEAUX": "33", "LILLE": "59"}
        d["titulaire"]["departement_naissance"] = dept_map.get(lieu, cp[:2] if cp else "")

        # Sexe et type
        d["titulaire"]["sexe"] = dossier.get("client_sexe") or "M"
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

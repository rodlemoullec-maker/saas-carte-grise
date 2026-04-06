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

CERFA_URLS = {
    "VN": "https://www.service-public.gouv.fr/simulateur/calcul/13749",
    "VO": "https://www.service-public.gouv.fr/simulateur/calcul/13750",
}
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


class CerfaFiller:
    """Remplit le Cerfa 13750*07 sur service-public.fr et telecharge le PDF."""

    def __init__(self, headless: bool = True):
        self.headless = headless

    def fill_and_download(self, data: dict, output_path: str | None = None, dossier_type: str = "VO") -> bytes:
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
                cerfa_url = CERFA_URLS.get(dossier_type, CERFA_URLS["VO"])
                cerfa_num = "13749" if dossier_type == "VN" else "13750"
                logger.info(f"Ouverture formulaire Cerfa {cerfa_num} ({dossier_type})")
                page.goto(cerfa_url, wait_until="networkidle")

                # Cookies
                try:
                    page.click("button:has-text('Accepter')", timeout=3000)
                except Exception:
                    pass

                if dossier_type == "VN":
                    # ═══ 13749 VN : 4 etapes ═══
                    self._fill_vn_page1(page, data)
                    page.click("text=Suivant"); time.sleep(3)
                    logger.info("VN P1→P2 OK")

                    self._fill_vn_page2(page, data)
                    page.click("text=Suivant")
                    page.wait_for_load_state("networkidle", timeout=10000)
                    time.sleep(2)
                    logger.info("VN P2→P3 OK")

                    page.screenshot(path="cerfa_vn_p3_before_fill.png")
                    self._fill_vn_page3(page, data)
                    page.screenshot(path="cerfa_vn_p3_after_fill.png")
                    page.click("text=Suivant")
                    page.wait_for_load_state("networkidle", timeout=10000)
                    time.sleep(2)
                    page.screenshot(path="cerfa_vn_p4.png")
                    logger.info("VN P3→P4 OK")
                else:
                    # ═══ 13750 VO : 4 etapes ═══
                    self._fill_page1(page, data)
                    page.click("text=Suivant"); time.sleep(2)
                    logger.info("VO P1 (vehicule) OK")

                    self._fill_page2(page, data)
                    page.click("text=Suivant"); time.sleep(2)
                    logger.info("VO P2 (titulaire) OK")

                    page.click("text=Suivant"); time.sleep(2)
                    logger.info("VO P3 (loueur) skip")

                # ═══ PAGE FINALE : TELECHARGER ═══
                time.sleep(2)
                # Forcer la case Certificat (le listbox custom ne propage pas la valeur)
                page.evaluate("""
                    var li = document.querySelector('.listbox-input');
                    if (li) li.value = 'Certificat';
                    var gr = document.querySelector('input[name="Groupe_de_boutons_radio"]');
                    if (gr) gr.value = 'Certificat';
                """)
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(2)
                page.screenshot(path="cerfa_final_page.png")
                # Chercher le bouton par plusieurs methodes
                btn = page.query_selector("button[name='telecharger']") or \
                      page.query_selector("button.btn-primary[type='submit']")
                if not btn:
                    # Chercher tous les boutons visibles contenant PDF ou formulaire
                    for b in page.query_selector_all("button:visible"):
                        txt = b.inner_text().lower()
                        if "pdf" in txt or "formulaire" in txt or "charger" in txt:
                            btn = b
                            break
                if btn:
                    logger.info(f"Bouton trouve: {btn.inner_text().strip()[:50]}")
                    with page.expect_download(timeout=30000) as dl_info:
                        btn.click()
                    download = dl_info.value
                else:
                    logger.error("Bouton telecharger non trouve!")
                    raise RuntimeError("Bouton telecharger non trouve")

                if output_path:
                    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                    download.save_as(output_path)
                    logger.info(f"PDF sauve : {output_path}")

                raw_pdf = Path(download.path()).read_bytes()

                # Post-traitement : cocher la case Certificat sur le PDF VO
                if dossier_type == "VO":
                    raw_pdf = self._check_certificat_box(raw_pdf)

                if output_path:
                    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                    Path(output_path).write_bytes(raw_pdf)

                logger.info(f"PDF genere : {len(raw_pdf)} bytes")
                return raw_pdf

            except Exception as e:
                logger.error(f"Erreur CerfaFiller : {e}")
                try:
                    page.screenshot(path="cerfa_error.png")
                except Exception:
                    pass
                raise
            finally:
                browser.close()

    # ─── VN (13749) specifique ──────────────────────────────────────

    def _fill_vn_page1(self, page, data: dict):
        """P1 VN: identification vehicule — tous les champs COC."""
        page.click("#identification_vehicule_choix_1")  # Du constructeur
        time.sleep(0.5)
        v = data.get("vehicule", {})

        # COC = Non EN PREMIER (avant tout remplissage)
        # Sinon remplir soussigne/K change l'etat et les champs restent masques
        label = page.query_selector("label[for='identification_vehicule_presence_coc_2']")
        if label:
            label.click()
        time.sleep(2)

        # Maintenant remplir tous les champs (visibles apres COC=Non)
        self._fill(page, "#identification_vehicule_soussigne", v.get("soussigne"))
        self._fill(page, "#identification_vehicule_reception", v.get("date_reception"))
        self._fill(page, "#identification_vehicule_numero_K", v.get("numero_k"))

        # ─── Champs remplis par cerfa_image_annotator.py (PIL) ───
        # D.1 (marque), D.2 (type variante), D.2.1 (CNIT), E (VIN),
        # F.1, F.2, F.3, G, G.1, J, J.1, J.2, J.3,
        # P.1, P.2, P.3, S.1, S.2, U.1, U.2, V.7, V.9,
        # rapport puiss./masse
        # → Tous annotés directement sur l'image PNG, pas via Playwright.

        # ─── Tous les champs véhicule (y compris couleur, usage) sont
        # maintenant gérés par cerfa_image_annotator.py (PIL),
        # plus aucune dépendance Playwright pour la page 1. ───

    def _fill_vn_page2(self, page, data: dict):
        """P2 VN: certificat de vente."""
        v = data.get("vehicule", {})
        try:
            self._fill(page, "#certificat_vente_soussignee", v.get("vendeur_nom"))
            self._fill(page, "#certificat_vente_date", v.get("date_achat"))
        except Exception as e:
            logger.warning(f"P2 VN certificat de vente: {e} — certains champs non remplis")

    def _fill_vn_page3(self, page, data: dict):
        """P3 VN: titulaire + domicile."""
        t = data.get("titulaire", {})
        is_pm = t.get("type", "physique") == "morale"
        def click_label_or_radio(field_id):
            """Clic sur le label du radio, fallback sur le radio directement, fallback JS."""
            lbl = page.query_selector(f"label[for='{field_id}']")
            if lbl and lbl.is_visible():
                lbl.click()
                return
            el = page.query_selector(f"#{field_id}")
            if el and el.is_visible():
                el.click(force=True)
                return
            page.evaluate(f"document.getElementById('{field_id}')?.click()")

        if is_pm:
            click_label_or_radio("demandeur_personne_2")
            time.sleep(1)
            self._fill(page, "#demandeur_titulaire_raison", t.get("raison_sociale"))
            self._fill(page, "#demandeur_titulaire_siret", t.get("siren"))
        else:
            click_label_or_radio("demandeur_personne_1")
            time.sleep(1)
            if t.get("sexe", "M") == "M":
                click_label_or_radio("demandeur_sexe_1")
            else:
                click_label_or_radio("demandeur_sexe_2")
            nom_prenom = f"{t.get('nom_naissance', '')} {t.get('prenom', '')}".strip()
            self._fill(page, "#demandeur_titulaire_nom_naissance", nom_prenom)
            self._fill(page, "#demandeur_titulaire_nom_usage", t.get("nom_usage"))
        self._fill(page, "#demandeur_titulaire_date_naissance", t.get("date_naissance"))
        self._fill(page, "#demandeur_titulaire_naissance_lieu", t.get("commune_naissance"))
        self._fill(page, "#demandeur_titulaire_naissance_dpt", t.get("departement_naissance"))
        self._fill(page, "#demandeur_titulaire_naissance_pays", t.get("pays_naissance"))
        click_label_or_radio("demandeur_multi_propriete_2")
        click_label_or_radio("demandeur_location_2")
        a = t.get("adresse", {})
        self._fill(page, "#demandeur_domicile_num_voie", a.get("numero_voie"))
        self._fill(page, "#demandeur_domicile_extension", a.get("extension"))
        self._fill(page, "#demandeur_domicile_type_voie", a.get("type_voie"))
        self._fill(page, "#demandeur_domicile_nom_voie", a.get("libelle_voie"))
        self._fill(page, "#demandeur_domicile_code_postale", a.get("code_postal"))
        self._fill(page, "#demandeur_domicile_commune", a.get("commune"))
        self._fill(page, "#demandeur_domicile_tel_portable", t.get("telephone"))
        self._fill(page, "#demandeur_domicile_mail", t.get("email"))

    # ─── VO (13750) specifique ──────────────────────────────────────

    def _fill_page1(self, page, data: dict):
        """Page 1 : demarche + vehicule."""
        # Demarche (dropdown custom)
        page.click("[role='button']")
        time.sleep(0.5)
        demarche = data.get("demarche", "Certificat")
        page.click("[role='button']")
        time.sleep(0.5)
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
            time.sleep(1)
            # Personne morale : SIREN + raison sociale (pas nom/prenom/naissance)
            self._fill(page, "#N_SIREN", t.get("siren"))
            self._fill(page, "#RaisonSocialeTitu", t.get("raison_sociale"))
        else:
            page.check("#Personne_1")
            time.sleep(0.5)
            if t.get("sexe", "M") == "M":
                page.check("#Sexe_1")
            else:
                page.check("#Sexe_2")
            # Personne physique : nom + prenom
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

    def _check_certificat_box(self, pdf_bytes: bytes) -> bytes:
        """Overlay un X dans la case Certificat du PDF 13750 telecharge."""
        from fpdf import FPDF
        from pypdf import PdfReader, PdfWriter
        import io

        H = 841.89
        # Case Certificat : texte a x=163.2, y=760.1 — la checkbox est a ~x=150, y=760
        ov = FPDF(unit="pt", format=(595.276, H))
        ov.add_page()
        ov.set_font("Helvetica", "B", 10)
        ov.set_xy(148, H - 765)
        ov.cell(8, 8, "X")

        ov_bytes = bytes(ov.output())
        original = PdfReader(io.BytesIO(pdf_bytes))
        overlay = PdfReader(io.BytesIO(ov_bytes))
        writer = PdfWriter()

        page = original.pages[0]
        page.merge_page(overlay.pages[0])
        writer.add_page(page)

        # Copier les autres pages si il y en a
        for i in range(1, len(original.pages)):
            writer.add_page(original.pages[i])

        output = io.BytesIO()
        writer.write(output)
        return output.getvalue()

    def _fill(self, page, selector: str, value: str | None):
        if not value:
            return
        try:
            page.fill(selector, str(value), timeout=5000)
        except Exception:
            pass  # Champ non visible ou absent

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

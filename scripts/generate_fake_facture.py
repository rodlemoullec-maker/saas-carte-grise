"""
Génère une facture véhicule fictive (Stark Varg / LE MOULLEC RODOLPH) pour
les tests E2E du dossier VN.
"""
from fpdf import FPDF


class FacturePDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 14)
        self.cell(0, 10, "GARAGE MOTO PASSION", ln=True, align="L")
        self.set_font("Helvetica", "", 9)
        self.cell(0, 5, "12 Avenue des Sports - 27700 LES ANDELYS", ln=True)
        self.cell(0, 5, "Tel : 02 32 54 12 34 - SIRET : 12345678900012", ln=True)
        self.cell(0, 5, "TVA intracom : FR12123456789", ln=True)
        self.ln(8)


pdf = FacturePDF()
pdf.add_page()

pdf.set_font("Helvetica", "B", 16)
pdf.cell(0, 10, "FACTURE N° 2026-0317", ln=True, align="C")
pdf.ln(3)

pdf.set_font("Helvetica", "", 11)
pdf.cell(0, 6, "Date de facture : 13/03/2026", ln=True)
pdf.cell(0, 6, "Date de vente : 13/03/2026", ln=True)
pdf.ln(5)

# Acheteur
pdf.set_font("Helvetica", "B", 11)
pdf.cell(0, 6, "ACHETEUR", ln=True)
pdf.set_font("Helvetica", "", 10)
pdf.cell(0, 5, "M. LE MOULLEC RODOLPH", ln=True)
pdf.cell(0, 5, "17 Rue de la Madeleine", ln=True)
pdf.cell(0, 5, "27700 LES ANDELYS", ln=True)
pdf.ln(8)

# Vehicule
pdf.set_font("Helvetica", "B", 11)
pdf.cell(0, 6, "DESIGNATION DU VEHICULE", ln=True)
pdf.set_font("Helvetica", "", 10)
pdf.cell(0, 5, "Marque         : STARK", ln=True)
pdf.cell(0, 5, "Modele         : VARG", ln=True)
pdf.cell(0, 5, "Type/Variante  : VARG 1", ln=True)
pdf.cell(0, 5, "Categorie      : L3e-A1E (motocyclette electrique)", ln=True)
pdf.cell(0, 5, "VIN            : UDUEX1AE3TA008739", ln=True)
pdf.cell(0, 5, "Energie        : Electrique", ln=True)
pdf.cell(0, 5, "Couleur        : Noir", ln=True)
pdf.cell(0, 5, "Vehicule neuf  : Oui", ln=True)
pdf.ln(8)

# Detail
pdf.set_font("Helvetica", "B", 11)
pdf.cell(0, 6, "DETAIL", ln=True)
pdf.set_font("Helvetica", "", 10)
pdf.cell(110, 6, "Designation", border=1)
pdf.cell(30, 6, "Qte", border=1, align="C")
pdf.cell(40, 6, "Montant TTC", border=1, align="C", ln=True)
pdf.cell(110, 6, "STARK VARG 1 (moto electrique)", border=1)
pdf.cell(30, 6, "1", border=1, align="C")
pdf.cell(40, 6, "12 990,00 EUR", border=1, align="R", ln=True)
pdf.cell(110, 6, "Carte grise (frais d'immatriculation)", border=1)
pdf.cell(30, 6, "1", border=1, align="C")
pdf.cell(40, 6, "0,00 EUR", border=1, align="R", ln=True)
pdf.ln(5)

pdf.set_font("Helvetica", "B", 11)
pdf.cell(140, 7, "Total HT", border=1, align="R")
pdf.cell(40, 7, "10 825,00 EUR", border=1, align="R", ln=True)
pdf.cell(140, 7, "TVA 20%", border=1, align="R")
pdf.cell(40, 7, "2 165,00 EUR", border=1, align="R", ln=True)
pdf.cell(140, 7, "Total TTC", border=1, align="R")
pdf.cell(40, 7, "12 990,00 EUR", border=1, align="R", ln=True)

pdf.ln(10)
pdf.set_font("Helvetica", "I", 9)
pdf.multi_cell(
    0, 5,
    "Reglement : virement bancaire au comptant. Vehicule garanti 2 ans pieces et "
    "main d'oeuvre selon CGV constructeur. Vehicule livre avec certificat de "
    "conformite (COC) europeen et carnet d'entretien."
)

pdf.output("facture_stark.pdf")
print("OK -> facture_stark.pdf")

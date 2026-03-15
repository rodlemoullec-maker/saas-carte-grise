# Barèmes taxes carte grise — à mettre à jour annuellement
# Source : Service-Public.fr + Code des impositions sur les biens et services

# Tarif par cheval fiscal par région (2025)
TARIF_REGIONAL_PAR_CV = {
    "auvergne_rhone_alpes": 43.00,
    "bourgogne_franche_comte": 51.00,
    "bretagne": 55.00,
    "centre_val_de_loire": 55.00,
    "corse": 27.00,
    "grand_est": 48.00,
    "hauts_de_france": 36.20,
    "ile_de_france": 54.95,
    "normandie": 46.15,
    "nouvelle_aquitaine": 45.00,
    "occitanie": 44.00,
    "pays_de_la_loire": 51.00,
    "provence_alpes_cote_azur": 51.20,
    "guadeloupe": 41.00,
    "guyane": 42.50,
    "martinique": 30.00,
    "mayotte": 30.00,
    "la_reunion": 51.00,
}

# Taxe fixe (redevance d'acheminement)
TAXE_FIXE_Y6 = 11.00

# Exonérations taxe régionale (Y1)
ENERGIES_EXONEREES_Y1 = ["EL", "HY"]  # Électrique, hydrogène
ENERGIES_DEMI_TARIF_Y1 = ["EH", "GH", "GL"]  # Hybrides selon régions

# Taux taxe formation professionnelle (Y3)
TAUX_FORMATION_PRO = 0.01  # 1% de Y1 (pour les pros)

# Barème malus CO2 (Y4) — véhicules neufs première immatriculation
# Applicable uniquement aux VP (voitures particulières)
# Seuil et tarifs 2025
MALUS_CO2_SEUIL = 118  # g/km — en dessous, pas de malus
MALUS_CO2_BAREME = [
    # (co2_min, co2_max, montant_euros)
    (118, 118, 50),
    (119, 119, 75),
    (120, 120, 100),
    (121, 121, 125),
    (122, 122, 150),
    (123, 123, 170),
    (124, 124, 190),
    (125, 125, 210),
    (126, 126, 230),
    (127, 127, 240),
    (128, 128, 260),
    (129, 129, 280),
    (130, 130, 310),
    (131, 131, 330),
    (132, 132, 360),
    (133, 133, 400),
    (134, 134, 450),
    (135, 135, 540),
    (136, 136, 650),
    (137, 137, 740),
    (138, 138, 818),
    (139, 139, 898),
    (140, 140, 983),
    (141, 141, 1074),
    (142, 142, 1172),
    (143, 143, 1276),
    (144, 144, 1386),
    (145, 145, 1504),
    (146, 146, 1629),
    (147, 147, 1761),
    (148, 148, 1901),
    (149, 149, 2049),
    (150, 150, 2205),
    (151, 151, 2370),
    (152, 152, 2544),
    (153, 153, 2726),
    (154, 154, 2918),
    (155, 155, 3119),
    (156, 156, 3331),
    (157, 157, 3552),
    (158, 158, 3784),
    (159, 159, 4026),
    (160, 160, 4279),
    (161, 161, 4543),
    (162, 162, 4818),
    (163, 163, 5105),
    (164, 164, 5404),
    (165, 165, 5715),
    (166, 166, 6039),
    (167, 167, 6375),
    (168, 168, 6724),
    (169, 169, 7086),
    (170, 170, 7462),
    (171, 171, 7851),
    (172, 172, 8254),
    (173, 173, 8671),
    (174, 174, 9103),
    (175, 175, 9550),
    (176, 176, 10011),
    (177, 177, 10488),
    (178, 178, 10980),
    (179, 179, 11488),
    (180, 180, 12012),
    (181, 181, 12552),
    (182, 182, 13109),
    (183, 183, 13682),
    (184, 184, 14273),
    (185, 185, 14881),
    (186, 186, 15506),
    (187, 187, 16149),
    (188, 188, 16810),
    (189, 189, 17490),
    (190, 190, 18188),
    (191, 191, 18905),
    (192, 192, 19641),
    (193, 193, 20396),
    (194, 194, 21171),
    (195, 195, 21966),
    (196, 196, 22781),
    (197, 197, 23616),
    (198, 198, 24472),
    (199, 199, 25349),
    (200, 200, 26247),
    (201, 201, 27166),
    (202, 202, 28107),
    (203, 203, 29070),
    (204, 204, 30056),
    (205, 205, 31063),
    (206, 206, 32094),
    (207, 207, 33148),
    (208, 208, 34224),
    (209, 209, 35324),
    (210, 210, 36447),
    (211, 211, 37595),
    (212, 212, 38767),
    (213, 213, 39964),
    (214, 214, 41185),
    (215, 215, 42431),
    (216, 216, 43703),
    (217, 217, 45000),
    (218, 218, 46323),
    (219, 219, 47672),
    (220, 220, 49047),
    (221, 221, 50449),
    (222, 222, 51878),
    (223, 223, 53333),
    (224, 999, 60000),  # Plafond
]

# Barème malus masse (Y5) — véhicules > 1800 kg
# Applicable uniquement aux VP neufs
MALUS_MASSE_SEUIL = 1800  # kg
MALUS_MASSE_TARIF_PAR_KG = 10  # €/kg au-dessus du seuil
MALUS_MASSE_PLAFOND = 60000  # € max

# Genres de véhicules exemptés de malus CO2 et masse
GENRES_EXEMPTES_MALUS = ["MTL", "MTT1", "MTT2", "CL", "TM", "REM", "RESP"]

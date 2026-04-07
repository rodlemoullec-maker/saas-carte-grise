"""
Templates d'emails de relance pour les blocages V-XX du diagnostic.

Chaque template est un texte personnalisable avec des placeholders
{client_prenom}, {client_nom}, {agent_nom_commerce}, etc.

Le générateur (notifications.relance_emails) :
1. Lit les codes blocages du dossier
2. Pour chaque code, choisit le bon template via RELANCE_TEMPLATES
3. Personnalise avec les données du dossier et de l'agent
4. Assemble le message final dans un email cohérent

Si un code n'a pas de template dédié, on utilise le template générique
qui inclut le message brut du blocage.
"""
from __future__ import annotations


# ─── Templates par code de blocage ──────────────────────────────────────────
#
# Chaque entrée est un fragment qui sera inséré dans la liste des points
# à corriger du mail de relance. Format : un titre court + une explication
# claire pour le client.
# ────────────────────────────────────────────────────────────────────────────

RELANCE_TEMPLATES: dict[str, dict[str, str]] = {

    # ─── CNI / Pièce d'identité ─────────────────────────────────────────────
    "CNI_EXPIREE": {
        "titre": "Pièce d'identité expirée",
        "explication": (
            "Votre carte d'identité est expirée. Merci de me transmettre une "
            "pièce d'identité en cours de validité (carte d'identité ou passeport)."
        ),
    },
    "CNI_DATE_ILLISIBLE": {
        "titre": "Date d'expiration de la pièce d'identité illisible",
        "explication": (
            "Je n'arrive pas à lire la date d'expiration de votre pièce d'identité. "
            "Pourriez-vous m'envoyer une photo plus nette du recto et du verso ?"
        ),
    },
    "CNI_MANQUANT": {
        "titre": "Pièce d'identité manquante",
        "explication": (
            "Il me manque votre pièce d'identité (carte d'identité ou passeport, "
            "recto + verso) pour finaliser votre dossier."
        ),
    },
    "PASSEPORT_MANQUANT": {
        "titre": "Passeport manquant",
        "explication": (
            "Il me manque votre passeport pour finaliser votre dossier."
        ),
    },

    # ─── Permis de conduire ────────────────────────────────────────────────
    "PERMIS_MANQUANT": {
        "titre": "Permis de conduire manquant",
        "explication": (
            "Il me manque votre permis de conduire (recto + verso). "
            "Une simple photo nette suffit."
        ),
    },
    "PERMIS_EXPIRE": {
        "titre": "Permis de conduire expiré",
        "explication": (
            "Votre permis de conduire est expiré. Merci de me transmettre un "
            "permis en cours de validité."
        ),
    },
    "PERMIS_INADAPTE": {
        "titre": "Permis incompatible avec le véhicule",
        "explication": (
            "Votre permis ne couvre pas la catégorie de ce véhicule. "
            "Vérifions ensemble les catégories dont vous disposez."
        ),
    },
    "FORMATION_7H_MANQUANTE": {
        "titre": "Attestation formation 7 heures manquante",
        "explication": (
            "Pour conduire une moto 125cc avec votre permis B, l'attestation de "
            "formation 7 heures est obligatoire. Merci de me la transmettre."
        ),
    },

    # ─── Justificatif de domicile ──────────────────────────────────────────
    "DOMICILE_MANQUANT": {
        "titre": "Justificatif de domicile manquant",
        "explication": (
            "Il me manque votre justificatif de domicile de moins de 6 mois "
            "(facture EDF, eau, internet, ou avis d'imposition récent)."
        ),
    },
    "DOMICILE_TROP_ANCIEN": {
        "titre": "Justificatif de domicile trop ancien",
        "explication": (
            "Votre justificatif de domicile a plus de 6 mois. "
            "Merci de m'en envoyer un plus récent (facture EDF, eau, internet…)."
        ),
    },
    "NOM_DIVERGENT_HEBERGEMENT": {
        "titre": "Attestation d'hébergement nécessaire",
        "explication": (
            "Le nom sur votre justificatif de domicile ne correspond pas au vôtre. "
            "Vous êtes hébergé(e) ? Dans ce cas, merci de me transmettre :\n"
            "  • une attestation d'hébergement signée par votre hébergeant,\n"
            "  • la pièce d'identité (recto + verso) de votre hébergeant."
        ),
    },

    # ─── COC / Certificat de conformité (VN) ───────────────────────────────
    "COC_MANQUANT": {
        "titre": "Certificat de conformité (COC) manquant",
        "explication": (
            "Pour un véhicule neuf, le certificat de conformité (COC) est "
            "obligatoire. Il vous est remis par le concessionnaire à la livraison."
        ),
    },
    "COC_INVALIDE": {
        "titre": "Certificat de conformité illisible",
        "explication": (
            "Je n'arrive pas à lire correctement votre certificat de conformité. "
            "Pourriez-vous me le scanner ou photographier en meilleure qualité ?"
        ),
    },

    # ─── Facture ────────────────────────────────────────────────────────────
    "FACTURE_MANQUANT": {
        "titre": "Facture d'achat manquante",
        "explication": (
            "Il me manque la facture d'achat de votre véhicule pour finaliser "
            "votre dossier."
        ),
    },

    # ─── CG barrée (VO) ─────────────────────────────────────────────────────
    "CG_BARREE_MANQUANT": {
        "titre": "Carte grise barrée manquante",
        "explication": (
            "Pour une voiture d'occasion, j'ai besoin de la carte grise barrée "
            "par le précédent propriétaire (avec la mention « vendu le » + date "
            "+ signature)."
        ),
    },
    "CG_NON_BARREE": {
        "titre": "Carte grise non correctement barrée",
        "explication": (
            "La carte grise que vous m'avez transmise n'est pas barrée correctement. "
            "Le précédent propriétaire doit y inscrire la mention « vendu le » suivie "
            "de la date et de sa signature, puis barrer le document en diagonale."
        ),
    },
    "CG_DATE_VENTE_MANQUANTE": {
        "titre": "Date de vente manquante sur la carte grise",
        "explication": (
            "La date de vente n'est pas indiquée sur la carte grise barrée. "
            "Le précédent propriétaire doit la noter dans la mention « vendu le ___ »."
        ),
    },

    # ─── Cession / 15776 ────────────────────────────────────────────────────
    "CERTIFICAT_CESSION_MANQUANT": {
        "titre": "Certificat de cession manquant",
        "explication": (
            "Il me manque le certificat de cession (Cerfa 15776) signé par vous "
            "et le précédent propriétaire."
        ),
    },

    # ─── VIN / Cohérence véhicule ───────────────────────────────────────────
    "VIN_INCOHERENT": {
        "titre": "Numéro VIN incohérent entre les documents",
        "explication": (
            "Le numéro de série du véhicule (VIN) ne correspond pas entre les "
            "différents documents que vous m'avez transmis. Vérifions ensemble "
            "lequel est correct."
        ),
    },
    "VIN_FORMAT": {
        "titre": "Numéro VIN au format incorrect",
        "explication": (
            "Le numéro VIN n'a pas le bon format (17 caractères attendus). "
            "Pourriez-vous me renvoyer une photo plus nette du document ?"
        ),
    },
    "VIN_CHARS": {
        "titre": "Numéro VIN avec caractères interdits",
        "explication": (
            "Le numéro VIN contient des caractères qui n'existent pas dans un VIN "
            "officiel (I, O ou Q). Il s'agit probablement d'une confusion avec "
            "1, 0 ou 0. Une photo plus nette du document permettrait de lever le doute."
        ),
    },

    # ─── Personne morale / Kbis ─────────────────────────────────────────────
    "KBIS_MANQUANT": {
        "titre": "Extrait Kbis manquant",
        "explication": (
            "Pour une immatriculation au nom d'une société, j'ai besoin d'un "
            "extrait Kbis de moins de 3 mois et de la pièce d'identité du "
            "représentant légal."
        ),
    },
    "KBIS_TROP_ANCIEN": {
        "titre": "Extrait Kbis trop ancien",
        "explication": (
            "Votre extrait Kbis a plus de 3 mois. Merci de m'en envoyer un plus "
            "récent (téléchargeable gratuitement sur infogreffe.fr)."
        ),
    },

    # ─── Co-titulaire ───────────────────────────────────────────────────────
    "COTITULAIRE_MANQUANT": {
        "titre": "Documents du co-titulaire manquants",
        "explication": (
            "Le dossier mentionne un co-titulaire mais je n'ai pas reçu sa pièce "
            "d'identité ni son justificatif de domicile."
        ),
    },

    # ─── Qualité OCR / lisibilité ──────────────────────────────────────────
    "DOCUMENT_ILLISIBLE": {
        "titre": "Document illisible",
        "explication": (
            "Le document que vous m'avez transmis n'est pas suffisamment lisible "
            "pour être traité. Pourriez-vous me le re-scanner ou photographier "
            "dans de meilleures conditions (éclairage, mise au point) ?"
        ),
    },

    # ─── Statut SIV ─────────────────────────────────────────────────────────
    "GAGE_ACTIF": {
        "titre": "Gage actif sur le véhicule",
        "explication": (
            "Un gage est encore actif sur le véhicule. Il faut obtenir une "
            "mainlevée auprès de l'organisme prêteur avant de pouvoir effectuer "
            "le changement de titulaire."
        ),
    },
    "OTCI_ACTIF": {
        "titre": "Opposition au transfert du certificat",
        "explication": (
            "Il y a une opposition au transfert du certificat d'immatriculation "
            "(OTCI) sur ce véhicule. Il faut la lever avant de pouvoir poursuivre."
        ),
    },
    "VEHICULE_VOLE": {
        "titre": "Véhicule signalé volé",
        "explication": (
            "Ce véhicule est signalé comme volé. Je ne peux pas traiter votre "
            "dossier dans ces conditions. Merci de me contacter rapidement."
        ),
    },
}


# ─── Template générique (fallback pour codes non listés) ───────────────────

GENERIC_BLOCAGE_TEMPLATE = {
    "titre": "Document à corriger",
    "explication": "{message}",  # On utilise le message brut du blocage
}


# ─── Squelette de l'email complet ──────────────────────────────────────────

EMAIL_HEADER = """\
Bonjour{client_intro},

Je vous remercie pour les documents que vous m'avez transmis.

Avant de pouvoir finaliser votre dossier de carte grise{vehicule_intro}, j'ai besoin de quelques précisions ou compléments :

"""

EMAIL_FOOTER = """\

Vous pouvez me transmettre les éléments manquants par retour d'email.

Bien cordialement,
{agent_nom}{agent_signature}
"""


# ─── Templates pour cas particuliers ───────────────────────────────────────

EMAIL_CERFA_PRET = """\
Bonjour{client_intro},

Bonne nouvelle : votre dossier est complet et le Cerfa a été préparé.

Je vais maintenant procéder à la soumission auprès du SIV. Vous recevrez votre carte grise par courrier dans les jours qui suivent.

Bien cordialement,
{agent_nom}{agent_signature}
"""

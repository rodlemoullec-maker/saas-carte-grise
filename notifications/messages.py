"""
Messages d'accompagnement centralisés.

Tous les messages affichés à l'utilisateur (vendeur pro et client)
sont définis ici pour garantir un ton cohérent et faciliter les
modifications / traductions futures.

Ton : chaleureux, direct, personnel. Pas de jargon technique.
On tutoie pas mais on est accessible. On guide, on ne blâme pas.
"""
from __future__ import annotations


# ─── Vendeur Pro ─────────────────────────────────────────────────────────────

PRO = {
    # Paramétrage
    "profil_incomplet": (
        "Bienvenue ! Pour commencer, prenez un instant pour completer "
        "votre profil — c'est rapide et ca nous permettra de bien preparer vos dossiers."
    ),
    "profil_pret": "Votre espace est pret ! Vous pouvez creer votre premier dossier.",
    "profil_non_configure": (
        "Bienvenue ! Pour demarrer, configurez votre espace en renseignant "
        "le nom et l'adresse de votre structure — ca ne prend qu'une minute."
    ),

    # Dossier
    "dossier_cree": "Dossier cree ! Deposez vos documents vehicule pour commencer.",
    "docs_manquants": (
        "Il nous manque encore quelques documents, ou certains ne sont pas tout a fait lisibles. "
        "Un petit ajustement et on est bons !"
    ),

    # SMS
    "sms_envoye": "SMS envoye au {telephone} ! Vous serez notifie des que votre client aura depose ses documents.",
    "attente_client": "En attente des documents de votre client. On vous previent des qu'il avance.",
    "client_a_uploade": "Bonne nouvelle ! Votre client a transmis ses documents. Le diagnostic est en cours.",

    # Cerfa
    "cerfa_pret": "Votre Cerfa est pret ! Telechargez-le et soumettez-le au SIV via votre portail habilite.",

    # Diagnostic
    "diagnostic_bloque": (
        "Pour lancer le diagnostic, on a besoin que tous les documents soient deposes "
        "et bien lisibles. Verifiez les pieces manquantes et on avance ensemble !"
    ),
    "cerfa_bloque": (
        "On y est presque ! Pour generer le Cerfa, assurez-vous que tous les documents "
        "sont bien deposes et lisibles."
    ),

    # Assurance
    "assurance_flotte_ok": (
        "Votre assurance flotte couvre ce vehicule — pas besoin de demander "
        "une attestation au client. Une chose de moins a gerer !"
    ),
    "assurance_demander_client": (
        "C'est note ! L'attestation d'assurance sera demandee a votre client. "
        "De notre cote, on verifiera que c'est bien une assurance auto "
        "et que le nom correspond au dossier."
    ),
    "assurance_info_pro": (
        "Pensez a verifier vous-meme que l'assurance couvre bien le vehicule "
        "avant de soumettre au SIV — c'est un point que vous maitrisez mieux que nous !"
    ),
    "assurance_gerer_direct": (
        "Bien note ! Aucune attestation d'assurance ne sera demandee au client "
        "— vous gerez ca directement de votre cote."
    ),
    "assurance_choix_requis": (
        "Plus qu'une petite etape : repondez aux questions sur l'assurance "
        "pour finaliser ce dossier."
    ),

    # Cession
    "pas_de_cession": (
        "Le certificat de cession sera genere par le systeme. "
        "Le client devra le signer numeriquement via le lien SMS."
    ),

    # Suppression / annulation
    "dossier_annule": "Dossier annule.",
    "dossier_finalise": "Dossier deja finalise — annulation impossible.",

    # Erreurs
    "choix_assurance_q2": "Repondez a la question 2 : souhaitez-vous demander l'attestation au client ?",
}


# ─── Client ──────────────────────────────────────────────────────────────────

CLIENT = {
    # Consentement
    "consentement_ok": (
        "Merci pour votre consentement ! Vous pouvez maintenant deposer "
        "vos documents en toute tranquillite."
    ),

    # Checklist
    "intro_checklist": "Voici les documents dont nous avons besoin. Ca prend 2-3 minutes.",

    # CPI
    "cpi_email": "C'est note ! Votre CPI vous sera envoye par email a {email}.",
    "cpi_main_propre": (
        "C'est note ! {nom_commerce} vous contactera directement "
        "une fois qu'il aura finalise le dossier aupres du SIV "
        "pour que vous puissiez recuperer votre CPI."
    ),

    # Session
    "session_premiere_visite": (
        "Vous pouvez fermer cette page a tout moment. "
        "Vos documents seront sauvegardes. "
        "Reouvrez le lien recu par SMS pour reprendre."
    ),
    "session_retour": (
        "Bon retour ! Vous avez deja depose {docs_deposes} document(s). "
        "Il en reste {docs_manquants} a deposer."
    ),
    "session_retour_complet": (
        "Bon retour ! Tous vos documents sont deposes "
        "— plus qu'a confirmer l'envoi !"
    ),

    # Confirmation envoi
    "recap_message": (
        "Tous vos documents sont deposes et valides. "
        "Verifiez la liste ci-dessous puis confirmez l'envoi a {nom_commerce}."
    ),
    "envoi_confirme": (
        "Merci ! Vos documents ont bien ete transmis a {nom_commerce}. "
        "Votre dossier de carte grise va etre finalise."
    ),

    # Suppression doc
    "doc_supprime": (
        "Le document '{doc_type}' a bien ete supprime. "
        "Vous pouvez en deposer un nouveau des que vous etes pret."
    ),
    "docs_deja_envoyes": (
        "Vos documents ont bien ete transmis, tout est en ordre. "
        "Pour toute modification, n'hesitez pas a contacter votre vendeur."
    ),

    # Dossier finalisé
    "dossier_termine": (
        "Merci, vos documents ont bien ete transmis. "
        "Votre dossier de carte grise est en cours de finalisation par {nom_commerce}."
    ),

    # Signature cession
    "cession_avant": "Vous allez signer le certificat de cession. C'est la derniere etape.",
    "cession_otp": "Un code de confirmation a ete envoye au {telephone}. Verifiez vos SMS.",
    "cession_signee": "Signature enregistree ! Telechargez votre exemplaire ci-dessous.",
    "cession_telechargee": (
        "Certificat de cession telecharge. Conservez ce document precieusement."
    ),

    # Blocage permis
    "permis_insuffisant": (
        "Votre permis {categories} ne couvre pas cette puissance. "
        "Il vous faut un permis {permis_requis}. Rapprochez-vous de votre vendeur."
    ),
}


# ─── Doc illisible — escalade progressive ────────────────────────────────────

# ─── Qualite OCR ────────────────────────────────────────────────────────────

QUALITE_OCR = {
    "avertissement": (
        "Qualite moyenne — donnees extraites mais erreurs possibles. "
        "Vous pouvez re-deposer un document plus net si vous le souhaitez."
    ),
}


DOC_ILLISIBLE = {
    "fichier_1ere_tentative": "Document difficile a lire. Essayez de le prendre en photo directement.",
    "fichier_retry": "Le fichier n'est toujours pas lisible. Prenez le document en photo avec un bon eclairage.",
    "photo_1ere_tentative": "La photo n'est pas assez nette. Assurez-vous que le document est bien eclaire et a plat.",
    "photo_retry": "Si le probleme persiste, contactez votre vendeur pour trouver une solution.",
}

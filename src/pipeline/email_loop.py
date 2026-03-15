"""Boucle de polling email — connecte réception → traitement → réponse.

C'est le module qui fait tourner le système en continu :
1. Poll la boîte email
2. Pour chaque nouvel email avec PJ : crée un dossier + traite
3. Envoie la réponse adaptée (accusé, relance, CERFA)

Utilisé par OpenClaw en mode automatique ou lancé directement.
"""

import time
import traceback
from pathlib import Path

from src.email_handler.receiver import EmailReceiver
from src.email_handler.sender import EmailSender
from src.pipeline.orchestrator import process_dossier, update_dossier_data
from config.settings import EMAIL_POLL_INTERVAL


def run_email_loop(
    auto_send: bool = True,
    poll_interval: int = 0,
):
    """Boucle principale : poll email → traite → répond.

    Args:
        auto_send: Si True, envoie les emails automatiquement (mode OpenClaw).
                   Si False, ne fait que traiter (mode dashboard manuel).
        poll_interval: Intervalle de polling en secondes (0 = une seule fois).
    """
    if poll_interval == 0:
        poll_interval = EMAIL_POLL_INTERVAL

    receiver = EmailReceiver()
    sender = EmailSender()

    print(f"Démarrage de la boucle email (polling toutes les {poll_interval}s)")
    print(f"Mode envoi automatique : {'OUI' if auto_send else 'NON'}")
    print()

    while True:
        try:
            _poll_and_process(receiver, sender, auto_send)
        except KeyboardInterrupt:
            print("\nArrêt de la boucle email.")
            break
        except Exception as e:
            print(f"Erreur dans la boucle : {e}")
            traceback.print_exc()

        if poll_interval <= 0:
            break

        time.sleep(poll_interval)


def _poll_and_process(
    receiver: EmailReceiver,
    sender: EmailSender,
    auto_send: bool,
):
    """Un cycle de polling : récupère les emails et les traite."""
    try:
        receiver.connect()
    except Exception as e:
        print(f"Erreur connexion IMAP : {e}")
        return

    emails = receiver.fetch_new_emails()

    if not emails:
        return

    print(f"📧 {len(emails)} nouvel(aux) email(s) détecté(s)")

    for email_data in emails:
        sender_email = email_data.get("sender_email", "")
        subject = email_data.get("subject", "")
        nb_pj = len(email_data.get("attachments", []))

        print(f"  → De: {sender_email} | Sujet: {subject} | PJ: {nb_pj}")

        # 1. Sauvegarder les PJ dans un dossier
        dossier_info = receiver.save_dossier(email_data)
        reference = dossier_info["reference"]
        dossier_path = dossier_info["dossier_path"]

        print(f"    Dossier créé : {reference}")

        # 2. Envoyer accusé réception
        if auto_send and sender_email:
            try:
                sender.send_accuse_reception(sender_email, reference, nb_pj)
                print(f"    Accusé réception envoyé à {sender_email}")
            except Exception as e:
                print(f"    Erreur envoi accusé : {e}")

        # 3. Traiter le dossier
        print(f"    Traitement en cours...")
        result = process_dossier(dossier_path)
        status = result.get("status", "erreur")

        # Sauvegarder l'email source dans le dossier BDD
        if result.get("dossier_id"):
            update_dossier_data(
                result["dossier_id"],
                donnees_extraites={"_sender_email": sender_email},
            )

        # 4. Envoyer la réponse adaptée
        if status == "pret":
            print(f"    ✓ Dossier prêt — CERFA généré")
            if auto_send and sender_email:
                try:
                    cerfa_path = result.get("cerfa_path", "")
                    vehicule = result.get("vehicule", {})
                    sender.send_cerfa(
                        to=sender_email,
                        reference=reference,
                        cerfa_path=cerfa_path,
                        marque=vehicule.get("marque", ""),
                        denomination=vehicule.get("denomination", ""),
                        immatriculation=result.get("immatriculation", ""),
                    )
                    print(f"    CERFA envoyé à {sender_email}")
                except Exception as e:
                    print(f"    Erreur envoi CERFA : {e}")

        elif status == "documents_manquants":
            validation = result.get("validation", {})
            docs_manquants = validation.get("documents_manquants", [])
            erreurs = validation.get("errors", [])

            print(f"    ⚠ Dossier incomplet — {len(docs_manquants)} doc(s) manquant(s)")

            if auto_send and sender_email and (docs_manquants or erreurs):
                try:
                    messages = docs_manquants + erreurs
                    sender.send_relance_documents(sender_email, reference, messages)
                    print(f"    Relance envoyée à {sender_email}")
                except Exception as e:
                    print(f"    Erreur envoi relance : {e}")

        else:
            print(f"    ✗ Erreur de traitement : {result.get('error', 'inconnue')}")

        # Marquer l'email comme lu
        try:
            receiver.mark_as_read(email_data["email_id"])
        except Exception:
            pass

    receiver.disconnect()


def process_once():
    """Fait un seul cycle de polling (utile pour les tests)."""
    run_email_loop(auto_send=False, poll_interval=0)


def process_once_with_send():
    """Fait un seul cycle avec envoi automatique."""
    run_email_loop(auto_send=True, poll_interval=0)

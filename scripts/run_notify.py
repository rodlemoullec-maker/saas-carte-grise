"""Script helper pour le skill OpenClaw carte-grise-notify.
Usage : python scripts/run_notify.py TYPE TO REFERENCE [ARGS...]
  Types : accuse_reception, relance_documents, cerfa, erreur
"""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.email_handler.sender import EmailSender

if len(sys.argv) < 4:
    print("Usage: python run_notify.py TYPE TO REFERENCE [ARGS...]")
    print("  accuse_reception TO REF NB_FICHIERS")
    print("  relance_documents TO REF 'doc1,doc2'")
    print("  cerfa TO REF CERFA_PATH MARQUE DENOM IMMAT")
    print("  erreur TO REF 'err1,err2'")
    sys.exit(1)

sender = EmailSender()
notif_type = sys.argv[1]
to = sys.argv[2]
ref = sys.argv[3]

if notif_type == "accuse_reception":
    nb = int(sys.argv[4]) if len(sys.argv) > 4 else 0
    sender.send_accuse_reception(to, ref, nb)
    print(f"Accusé envoyé à {to}")

elif notif_type == "relance_documents":
    docs = sys.argv[4].split(",") if len(sys.argv) > 4 else []
    sender.send_relance_documents(to, ref, docs)
    print(f"Relance envoyée à {to}")

elif notif_type == "cerfa":
    cerfa_path = sys.argv[4] if len(sys.argv) > 4 else ""
    marque = sys.argv[5] if len(sys.argv) > 5 else ""
    denom = sys.argv[6] if len(sys.argv) > 6 else ""
    immat = sys.argv[7] if len(sys.argv) > 7 else ""
    sender.send_cerfa(to, ref, cerfa_path, marque, denom, immat)
    print(f"CERFA envoyé à {to}")

elif notif_type == "erreur":
    errs = sys.argv[4].split(",") if len(sys.argv) > 4 else []
    sender.send_erreur_validation(to, ref, errs)
    print(f"Erreurs envoyées à {to}")

else:
    print(f"Type inconnu: {notif_type}")
    sys.exit(1)

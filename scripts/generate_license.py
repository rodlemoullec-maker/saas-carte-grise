#!/usr/bin/env python3
"""
Génère une licence AutoDoc Pro signée pour un client.

À LANCER PAR L'ÉDITEUR uniquement (nécessite la clé privée).

La licence générée est un token signé en Ed25519 que le client copie-colle
dans son interface AutoDoc Pro pour activer son installation locale.

Usage :
    python scripts/generate_license.py \\
        --email contact@cabinet-martin.fr \\
        --name "Cabinet Martin SIV" \\
        --type annual \\
        --private-key <hex> \\
        [--days 365]

Types supportés :
    annual    → licence annuelle (365 jours par défaut, ajustable avec --days)
    perpetual → licence perpétuelle (jamais expirée)
    trial     → licence d'essai prolongée (30 jours par défaut)

Le token de licence est imprimé sur stdout. Vous pouvez le copier-coller
dans l'email envoyé au client après son achat.
"""
from __future__ import annotations

import argparse
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Permettre d'importer les modules du projet quel que soit le cwd
sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.license.signer import sign_license


DEFAULT_DAYS = {
    "trial": 30,
    "annual": 365,
    "perpetual": None,  # Pas d'expiration
}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Génère une licence AutoDoc Pro signée pour un client.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--email", required=True, help="Email du client")
    parser.add_argument("--name", required=True, help="Nom commercial du client")
    parser.add_argument(
        "--type",
        choices=["annual", "perpetual", "trial"],
        default="annual",
        help="Type de licence (défaut: annual)",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=None,
        help="Durée en jours (défaut: 365 pour annual, 30 pour trial)",
    )
    parser.add_argument(
        "--private-key",
        required=True,
        help="Clé privée Ed25519 en hex (64 caractères)",
    )

    args = parser.parse_args()

    # Calculer la date d'expiration
    now = datetime.now(timezone.utc)
    days = args.days if args.days is not None else DEFAULT_DAYS[args.type]

    if args.type == "perpetual":
        expires_at = "perpetual"
    else:
        if days is None:
            days = 365
        exp = now + timedelta(days=days)
        expires_at = exp.strftime("%Y-%m-%dT%H:%M:%SZ")

    payload = {
        "license_id": str(uuid.uuid4()),
        "agent_email": args.email,
        "agent_name": args.name,
        "issued_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "expires_at": expires_at,
        "type": args.type,
        "version": 1,
    }

    try:
        token = sign_license(payload, args.private_key.strip())
    except Exception as e:
        print(f"ERREUR : {e}", file=sys.stderr)
        sys.exit(1)

    print()
    print("=" * 70)
    print("LICENCE GÉNÉRÉE")
    print("=" * 70)
    print()
    print(f"Client     : {args.name}")
    print(f"Email      : {args.email}")
    print(f"Type       : {args.type}")
    print(f"Émise le   : {payload['issued_at']}")
    print(f"Expire le  : {expires_at}")
    print(f"License ID : {payload['license_id']}")
    print()
    print("=" * 70)
    print("TOKEN DE LICENCE (à envoyer au client)")
    print("=" * 70)
    print()
    print(token)
    print()
    print("=" * 70)
    print()
    print("Instructions à inclure dans l'email au client :")
    print()
    print("  1. Ouvrez AutoDoc Pro sur votre ordinateur")
    print("  2. Allez dans Paramètres → Licence")
    print("  3. Collez le token ci-dessus dans le champ d'activation")
    print("  4. Cliquez sur \"Activer\"")
    print()


if __name__ == "__main__":
    main()

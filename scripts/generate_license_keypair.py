#!/usr/bin/env python3
"""
Génère une paire de clés Ed25519 pour signer les licences Imatra.

À LANCER UNE SEULE FOIS par l'éditeur, au début du projet.

La clé privée doit être conservée en lieu sûr (gestionnaire de secrets,
trousseau chiffré). Elle ne doit JAMAIS être commitée dans le repo.

La clé publique doit être copiée dans engine/license/signer.py
(constante PUBLIC_KEY_HEX) avant chaque release du logiciel.

Usage :
    python scripts/generate_license_keypair.py

    → affiche les deux clés
    → propose d'écrire la clé publique dans signer.py automatiquement
"""
from __future__ import annotations

import sys
from pathlib import Path

# Permettre d'importer les modules du projet quel que soit le cwd
sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.license.signer import generate_keypair


def main() -> None:
    print("=" * 70)
    print("Imatra — Génération d'une paire de clés Ed25519")
    print("=" * 70)
    print()

    private_hex, public_hex = generate_keypair()

    print("CLÉ PRIVÉE (à GARDER SECRÈTE — ne JAMAIS commiter) :")
    print()
    print(f"   {private_hex}")
    print()
    print("CLÉ PUBLIQUE (à embarquer dans engine/license/signer.py) :")
    print()
    print(f"   {public_hex}")
    print()
    print("=" * 70)
    print()
    print("Étapes suivantes :")
    print()
    print("1. Stockez la CLÉ PRIVÉE dans votre gestionnaire de secrets")
    print("   (1Password, Bitwarden, AWS Secrets Manager, etc.)")
    print()
    print("2. Mettez à jour engine/license/signer.py :")
    print()
    print("   PUBLIC_KEY_HEX = (")
    print(f'       "{public_hex}"')
    print("   )")
    print()
    print("3. Pour générer une licence client :")
    print()
    print("   python scripts/generate_license.py \\")
    print("       --email client@example.com \\")
    print("       --name 'Cabinet Martin' \\")
    print("       --type annual \\")
    print(f"       --private-key {private_hex[:16]}...")
    print()


if __name__ == "__main__":
    main()

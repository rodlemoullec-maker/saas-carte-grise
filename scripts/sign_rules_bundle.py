#!/usr/bin/env python3
"""
Signe un bundle de règles AutoDoc Pro pour publication aux agents installés.

À LANCER PAR L'ÉDITEUR uniquement (nécessite la clé privée).

Usage :
    python scripts/sign_rules_bundle.py \\
        --input rules_bundle.json \\
        --output rules_bundle_signed.json \\
        --private-key <hex>

Le fichier d'entrée doit contenir uniquement le champ "bundle"
(pas de signature). Le fichier de sortie aura la structure :

    {
        "bundle": { ... le contenu du bundle ... },
        "signature": "base64url..."
    }

Cette structure est ensuite déposée sur https://licenses.autodocpro.fr/rules/latest
pour que tous les agents la téléchargent automatiquement.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Permettre d'importer les modules du projet quel que soit le cwd
sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.license.signer import sign_payload


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Signe un bundle de règles AutoDoc Pro pour publication.",
    )
    parser.add_argument("--input", required=True, help="Fichier JSON contenant le bundle (sans signature)")
    parser.add_argument("--output", required=True, help="Fichier JSON de sortie (bundle + signature)")
    parser.add_argument("--private-key", required=True, help="Clé privée Ed25519 en hex (64 caractères)")

    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"ERREUR : fichier d'entrée introuvable : {input_path}", file=sys.stderr)
        sys.exit(1)

    bundle_data = json.loads(input_path.read_text(encoding="utf-8"))

    # Si l'utilisateur a fourni un fichier déjà au format {bundle: {...}, signature: ...},
    # on prend juste le sous-champ "bundle"
    if isinstance(bundle_data, dict) and "bundle" in bundle_data and "signature" in bundle_data:
        bundle_data = bundle_data["bundle"]

    # Sérialisation canonique pour garantir une signature reproductible
    canonical = json.dumps(bundle_data, separators=(",", ":"), sort_keys=True).encode("utf-8")

    try:
        signature = sign_payload(canonical, args.private_key.strip())
    except Exception as e:
        print(f"ERREUR signature : {e}", file=sys.stderr)
        sys.exit(1)

    output = {
        "bundle": bundle_data,
        "signature": signature,
    }

    output_path = Path(args.output)
    output_path.write_text(
        json.dumps(output, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    version = bundle_data.get("version", "unknown")
    print()
    print("=" * 60)
    print("BUNDLE SIGNÉ")
    print("=" * 60)
    print(f"Version  : {version}")
    print(f"Sortie   : {output_path}")
    print(f"Taille   : {output_path.stat().st_size} bytes")
    print()
    print("Étape suivante : déposez ce fichier sur")
    print("    https://licenses.autodocpro.fr/rules/latest")
    print()
    print("Tous les agents installés le récupéreront automatiquement à leur")
    print(f"prochaine vérification (par défaut, dans les 24 heures).")
    print()


if __name__ == "__main__":
    main()

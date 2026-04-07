"""
Système de règles paramétrables AutoDoc Pro local.

Les règles V-XX et C-XX du diagnostic sont structurellement codées en Python
dans engine/pipeline/realtime.py. Mais leurs **paramètres** (seuils, durées
de validité, tarifs régionaux, listes de mots-clés) évoluent avec la
réglementation et doivent pouvoir être mis à jour à distance sans
redéployer le logiciel chez chaque agent.

Ce module gère :

1. **Bundle par défaut** (engine/rules/default_bundle.py) : embarqué dans le
   code source, contient les valeurs de référence au moment de la release.

2. **Bundle local** (data/rules/current.json) : si présent, il prime sur le
   bundle par défaut. Mis à jour par l'updater quand l'éditeur publie une
   nouvelle version signée.

3. **Loader** (engine/rules/loader.py) : charge le bundle, vérifie sa
   signature Ed25519, expose une API `get_rule(key, default)`.

4. **Updater** (engine/rules/updater.py) : interroge périodiquement le serveur
   de l'éditeur pour récupérer la dernière version du bundle, vérifie la
   signature, applique localement.

5. **Endpoints API** (api/routers/rules.py) : expose le statut et permet à
   l'agent de déclencher manuellement une vérification de mise à jour.

L'éditeur publie un nouveau bundle en :
1. Modifiant les paramètres dans le bundle JSON
2. Le signant avec sa clé privée Ed25519 (la même que pour les licences)
3. Le déposant sur le serveur de licences (URL configurable)

Tous les agents installés le récupèrent automatiquement à leur prochaine
vérification (par défaut une fois par jour).
"""

from engine.rules.loader import get_rule, get_current_bundle, RulesBundle

__all__ = ["get_rule", "get_current_bundle", "RulesBundle"]

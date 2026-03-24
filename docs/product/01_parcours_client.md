# Parcours Client & Expérience Utilisateur

## Acteurs et leurs parcours distincts

---

## 1. PARCOURS — LE PROFESSIONNEL (garage / concession)

### Onboarding (1 fois)

```
[Inscription SaaS]
  → Saisie infos société (SIRET, raison sociale, contact)
  → Choix du plan tarifaire
  → Vérification SIRET actif (auto)
  → Upload habilitation SIV (manuel → validé par admin SaaS)
  → Création compte + accès dashboard
  → Formation rapide (vidéo 5 min ou live)
```

### Utilisation quotidienne

```
[Nouveau dossier]
  → Sélectionner le type : Neuf / Occasion / Changement adresse / ...
  → Renseigner les infos basiques (nom client, téléphone)
  → 2 options de collecte documents :
      Option A : Uploader directement depuis le poste
      Option B : Envoyer un lien sécurisé au client (il uploade lui-même)

[Suivi]
  → Dashboard : voir statut en temps réel (PENDING → PROCESSING → ACCEPTE/CORRECTION)
  → Notification push/email si action requise
  → Si CORRECTION : voir exactement ce qui manque + relancer facilement
  → Si ACCEPTE : 1 clic pour soumettre au SIV
  → Confirmation soumission + numéro de suivi SIV
```

### Points de friction à éliminer

| Friction actuelle | Solution dans le SaaS |
|-------------------|-----------------------|
| Oubli d'un document | Checklist visible en temps réel |
| Rejet SIV sans explication | Message d'erreur clair + action corrective |
| Attente de réponse préfecture | Notification automatique dès réponse SIV |
| Ressaisie manuelle des données | OCR + extraction automatique |
| Dossier perdu / mal archivé | Historique complet, recherche rapide |

---

## 2. PARCOURS — LE CLIENT PARTICULIER

### Via lien sécurisé (envoyé par le professionnel)

```
[Réception SMS/Email]
  → "Bonjour [Prénom], votre dossier carte grise est en cours.
     Merci de nous envoyer vos documents ici : [lien]"

[Page d'upload sécurisée]
  → Interface simplifiée (mobile-first — la plupart uploadent depuis leur téléphone)
  → Documents requis listés clairement avec exemples
  → Upload photo directe depuis l'appareil photo (iOS/Android)
  → Feedback immédiat : "Document reçu ✓" ou "Photo floue, reprendre ?"
  → Pas besoin de compte / mot de passe

[Notifications de suivi]
  → "Vos documents ont été reçus"
  → "Votre dossier est en cours de traitement"
  → "Votre carte grise a été demandée — délai : X jours"
  → "Votre carte grise est en chemin !" (si notification SIV reçue)
```

### Expérience mobile — priorité absolue

- Upload photo depuis le téléphone = cas d'usage principal
- Page d'upload responsive, chargement rapide (< 2s)
- Instructions illustrées pour chaque document (ex: "Comment photographier votre CNI ?")
- Détection automatique si photo floue / trop sombre → demander une nouvelle photo avant envoi

---

## 3. PARCOURS — L'AGENT HABILITÉ

```
[Ouverture session matin]
  → Dashboard : file de revue (dossiers REVUE_AGENT)
  → Tri par priorité (ancienneté, type de dossier)

[Revue d'un dossier]
  → Vue côte-à-côte : image du document + données extraites
  → Alertes colorées : rouge = bloquant, orange = warning
  → Comparaison croisements : "VIN COC = VIN Facture ✓"
  → Décision : [Valider] ou [Demander correction] (motif obligatoire)
  → Si fraude suspectée : [Signaler] → escalade

[Fin de journée]
  → Récap : X dossiers traités, X soumis SIV, X en correction
```

---

## 4. FUNNEL DE CONVERSION (Vision SaaS B2B)

```
[Acquisition]
  Recherche Google "logiciel carte grise garage"
  → Bouche-à-oreille (groupes Facebook/WhatsApp garages)
  → Partenariats (logiciels DMS : Irium, CarsDB, Epyx...)
  → Salons professionnels (Equip Auto, Rétromobile...)

[Activation]
  → Landing page claire avec démo vidéo 2 min
  → Essai gratuit 14 jours sans carte bancaire
  → Onboarding guidé : premier dossier traité en < 15 min

[Rétention]
  → Gain de temps mesurable (reporting mensuel : "X heures économisées")
  → Réduction des rejets SIV (KPI visible dans le dashboard)
  → Nouvelles fonctionnalités régulières

[Expansion]
  → Upsell : plan multi-utilisateurs (+ commerciaux)
  → Add-on : SMS client automatiques
  → Réseau : recommandation à d'autres garages

[Revenus]
  → Abonnement mensuel par utilisateur habilité
  → Facturation à l'usage possible (X dossiers/mois inclus)
  → API premium pour DMS (intégration directe)
```

---

## 5. MODÈLE TARIFAIRE (à affiner)

| Plan | Cible | Prix indicatif | Inclus |
|------|-------|----------------|--------|
| Starter | Garage indépendant | 49€/mois | 1 agent habilité, 50 dossiers/mois |
| Pro | Concession moyenne | 129€/mois | 3 agents, 200 dossiers/mois, API |
| Enterprise | Groupe automobile | Sur devis | Agents illimités, intégration DMS, support dédié |

---

## 6. MESSAGES CLÉS (copywriting)

**Accroche principale :**
> "Traitez une carte grise neuf en 3 minutes. Zéro rejet SIV."

**Bénéfices à mettre en avant :**
- Gain de temps : "Ce qui prenait 45 min ne prend plus que 3 min"
- Zéro erreur : "Vérification automatique avant envoi au SIV"
- Simplicité client : "Le client envoie ses docs depuis son téléphone"
- Conformité : "Audit trail complet, vous êtes protégé"
- Scalabilité : "Traitez 10x plus de dossiers avec la même équipe"

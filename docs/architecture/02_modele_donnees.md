# Modèle de Données

## Entités principales

### Dossier

```
Dossier
├── id                  UUID
├── type                Enum (NEUF_PRO_PARTICULIER, ...)
├── status              Enum (PENDING, PROCESSING, ACCEPTE, CORRECTION, REJET, FRAUDE, REVUE_AGENT, SUBMITTED, CLOSED)
├── score               Float (0–100)
├── created_at          DateTime
├── updated_at          DateTime
├── submitted_at        DateTime (SIV)
│
├── professionnel_id    FK → Professionnel
├── agent_id            FK → User (agent qui a validé, si applicable)
│
├── documents[]         → Document[]
├── cross_check_results[] → CrossCheckResult[]
├── blocking_rules[]    → BlockingRule[]
├── issues[]            → Issue[]
│
├── siv_payload         JSON (payload envoyé au SIV)
├── siv_response        JSON (réponse SIV)
├── siv_reference       String (numéro de suivi SIV)
│
└── audit_log[]         → AuditEvent[]
```

### Document

```
Document
├── id                  UUID
├── dossier_id          FK → Dossier
├── type                Enum (COC, FACTURE, CNI, DOMICILE, PERMIS, ASSURANCE, KBIS)
├── status              Enum (PENDING, PROCESSING, EXTRACTED, VALIDATED, REJECTED)
│
├── file_path           String (chemin storage chiffré)
├── file_hash           String (SHA-256 pour intégrité)
├── file_size           Int
├── mime_type           String
├── page_count          Int
│
├── ocr_confidence      Float (score moyen OCR)
├── extracted_data      JSON (données extraites, schema par type)
├── validation_result   JSON (résultat validation individuelle)
│
├── uploaded_at         DateTime
└── processed_at        DateTime
```

### Données extraites par type (JSON schemas)

#### COC
```json
{
  "vin": "string (17)",
  "cnit": "string",
  "marque": "string",
  "modele": "string",
  "energie": "string (normalisé)",
  "carrosserie": "string (code EU)",
  "puissance_kw": "float",
  "puissance_fiscale_cv": "int | null",
  "cylindree_cm3": "int | null",
  "places_assises": "int",
  "ptac_kg": "int",
  "n_homologation_eu": "string",
  "constructeur": "string",
  "date_premiere_immat_ue": "date | null",
  "ocr_confidence": "float"
}
```

#### FACTURE
```json
{
  "vin": "string (17)",
  "marque": "string",
  "modele": "string",
  "energie": "string",
  "date_vente": "date",
  "prix_ht": "float | null",
  "prix_ttc": "float | null",
  "tva_taux": "float | null",
  "siret_vendeur": "string (14)",
  "nom_vendeur": "string",
  "adresse_vendeur": "string",
  "nom_acheteur": "string",
  "adresse_acheteur": "string",
  "n_facture": "string | null",
  "kilometrage": "int | null",
  "mention_neuf": "boolean",
  "ocr_confidence": "float"
}
```

#### CNI / PASSEPORT
```json
{
  "nom_naissance": "string",
  "nom_usage": "string | null",
  "prenoms": ["string"],
  "date_naissance": "date",
  "lieu_naissance": "string",
  "date_expiration": "date",
  "n_document": "string",
  "nationalite": "string",
  "mrz_ligne1": "string | null",
  "mrz_ligne2": "string | null",
  "mrz_valide": "boolean | null",
  "type_document": "string (CNI | PASSEPORT | TITRE_SEJOUR)",
  "ocr_confidence": "float"
}
```

#### DOMICILE
```json
{
  "nom_titulaire": "string",
  "adresse_ligne1": "string",
  "adresse_ligne2": "string | null",
  "code_postal": "string (5)",
  "ville": "string",
  "pays": "string",
  "date_document": "date",
  "type_justificatif": "string",
  "emetteur": "string",
  "ban_normalized": "object | null",
  "ocr_confidence": "float"
}
```

#### PERMIS
```json
{
  "nom": "string",
  "prenom": "string",
  "date_naissance": "date",
  "n_permis": "string",
  "categories": [{"code": "string", "date_obtention": "date", "date_validite": "date"}],
  "restrictions": ["string"],
  "pays_emission": "string",
  "date_delivrance": "date",
  "ocr_confidence": "float"
}
```

#### ASSURANCE
```json
{
  "nom_assure": "string",
  "prenom_assure": "string",
  "vin": "string | null",
  "marque": "string | null",
  "modele": "string | null",
  "n_contrat": "string",
  "date_effet": "date",
  "date_echeance": "date",
  "compagnie": "string",
  "garanties": ["string"],
  "rc_incluse": "boolean",
  "provisoire": "boolean",
  "ocr_confidence": "float"
}
```

### CrossCheckResult

```
CrossCheckResult
├── id                  UUID
├── dossier_id          FK → Dossier
├── rule_name           String (ex: "vin_coc_facture")
├── status              Enum (PASS | FAIL | WARNING | SKIPPED)
├── source_a            String (type doc source)
├── source_b            String (type doc cible)
├── field               String (champ comparé)
├── value_a             String
├── value_b             String
├── confidence          Float
└── detail              String (message explicatif)
```

### Issue (problème détecté)

```
Issue
├── id                  UUID
├── dossier_id          FK → Dossier
├── severity            Enum (BLOCKING | WARNING | INFO)
├── category            Enum (VIN | IDENTITY | VEHICLE | TEMPORAL | DOCUMENT | FRAUD)
├── code                String (ex: "VIN_COC_FACTURE_MISMATCH")
├── document_type       String (document concerné)
├── field               String (champ concerné)
├── message             String (message lisible)
└── correction_action   String (action requise)
```

### AuditEvent

```
AuditEvent
├── id                  UUID
├── dossier_id          FK → Dossier
├── user_id             FK → User | null (null = système)
├── action              String (ex: "DOCUMENT_UPLOADED", "DECISION_OVERRIDE", "SIV_SUBMITTED")
├── previous_status     String | null
├── new_status          String | null
├── metadata            JSON
└── created_at          DateTime
```

## Relations

```
Professionnel (1) ──── (N) Dossier
User/Agent    (1) ──── (N) Dossier
Dossier       (1) ──── (N) Document
Dossier       (1) ──── (N) CrossCheckResult
Dossier       (1) ──── (N) Issue
Dossier       (1) ──── (N) AuditEvent
```

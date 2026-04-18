"""
Tests unitaires pour notifications.relance_emails

Couvre :
- generate_relance_email avec différents scénarios (relance, cerfa_pret, no_blocages)
- Mapping des codes V-XX vers les templates
- Personnalisation (client_intro, vehicule_intro, agent_signature)
- Sujets contextuels
- Fallback générique pour codes inconnus
- Déduplication des blocages
"""
from __future__ import annotations

from dataclasses import dataclass

from notifications.relance_emails import generate_relance_email


# ─── Mocks ──────────────────────────────────────────────────────────────────


@dataclass
class FakeDossier:
    reference: str = "CG-2026-12345"
    immatriculation: str | None = "AB-123-CD"
    vin: str | None = None
    client_prenom: str | None = "Marie"
    client_nom: str | None = "DUPONT"
    client_email: str | None = "marie@example.fr"
    diagnostic: str | None = "ROUGE"
    blocages: list | dict | None = None
    validation_warnings: list | dict | None = None


@dataclass
class FakeAgent:
    nom_commerce: str | None = "Cabinet Martin SIV"
    raison_sociale: str | None = "Cabinet Martin"
    adresse: str | None = "12 rue de la République"
    code_postal: str | None = "27700"
    ville: str | None = "Les Andelys"
    telephone_commerce: str | None = "02 32 54 12 34"
    email_commerce: str | None = "contact@cabinet-martin-siv.fr"
    telephone: str | None = None
    email: str | None = "agent@local"


# ─── Mode "relance" ────────────────────────────────────────────────────────


class TestGenerateRelance:
    def test_simple_relance_one_blocage(self) -> None:
        dossier = FakeDossier(
            blocages=[{"code": "CNI_EXPIREE", "message": "CNI expirée depuis 30 jours"}],
        )
        result = generate_relance_email(dossier, FakeAgent())

        assert result["mode"] == "relance"
        assert result["blocages_count"] == 1
        assert result["to"] == "marie@example.fr"
        assert "1 élément" in result["subject"]
        assert "AB-123-CD" in result["subject"]
        assert "CG-2026-12345" in result["subject"]

        body = result["body"]
        assert "Marie" in body  # Personnalisation prénom
        assert "Pièce d'identité expirée" in body  # Titre du template
        assert "Cabinet Martin SIV" in body  # Signature agent
        assert "12 rue de la République" in body  # Adresse agent

    def test_multiple_blocages(self) -> None:
        dossier = FakeDossier(
            blocages=[
                {"code": "CNI_EXPIREE", "message": "..."},
                {"code": "DOMICILE_TROP_ANCIEN", "message": "..."},
                {"code": "FORMATION_7H_MANQUANTE", "message": "..."},
            ],
        )
        result = generate_relance_email(dossier, FakeAgent())

        assert result["blocages_count"] == 3
        assert "3 éléments" in result["subject"]

        body = result["body"]
        # Les 3 sections doivent être présentes
        assert "1." in body
        assert "2." in body
        assert "3." in body
        assert "Pièce d'identité expirée" in body
        assert "Justificatif de domicile trop ancien" in body
        assert "Attestation formation 7 heures" in body

    def test_deduplication_same_code(self) -> None:
        """Plusieurs blocages avec le même code → un seul dans l'email."""
        dossier = FakeDossier(
            blocages=[
                {"code": "CNI_EXPIREE", "message": "premier"},
                {"code": "CNI_EXPIREE", "message": "deuxième"},
                {"code": "CNI_EXPIREE", "message": "troisième"},
            ],
        )
        result = generate_relance_email(dossier, FakeAgent())
        assert result["blocages_count"] == 1
        # Une seule fois "1." dans le corps (pas 2. ni 3.)
        body = result["body"]
        assert body.count("1.") == 1
        assert "2." not in body

    def test_unknown_code_uses_generic_template(self) -> None:
        dossier = FakeDossier(
            blocages=[{"code": "CODE_INCONNU_XYZ", "message": "Erreur custom détectée"}],
        )
        result = generate_relance_email(dossier, FakeAgent())
        assert result["blocages_count"] == 1
        assert "Erreur custom détectée" in result["body"]


# ─── Mode "cerfa_pret" ─────────────────────────────────────────────────────


class TestCerfaPret:
    def test_diagnostic_vert_returns_cerfa_pret(self) -> None:
        dossier = FakeDossier(
            diagnostic="VERT",
            blocages=[],
        )
        result = generate_relance_email(dossier, FakeAgent())
        assert result["mode"] == "cerfa_pret"
        assert result["blocages_count"] == 0
        assert "complet" in result["subject"].lower()
        assert "Bonne nouvelle" in result["body"]
        assert "Marie" in result["body"]

    def test_cerfa_pret_with_no_diagnostic_falls_back(self) -> None:
        """Sans diagnostic VERT explicite, on tombe en no_blocages."""
        dossier = FakeDossier(
            diagnostic=None,
            blocages=[],
            validation_warnings=[],
        )
        result = generate_relance_email(dossier, FakeAgent())
        assert result["mode"] == "no_blocages"


# ─── Personnalisation ─────────────────────────────────────────────────────


class TestPersonnalisation:
    def test_client_intro_with_prenom(self) -> None:
        dossier = FakeDossier(
            client_prenom="Marie",
            client_nom="DUPONT",
            blocages=[{"code": "CNI_MANQUANT", "message": "..."}],
        )
        result = generate_relance_email(
            dossier,
            FakeAgent(),
        )
        # Quand prenom existe : "Bonjour Marie"
        assert "Bonjour Marie" in result["body"]

    def test_client_intro_without_prenom(self) -> None:
        dossier = FakeDossier(
            client_prenom=None,
            client_nom="DUPONT",
            blocages=[{"code": "CNI_MANQUANT", "message": "..."}],
        )
        result = generate_relance_email(dossier, FakeAgent())
        # Sans prenom mais avec nom
        assert "Bonjour DUPONT" in result["body"]

    def test_client_intro_anonymous(self) -> None:
        dossier = FakeDossier(
            client_prenom=None,
            client_nom=None,
            blocages=[{"code": "CNI_MANQUANT", "message": "..."}],
        )
        result = generate_relance_email(dossier, FakeAgent())
        # Sans nom : juste "Bonjour,"
        assert "Bonjour," in result["body"]

    def test_vehicule_intro_with_immat(self) -> None:
        dossier = FakeDossier(
            immatriculation="AB-123-CD",
            blocages=[{"code": "CNI_MANQUANT", "message": "..."}],
        )
        result = generate_relance_email(dossier, FakeAgent())
        assert "AB-123-CD" in result["body"]

    def test_vehicule_intro_with_vin_only(self) -> None:
        dossier = FakeDossier(
            immatriculation=None,
            vin="WBA1234567890ABCD",
            blocages=[{"code": "CNI_MANQUANT", "message": "..."}],
        )
        result = generate_relance_email(dossier, FakeAgent())
        # VIN tronqué dans l'intro
        assert "WBA12345" in result["body"]

    def test_agent_signature_complete(self) -> None:
        dossier = FakeDossier(blocages=[{"code": "CNI_MANQUANT", "message": "..."}])
        result = generate_relance_email(dossier, FakeAgent())
        body = result["body"]
        assert "Cabinet Martin SIV" in body
        assert "12 rue de la République" in body
        assert "27700 Les Andelys" in body
        assert "Tél : 02 32 54 12 34" in body
        assert "contact@cabinet-martin-siv.fr" in body

    def test_agent_signature_minimal(self) -> None:
        """Agent sans tous les champs : signature minimale."""
        agent = FakeAgent(
            nom_commerce="Solo SIV",
            raison_sociale="Solo SIV",
            adresse=None,
            code_postal=None,
            ville=None,
            telephone_commerce=None,
            email_commerce=None,
            telephone=None,
            email="agent@local",  # ignoré (placeholder)
        )
        dossier = FakeDossier(blocages=[{"code": "CNI_MANQUANT", "message": "..."}])
        result = generate_relance_email(dossier, agent)
        body = result["body"]
        assert "Solo SIV" in body


# ─── Sujets ────────────────────────────────────────────────────────────────


class TestSubject:
    def test_subject_with_immat_and_ref(self) -> None:
        dossier = FakeDossier(
            blocages=[{"code": "CNI_MANQUANT", "message": "..."}],
        )
        result = generate_relance_email(dossier, FakeAgent())
        assert "AB-123-CD" in result["subject"]
        assert "CG-2026-12345" in result["subject"]
        assert "1 élément" in result["subject"]

    def test_subject_singular(self) -> None:
        dossier = FakeDossier(blocages=[{"code": "CNI_MANQUANT", "message": "..."}])
        result = generate_relance_email(dossier, FakeAgent())
        assert "1 élément à compléter" in result["subject"]

    def test_subject_plural(self) -> None:
        dossier = FakeDossier(
            blocages=[
                {"code": "CNI_MANQUANT", "message": "..."},
                {"code": "PERMIS_MANQUANT", "message": "..."},
            ],
        )
        result = generate_relance_email(dossier, FakeAgent())
        assert "2 éléments à compléter" in result["subject"]


# ─── Cas limites ───────────────────────────────────────────────────────────


class TestEdgeCases:
    def test_no_blocages_no_warnings_no_diagnostic(self) -> None:
        dossier = FakeDossier(blocages=None, validation_warnings=None, diagnostic=None)
        result = generate_relance_email(dossier, FakeAgent())
        assert result["mode"] == "no_blocages"
        assert result["body"] == ""

    def test_blocages_as_dict_not_list(self) -> None:
        """Robustesse : blocages stocké comme dict (format alternatif)."""
        dossier = FakeDossier(
            blocages={"blocages": [{"code": "CNI_MANQUANT", "message": "..."}]},
        )
        result = generate_relance_email(dossier, FakeAgent())
        assert result["blocages_count"] == 1

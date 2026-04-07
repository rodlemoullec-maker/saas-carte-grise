"""
Tests smoke — vérifient que tous les modules clés s'importent sans erreur
et que la structure des routes API est cohérente.

Ces tests sont rapides (pas d'OCR, pas de DB, pas de réseau) et servent à
détecter immédiatement une régression d'import après une modification.
"""
from __future__ import annotations


# ─── Imports backend ──────────────────────────────────────────────────────


class TestImportsBackend:
    def test_api_main(self) -> None:
        import api.main  # noqa: F401

    def test_api_routers(self) -> None:
        from api.routers import dossiers, documents, decisions, professionnel, emails  # noqa: F401
        from api.routers import license as license_router  # noqa: F401
        from api.routers import rules  # noqa: F401

    def test_api_models(self) -> None:
        from api.models import base, dossier, document, professionnel, audit  # noqa: F401

    def test_api_dependencies(self) -> None:
        from api.dependencies import get_current_agent, DBSession  # noqa: F401

    def test_storage(self) -> None:
        from storage.document_store import LocalEncryptedStore, get_document_store  # noqa: F401


class TestImportsEngine:
    def test_pipeline(self) -> None:
        from engine.pipeline.realtime import (  # noqa: F401
            classify_document,
            extract_data,
            run_diagnostic,
            set_profil_pro,
            _check_pro_docs,
            _check_client_docs,
            _check_cerfa_blocages,
        )

    def test_cerfa(self) -> None:
        from engine.cerfa_automation.cerfa_filler import CerfaFiller  # noqa: F401
        from engine.cerfa.cerfa_image_annotator import annotate_cerfa_vn, annotate_cerfa_vo  # noqa: F401

    def test_email_parser(self) -> None:
        from engine.email_parser import (  # noqa: F401
            parse_email_bytes,
            extract_hints_from_email,
            EmailAttachment,
            ParsedEmail,
        )

    def test_dossier_matcher(self) -> None:
        from engine.dossier_matcher import (  # noqa: F401
            find_matching_dossier,
            merge_hints,
            DossierMatch,
        )

    def test_license(self) -> None:
        from engine.license.signer import (  # noqa: F401
            sign_license,
            verify_license,
            sign_payload,
            verify_payload,
            generate_keypair,
            LicensePayload,
            LicenseExpired,
            LicenseInvalidSignature,
            LicenseFormatError,
        )
        from engine.license.manager import LicenseManager, LicenseStatus, get_license_manager  # noqa: F401

    def test_rules(self) -> None:
        from engine.rules import get_rule, get_current_bundle, RulesBundle  # noqa: F401
        from engine.rules.loader import save_local_bundle, reload  # noqa: F401
        from engine.rules.updater import check_for_updates, get_update_status  # noqa: F401
        from engine.rules.default_bundle import get_default_bundle, DEFAULT_BUNDLE_VERSION  # noqa: F401

    def test_rgpd(self) -> None:
        from engine.rgpd.cleanup import cleanup_client_data_after_cerfa, cleanup_expired_dossiers  # noqa: F401


class TestImportsIntegrations:
    def test_ocr_providers(self) -> None:
        from integrations.ocr_providers import (  # noqa: F401
            BaseOCRProvider,
            OCRPage,
            OCRResult,
            get_ocr_provider,
        )

    def test_paddle_ocr_provider(self) -> None:
        # On importe la classe sans instancier (pas besoin de paddleocr installé)
        from integrations.ocr_providers.paddle_ocr import PaddleOcrProvider  # noqa: F401


class TestImportsNotifications:
    def test_relance_emails(self) -> None:
        from notifications.relance_emails import generate_relance_email  # noqa: F401

    def test_messages(self) -> None:
        from notifications.messages import PRO, CLIENT  # noqa: F401


# ─── Structure des routes ────────────────────────────────────────────────


class TestRoutesStructure:
    def test_app_has_expected_routes(self) -> None:
        from api.main import app
        paths = {route.path for route in app.routes}

        # Routes critiques attendues
        expected = {
            "/health",
            "/info",
            "/dossiers/",
            "/dossiers/{dossier_id}",
            "/dossiers/{dossier_id}/checklist",
            "/dossiers/{dossier_id}/run-diagnostic",
            "/dossiers/{dossier_id}/cerfa",
            "/dossiers/{dossier_id}/relance-email",
            "/dossiers/{dossier_id}/admin",
            "/dossiers/{dossier_id}/download-zip",
            "/documents/{dossier_id}/upload",
            "/documents/{document_id}",
            "/decisions/{dossier_id}",
            "/decisions/{dossier_id}/retry",
            "/agent",
            "/agent/cachet",
            "/agent/signature",
            "/agent/kbis",
            "/emails/upload",
            "/emails/preview",
            "/license/status",
            "/license/activate",
            "/license/deactivate",
            "/rules/status",
            "/rules/check-update",
            "/rules/inspect",
        }
        missing = expected - paths
        assert not missing, f"Routes manquantes : {sorted(missing)}"

    def test_no_obsolete_routes(self) -> None:
        """Aucune route SaaS obsolète ne doit subsister."""
        from api.main import app
        paths = {route.path for route in app.routes}

        # Routes qui ne doivent PLUS exister après la migration locale
        forbidden = {
            "/public/{slug}",
            "/client/{token}",
            "/scan/{token}",
            "/webhooks/stripe",
            "/webhooks/siv",
            "/dossiers/batch",
            "/dossiers/batch/launch",
        }
        present = forbidden & paths
        assert not present, f"Routes obsolètes encore présentes : {sorted(present)}"


# ─── Cohérence config ────────────────────────────────────────────────────


class TestConfig:
    def test_settings_default_class_uses_sqlite(self) -> None:
        """
        Vérifie que le DÉFAUT de la classe Settings (sans .env) pointe vers SQLite.
        On ne charge pas un Settings() réel car le .env local de la machine de dev
        peut surcharger DATABASE_URL avec une URL héritée du SaaS.
        """
        from config.settings import Settings
        # Inspecter le défaut sans instancier (sinon .env est lu)
        default_url = Settings.model_fields["database_url"].default
        assert "sqlite" in default_url.lower()

    def test_settings_default_ocr_paddle(self) -> None:
        from config.settings import Settings
        assert Settings.model_fields["ocr_provider"].default == "paddle"

    def test_settings_default_imatra_db(self) -> None:
        from config.settings import Settings
        assert "imatra" in Settings.model_fields["database_url"].default.lower()

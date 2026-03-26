"""Tests unitaires — CompletenessValidator (V-01 → V-10, V-36)."""
from __future__ import annotations

import pytest

from engine.validators.completeness import (
    CompletenessValidator,
    DossierDocuments,
    FlowType,
)


class TestCompletenessVN:
    """Tests complétude VN (véhicule neuf)."""

    def setup_method(self):
        self.v = CompletenessValidator()

    def _full_vn_docs(self, **overrides) -> DossierDocuments:
        defaults = dict(
            cni_ou_passeport=True, permis=True, justif_domicile=True,
            cerfa_cg=True, mandat=True, coc=True, assurance=True,
            attestation_identite_pro=True,
        )
        defaults.update(overrides)
        return DossierDocuments(**defaults)

    def test_all_docs_present(self):
        result = self.v.validate(FlowType.VN, self._full_vn_docs())
        assert result.valid is True

    def test_cni_missing(self):
        result = self.v.validate(FlowType.VN, self._full_vn_docs(cni_ou_passeport=False))
        assert result.valid is False
        assert any(e.code == "V-01" for e in result.errors)

    def test_permis_missing(self):
        result = self.v.validate(FlowType.VN, self._full_vn_docs(permis=False))
        assert result.valid is False
        assert any(e.code == "V-02" for e in result.errors)

    def test_permis_not_required_for_pm(self):
        result = self.v.validate(
            FlowType.VN,
            self._full_vn_docs(permis=False, is_personne_morale=True),
        )
        # Pas de V-02 pour PM
        assert not any(e.code == "V-02" for e in result.errors)

    def test_coc_missing_vn(self):
        result = self.v.validate(FlowType.VN, self._full_vn_docs(coc=False))
        assert result.valid is False
        assert any(e.code == "V-10" for e in result.errors)

    def test_assurance_missing(self):
        result = self.v.validate(FlowType.VN, self._full_vn_docs(assurance=False))
        assert result.valid is False
        assert any(e.code == "V-09" for e in result.errors)

    def test_attestation_pro_missing(self):
        result = self.v.validate(FlowType.VN, self._full_vn_docs(attestation_identite_pro=False))
        assert result.valid is False
        assert any(e.code == "V-38" for e in result.errors)


class TestCompletenessVO:
    """Tests complétude VO (véhicule d'occasion)."""

    def setup_method(self):
        self.v = CompletenessValidator()

    def _full_vo_docs(self, **overrides) -> DossierDocuments:
        defaults = dict(
            cni_ou_passeport=True, permis=True, justif_domicile=True,
            cerfa_cg=True, mandat=True, assurance=True,
            attestation_identite_pro=True,
            cerfa_cession=True, cg_barree=True, controle_technique=True,
            da=True, recepisse_da=True,
        )
        defaults.update(overrides)
        return DossierDocuments(**defaults)

    def test_all_docs_present(self):
        result = self.v.validate(FlowType.VO, self._full_vo_docs())
        assert result.valid is True

    def test_cession_missing(self):
        result = self.v.validate(FlowType.VO, self._full_vo_docs(cerfa_cession=False))
        assert result.valid is False
        assert any(e.code == "V-06" for e in result.errors)

    def test_cg_barree_missing(self):
        result = self.v.validate(FlowType.VO, self._full_vo_docs(cg_barree=False))
        assert result.valid is False
        assert any(e.code == "V-07" for e in result.errors)

    def test_cg_barree_missing_but_perdue(self):
        result = self.v.validate(FlowType.VO, self._full_vo_docs(cg_barree=False, cg_perdue=True))
        # WARNING, pas BLOCKING
        assert not any(e.code == "V-07" and e.level.value == "BLOCKING" for e in result.errors)

    def test_ct_missing(self):
        result = self.v.validate(FlowType.VO, self._full_vo_docs(controle_technique=False))
        assert result.valid is False
        assert any(e.code == "V-08" for e in result.errors)

    def test_ct_missing_but_dispense(self):
        result = self.v.validate(
            FlowType.VO,
            self._full_vo_docs(controle_technique=False, ct_dispense=True),
        )
        # Dispensé → pas de V-08
        assert not any(e.code == "V-08" for e in result.errors)

    def test_ct_dispense_but_volontaire(self):
        # CT volontaire sur dispensé → DEVIENT obligatoire
        result = self.v.validate(
            FlowType.VO,
            self._full_vo_docs(controle_technique=False, ct_dispense=True, ct_volontaire=True),
        )
        assert any(e.code == "V-08" for e in result.errors)

    def test_da_missing(self):
        result = self.v.validate(FlowType.VO, self._full_vo_docs(da=False))
        assert result.valid is False
        assert any(e.code == "V-36" for e in result.errors)

    def test_mineur_docs_required(self):
        result = self.v.validate(
            FlowType.VO,
            self._full_vo_docs(is_mineur=True, autorisation_parentale=False, livret_famille=False),
        )
        assert any(e.code == "V-MINEUR-01" for e in result.errors)
        assert any(e.code == "V-MINEUR-02" for e in result.errors)

    def test_etranger_titre_sejour_required(self):
        result = self.v.validate(
            FlowType.VO,
            self._full_vo_docs(is_etranger=True, titre_sejour=False),
        )
        assert any(e.code == "V-13" for e in result.errors)

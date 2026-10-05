"""Tests for labeled .expected.json fixtures [SCRUM-408].

Verifies that:
- Fixtures load via load_expected_fixtures()
- All fixture files are valid JSON with required keys
- Document paths point to existing files
- Definition IDs match known prebuilt definitions
- Template fields are represented in expected values
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.eval.fixtures import ExpectedFixture, load_expected_fixtures


SAMPLE_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "sample-data"


# Prebuilt definition IDs from src/definitions/prebuilt.py
KNOWN_DEFINITION_IDS = {
    "def-invoice",
    "def-trade-finance-scrutiny",
    "def-boq-estimator",
    "def-compliance-audit",
    "def-commercial-lease",
    "def-commodity-trade",
    "def-metallurgical-assay",
    "def-medical-claim",
    "def-store-audit",
    "def-thermal-receipt",
    "def-ad-buy",
    "def-utility-bill",
    "def-bank-statement",
    "def-purchase-order",
    "def-purchase-order-sf1449",
    "def-packing-list",
    "def-packing-list-travel",
    "def-w2-tax-form",
    "def-pay-stub",
    "def-insurance-policy",
    "def-pnid-to-dexpi",
}


# Expected fixture count per type (minimum)
EXPECTED_TYPES = {
    "invoices": 4,
    # Lowered from 2 to 1 in ADE-9: the second statement was a byte-identical copy of the first PDF with
    # invented expected values, so it added no coverage. Raise back to 2 (ADE-10) once a genuinely
    # different bank statement with verified expected values is added.
    "bank-statements": 1,
    "utility-bills": 2,
    "purchase-order": 2,
    "pay-stub": 2,
}


class TestFixtureLoading:
    """Verify fixtures load correctly via load_expected_fixtures [SCRUM-408]."""

    def test_fixtures_exist(self):
        """At least 10 .expected.json files should exist across 5 types."""
        all_files = list(SAMPLE_DATA_DIR.rglob("*.expected.json"))
        assert len(all_files) >= 10, f"Expected >= 10 fixture files, found {len(all_files)}"

    def test_load_all_fixtures(self):
        """load_expected_fixtures should return all fixtures from sample-data/."""
        fixtures = load_expected_fixtures(SAMPLE_DATA_DIR)
        assert len(fixtures) >= 10, f"Expected >= 10 fixtures, got {len(fixtures)}"

    def test_fixtures_per_type(self):
        """Each expected type folder should have the minimum fixture count."""
        for folder, min_count in EXPECTED_TYPES.items():
            files = list((SAMPLE_DATA_DIR / folder).glob("*.expected.json"))
            assert len(files) >= min_count, (
                f"{folder}/ has {len(files)} fixtures, expected >= {min_count}"
            )


class TestFixtureValidity:
    """Each loaded fixture should have valid structure [SCRUM-408]."""

    @pytest.fixture(scope="class")
    def all_fixtures(self) -> list[ExpectedFixture]:
        return load_expected_fixtures(SAMPLE_DATA_DIR)

    def test_all_have_definition_id(self, all_fixtures: list[ExpectedFixture]):
        for f in all_fixtures:
            assert f.definition_id, f"Fixture for {f.document_path} has no definition_id"

    def test_definition_ids_are_known(self, all_fixtures: list[ExpectedFixture]):
        for f in all_fixtures:
            assert f.definition_id in KNOWN_DEFINITION_IDS, (
                f"Fixture {f.document_path} has unknown definition_id: {f.definition_id}"
            )

    def test_all_have_expected_values(self, all_fixtures: list[ExpectedFixture]):
        for f in all_fixtures:
            assert len(f.expected) > 0, f"Fixture {f.document_path} has empty expected values"

    def test_document_paths_exist(self, all_fixtures: list[ExpectedFixture]):
        for f in all_fixtures:
            doc_path = Path(f.document_path)
            assert doc_path.exists(), f"Document does not exist: {f.document_path}"

    def test_all_have_document_field(self, all_fixtures: list[ExpectedFixture]):
        """Each fixture should have a non-empty document path."""
        for f in all_fixtures:
            assert f.document_path, "Fixture has empty document_path"


class TestFixtureContent:
    """Verify fixture content matches template fields [SCRUM-408]."""

    @pytest.fixture(scope="class")
    def all_fixtures(self) -> list[ExpectedFixture]:
        return load_expected_fixtures(SAMPLE_DATA_DIR)

    def test_invoice_fixtures_have_core_fields(self, all_fixtures: list[ExpectedFixture]):
        invoice_fixtures = [f for f in all_fixtures if f.definition_id == "def-invoice"]
        assert len(invoice_fixtures) >= 4
        for f in invoice_fixtures:
            for field in ("invoice_number", "invoice_date", "vendor", "total"):
                assert field in f.expected, (
                    f"Invoice fixture {f.document_path} missing field: {field}"
                )

    def test_bank_statement_fixtures_have_core_fields(self, all_fixtures: list[ExpectedFixture]):
        bs_fixtures = [f for f in all_fixtures if f.definition_id == "def-bank-statement"]
        assert len(bs_fixtures) >= 1  # was 2; see ADE-9 / ADE-10 (the second one was a duplicate)
        for f in bs_fixtures:
            for field in ("bank_name", "account_number", "opening_balance", "closing_balance"):
                assert field in f.expected, (
                    f"Bank statement fixture {f.document_path} missing field: {field}"
                )

    def test_utility_bill_fixtures_have_core_fields(self, all_fixtures: list[ExpectedFixture]):
        ub_fixtures = [f for f in all_fixtures if f.definition_id == "def-utility-bill"]
        assert len(ub_fixtures) >= 2
        for f in ub_fixtures:
            for field in ("account_number", "utility_type", "amount_due", "due_date"):
                assert field in f.expected, (
                    f"Utility bill fixture {f.document_path} missing field: {field}"
                )

    def test_purchase_order_fixtures_have_core_fields(self, all_fixtures: list[ExpectedFixture]):
        po_fixtures = [
            f
            for f in all_fixtures
            if f.definition_id in ("def-purchase-order", "def-purchase-order-sf1449")
        ]
        assert len(po_fixtures) >= 2
        for f in po_fixtures:
            for field in ("po_number", "po_date", "buyer", "vendor", "total"):
                assert field in f.expected, (
                    f"Purchase order fixture {f.document_path} missing field: {field}"
                )

    def test_pay_stub_fixtures_have_core_fields(self, all_fixtures: list[ExpectedFixture]):
        ps_fixtures = [f for f in all_fixtures if f.definition_id == "def-pay-stub"]
        assert len(ps_fixtures) >= 2
        for f in ps_fixtures:
            for field in ("employee_name", "employer_name", "gross_pay", "net_pay"):
                assert field in f.expected, (
                    f"Pay stub fixture {f.document_path} missing field: {field}"
                )

    def test_numeric_tolerances_present(self, all_fixtures: list[ExpectedFixture]):
        """Fixtures with numeric expected values should have tolerances for money fields."""
        for f in all_fixtures:
            if "total" in f.expected and isinstance(f.expected["total"], (int, float)):
                assert "total" in f.tolerances, (
                    f"Fixture {f.document_path} has numeric 'total' but no tolerance"
                )


class TestBenchmarkSuiteWithRealFixtures:
    """Verify the benchmark suite can discover and use the real fixtures [SCRUM-408]."""

    def test_load_fixtures_from_invoices_dir(self):
        """load_expected_fixtures should find fixtures in invoices/ subfolder."""
        fixtures = load_expected_fixtures(SAMPLE_DATA_DIR / "invoices")
        assert len(fixtures) >= 4
        for f in fixtures:
            assert f.definition_id == "def-invoice"

    def test_load_fixtures_from_bank_statements_dir(self):
        fixtures = load_expected_fixtures(SAMPLE_DATA_DIR / "bank-statements")
        assert len(fixtures) >= 1  # was 2; see ADE-9 / ADE-10 (the second one was a duplicate)
        for f in fixtures:
            assert f.definition_id == "def-bank-statement"

    def test_load_fixtures_from_utility_bills_dir(self):
        fixtures = load_expected_fixtures(SAMPLE_DATA_DIR / "utility-bills")
        assert len(fixtures) >= 2
        for f in fixtures:
            assert f.definition_id == "def-utility-bill"

    def test_load_fixtures_from_purchase_order_dir(self):
        fixtures = load_expected_fixtures(SAMPLE_DATA_DIR / "purchase-order")
        assert len(fixtures) >= 2

    def test_load_fixtures_from_pay_stub_dir(self):
        fixtures = load_expected_fixtures(SAMPLE_DATA_DIR / "pay-stub")
        assert len(fixtures) >= 2
        for f in fixtures:
            assert f.definition_id == "def-pay-stub"

    def test_benchmark_suite_can_load_all_fixture_types(self):
        """The benchmark suite's run_benchmark_suite should be able to load fixtures
        from each subfolder without errors."""
        from src.eval.benchmark_suite import run_benchmark_suite

        # We don't run the suite (requires credentials), but we verify
        # that load_expected_fixtures works for each type
        for folder in EXPECTED_TYPES:
            fixtures = load_expected_fixtures(SAMPLE_DATA_DIR / folder)
            assert len(fixtures) > 0, f"No fixtures found in {folder}/"

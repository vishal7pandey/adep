# Sample Data

Sample documents for testing ADEP extraction agents. Each subfolder
corresponds to a skill/template category.

Planning note: for a curated source catalog and recommended corpus mix,
see [SOURCE-MAP.md](SOURCE-MAP.md).

## Current Inventory

| Folder | Files | Source | Notes |
|--------|-------|--------|-------|
| `invoices/` | 2 PDFs, 2 JPGs | Azure Form Recognizer, SampleFile.com, Wikimedia Commons | 2 standard commercial invoice PDFs; `sample-invoice-03.jpg` is a real multi-page itemized international shipping invoice (Annie International Inc., HTSUS codes, per-unit pricing); `sample-invoice-04.jpg` is a real handwritten 19th-century itemized statement of expenses |
| `bank-statements/` | 2 PDFs | SampleFile.com | Account-statement style samples for parser/regression tests with summary balances and transaction-like sections. |
| `contracts/` | 2 PDFs | SampleFile.com, SEC EDGAR (public domain U.S. government filing) | `sample-contract-01.pdf` is a short generic contract; `sample-contract-02-distribution-agreement-sec.pdf` is a real, fully-executed, modern (2022) Exclusive Distribution Agreement between two named companies filed as an exhibit with the SEC — real signatures, addresses, governing law, term/termination clauses |
| `utility-bills/` | 2 PDFs | DC DOE / Pepco; Cape Light Compact / FirstEnergy explainer | Includes one residential electric bill and one annotated "how to read your electric bill" sample useful for field-label mapping and charge-section extraction. |
| `medical-claims/` | 2 PDFs | CMS.gov, SFHP.org | CMS-1500 health insurance claim forms |
| `boq/` | 1 PDF | ConstructionEstimatorIndia.com | Bill of quantities with line items |
| `circuit-diagrams/` | 3 JPGs | Wikimedia Commons (CC / public domain) | Real-world complex circuit drawings (historic telecom and Bell technical diagrams) for dense-symbol OCR and diagram parsing tests. |
| `chip-boards/` | 3 JPGs | Wikimedia Commons (CC / public domain) | High-detail PCB/chip-board imagery (motherboard and module component/foil sides) suited for teardown-style visual analysis and component labeling. |
| `engineering-drawings/` | 3 JPGs | NASA Images API (public domain / NASA media usage policy) | Detailed engineering cutaways and line drawings (X-15, Apollo CSM changes, zero-g propulsion unit) for technical drawing extraction and layout parsing. |
| `pid-diagrams/` | 3 JPGs, 3 PDFs | Wikimedia Commons (public domain / CC), University of Oklahoma, AquaEnergy Knowledge Hub | Mixed-format P&ID set: archival process diagrams plus dense educational/reference P&ID documents for symbol/tag extraction and process-line interpretation. Maps to the `pid_diagram` skill/template. |
| `bill-of-materials/` | 2 JPGs | Wikimedia Commons — U.S. National Archives (NARA) & Historic American Engineering Record (HAER), public domain | Real archival bills of material: a WWII-era US Navy destroyer marine reduction gear BOM, and a 1929 highway bridge reinforcing-steel bill of materials with bent-bar schedules |
| `receipts/` | 2 JPGs | Wikimedia Commons — Digital Public Library of America (DPLA), public domain | Real handwritten itemized 1845 household bills/receipts (St. Louis carriage storage, misc. purchases) |
| `insurance-policy/` | 2 JPGs | Wikimedia Commons, public domain | Real filled-out insurance policies: a 1936 Japanese Government-General of Korea Post Office policy, and an 1909 German fire insurance policy (Londoner Phönix Feuer-Assecuranz-Societät). Maps to the `insurance_policy` skill/template (no folder existed previously). |
| `trade-finance/` | 1 JPG, 3 PDFs | Wikimedia Commons (public domain); SEC EDGAR (public domain U.S. government filing); Black Horse International Trade | Expanded letter-of-credit coverage with real/historical LC plus MT700-style draft and LC agreement reference docs for documentary credit field extraction and workflow validation. |
| `leases/` | 2 PDFs | SEC EDGAR (public domain U.S. government filing); HUD Housing Counselors | `sample-lease-02-color-image-sec.pdf` remains the real executed commercial lease amendment; `sample-lease-03-hud-lease-agreements-training.pdf` adds lease-agreement instructional content and structured lease terminology for extraction robustness. |
| `compliance-audits/` | 2 PDFs | GAO / files.gao.gov (U.S. government) | Real audit and audit-methodology references: Government Auditing Standards revision and GAO Financial Audit Manual Volume 3. Useful for long-form compliance language, controls terminology, and audit-report structure. |
| `commodity-trade/` | 5 PDFs | g2b.co, OneMotoring (LTA Singapore), Off-OPEC/BLCO procedure sources | Added BLCO FOB/CIF procedural and export-grade documentation to improve crude-trade workflow realism (nominations, shipping, documentation requirements) in addition to bill-of-lading artifacts. |
| `metallurgical-assay/` | 2 PDFs | NIST SRM certificates | Real ore assay-style certificates of analysis (iron ore and manganese ore SRMs) with certified composition/value tables and uncertainty context. |
| `store-audits/` | 2 PDFs | APG Solutions, Inpas Pages | Practical retail/store audit checklists (including ISO-9001-oriented checklist format) for checklist extraction, pass/fail item parsing, and procedural compliance fields. |
| `ad-buy/` | 2 PDFs | SIAM, Education Next | Real insertion order documents for print/media ads, including placement terms, rates, issue schedule, and advertiser metadata. Useful for ad-buy workflow extraction. |
| `packing-list/` | 2 PDFs | PrintableSample; TracAbout | Added a second packing-checklist layout (`sample-packing-list-02-travel-packing-checklist.pdf`) to broaden checklist-style OCR and section/checkbox extraction coverage. |
| `purchase-order/` | 2 PDFs | LegalTemplates; GSA | Added `sample-purchase-order-02-sf1449.pdf` (U.S. Standard Form 1449, Solicitation/Contract/Order) to complement template-style POs with a formal government order form structure. |
| `pay-stub/` | 2 PDFs | U.S. military/public payroll guidance sources | Leave and Earnings Statement (LES) style payroll samples with earnings, deductions, and leave balances suitable for payroll field extraction and numeric reconciliation tests. |
| `w2-tax-form/` | 2 PDFs | IRS VITA sample, University payroll sample | Filled/sample W-2 style documents for wage/tax-box extraction and tax-form layout parsing. Includes one IRS-hosted training sample and one institutional sample explainer form. |

## Adding More Samples

1. Download free sample documents from:
   - [SampleFile.com](https://samplefile.com/samples/document/pdf/)
   - [Novus Examples](https://examples.novusstreamsolutions.com/documents)
   - [ExpressExpense](https://expressexpense.com/blog/free-receipt-images-ocr-machine-learning-dataset/) (200 receipt images)
   - Government forms (CMS, IRS, etc.)
   - [Wikimedia Commons](https://commons.wikimedia.org/) — real, openly-licensed (public domain / CC) scans of historical and archival invoices, receipts, engineering diagrams (P&ID), and bills of material (NARA/HAER collections). Use `Special:FilePath/<File name>` for a direct, redirect-following download URL; append `?width=NNNN` to get a smaller rendered JPEG instead of a huge original TIFF.
   - [SEC EDGAR Full Text Search](https://www.sec.gov/edgar/search/) — real, modern, professionally drafted legal/financial documents (leases, distribution/supply agreements, letters of credit, etc.) filed as exhibits to public company filings, all public domain U.S. government records. Query the JSON API directly (requires a descriptive `User-Agent` header): `https://efts.sec.gov/LATEST/search-index?q=%22exact+phrase%22&forms=EX-10`, then build the document URL as `https://www.sec.gov/Archives/edgar/data/{CIK}/{accession-no-dashes}/{filename}` from the `_id` field (`accession:filename`). Many exhibits are plain `.txt`/`.htm` — render to PDF locally (e.g. with `reportlab` + `beautifulsoup4`, both already available in this repo's environment) rather than fabricating content, preserving the verbatim real text.
2. Place in the appropriate subfolder
3. Name files as `sample-{type}-NN.pdf` (or `.jpg`)
4. Update this README

## Usage

Point ADEP agent definitions at these files to test extraction:
```python
run(definition="def-invoice-v1", document_path="sample-data/invoices/sample-invoice-01.pdf")
```

## Labeled Fixtures (.expected.json)

Each `.expected.json` file pairs a sample document with ground-truth field values,
tolerances, and minimum confidence thresholds for the benchmark suite
(`src/eval/benchmark_suite.py`) and evaluation harness (`src/eval/harness.py`).

Current labeled fixtures (10 files across 5 types):

| Folder | Fixtures | Definition ID | Template Fields |
|--------|----------|---------------|-----------------|
| `invoices/` | 4 | `def-invoice` | invoice_number, invoice_date, due_date, vendor, subtotal, tax, total |
| `bank-statements/` | 2 | `def-bank-statement` | bank_name, account_number, account_holder, statement_period, balances, totals |
| `utility-bills/` | 2 | `def-utility-bill` | account_number, service_address, billing_period, utility_type, usage, amount_due |
| `purchase-order/` | 2 | `def-purchase-order` / `def-purchase-order-sf1449` | po_number, po_date, buyer, vendor, total |
| `pay-stub/` | 2 | `def-pay-stub` | employee_name, employer_name, pay dates, gross/net pay, taxes |

Load fixtures programmatically:
```python
from src.eval.fixtures import load_expected_fixtures
fixtures = load_expected_fixtures("sample-data/invoices/")
```

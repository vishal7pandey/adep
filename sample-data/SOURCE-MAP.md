# Sample Data Source Map

Practical source map for building a robust demo corpus, grouped by document type and use case.

## Best source types

- Government/public datasets: realistic forms, IDs, financials, handwritten samples, and multilingual docs.
- Research/benchmark datasets: OCR, layout, tables, receipts, invoices, and document understanding evals.
- Open-source synthetic generators: high volume, controlled variation, and labeled ground truth.
- Public company filings and reports: engineering, financial, and annual-report style docs.
- Open repositories/scans/archives: handwritten, historical, and noisy real-world pages.

## Strong sources by category

| Category | Sources | Notes |
|---|---|---|
| General document understanding | [DocVQA](https://www.docvqa.org/), [RVL-CDIP](https://www.cs.cmu.edu/~aharley/rvl-cdip/), [PubLayNet](https://github.com/ibm-aur-nlp/PubLayNet) | Baseline for layouts, page types, and document QA. |
| OCR and text extraction | [IAM Handwriting Database](https://fki.tic.heia-fr.ch/databases/iam-handwriting-database), [UW3](https://tc11.cvc.uab.es/datasets/), [SROIE](https://rrc.cvc.uab.es/?ch=13) | IAM for handwriting; SROIE for receipts. |
| Invoices, receipts, forms | [CORD](https://github.com/clovaai/cord), [FUNSD](https://guillaumejaume.github.io/FUNSD/), [XFUND](https://github.com/doc-analysis/XFUND) | Key-value extraction and form understanding. |
| Tables and financial docs | [FinTabNet](https://github.com/console-operator/FinTabNet), [SciTSR](https://github.com/Visuallish/SciTSR), [PubTables-1M](https://github.com/microsoft/table-transformer) | Table structure and tabular extraction. |
| Scientific/engineering docs | [arXiv PDF dataset](https://arxiv.org/help/bulk_data), [PubMed Central Open Access](https://pmc.ncbi.nlm.nih.gov/tools/openftlist/), [S2ORC](https://allenai.org/data/s2orc) | Technical language, figures, citations, equations, dense layouts. |
| Business/financial filings | [SEC EDGAR](https://www.sec.gov/edgar/search-and-access), [UK Companies House](https://find-and-update.company-information.service.gov.uk/), [EDINET](https://disclosure2dl.edinet-fsa.go.jp/) | Annual reports, prospectuses, exhibits, statements. |
| Handwritten documents | [IAM](https://fki.tic.heia-fr.ch/databases/iam-handwriting-database), [RIMES](https://www.a2ialab.com/doku.php?id=rimes_database), [Bentham](https://www.cvc.uab.es/?s=publications&id=1809) | Cursive, historical, variable handwriting. |
| Historical/archival scans | [Balsac](https://www.balsac.ca/), [HathiTrust](https://www.hathitrust.org/), [Internet Archive](https://archive.org/) | Degraded scans and archival noise. |
| Multimodal document benchmarks | [DocILE](https://docile.rossum.ai/), [DocLayNet](https://github.com/DS4SD/DocLayNet), [OmniDocBench](https://github.com/opendatalab/OmniDocBench) | Modern document AI evaluations. |
| Synthetic document generation | [SynthDoG](https://github.com/clovaai/syndog), [DeepSolo synthetic docs](https://github.com/ViTAE-Transformer/DeepSolo), [PaddleOCR synthetic data](https://github.com/PaddlePaddle/PaddleOCR) | Fast variation generation at scale. |

## Best public web sources to download from

- [SEC EDGAR](https://www.sec.gov/edgar/search-and-access): 10-K, 10-Q, prospectuses, exhibits.
- [Companies House](https://find-and-update.company-information.service.gov.uk/): annual accounts, incorporation docs.
- [EDINET](https://disclosure2dl.edinet-fsa.go.jp/): Japanese financial filings.
- [GovInfo](https://www.govinfo.gov/): US government PDFs, reports, hearings.
- [eCFR](https://www.ecfr.gov/) and [Federal Register](https://www.federalregister.gov/): regulatory docs.
- [EU Publications Office](https://op.europa.eu/en/web/general-publications/publications): official EU docs.
- [Wikimedia Commons](https://commons.wikimedia.org/): photos/scans of forms, handwritten artifacts, IDs, signs, historical docs.
- [Internet Archive](https://archive.org/): books, scans, manuals, historical docs.
- [HathiTrust](https://www.hathitrust.org/): scanned books and archival docs.
- [arXiv](https://arxiv.org/): engineering/scientific PDFs.
- [PubMed Central](https://pmc.ncbi.nlm.nih.gov/): biomedical PDFs and figures.
- [NASA Technical Reports Server](https://ntrs.nasa.gov/): engineering-heavy reports.

## Domain-focused source lists

### Engineering documents

- [arXiv](https://arxiv.org/)
- [PubMed Central](https://pmc.ncbi.nlm.nih.gov/)
- [SEC filings](https://www.sec.gov/edgar/search-and-access)
- [GovInfo](https://www.govinfo.gov/)
- [Internet Archive manuals](https://archive.org/details/manuals)
- [NASA Technical Reports Server](https://ntrs.nasa.gov/)

### Financial documents

- [SEC EDGAR](https://www.sec.gov/edgar/search-and-access)
- [Companies House](https://find-and-update.company-information.service.gov.uk/)
- [EDINET](https://disclosure2dl.edinet-fsa.go.jp/)
- [XBRL repositories](https://www.xbrl.org/)
- [SROIE](https://rrc.cvc.uab.es/?ch=13)
- [FinTabNet](https://github.com/console-operator/FinTabNet)
- [PubTables-1M](https://github.com/microsoft/table-transformer)

### Handwritten documents

- [IAM Handwriting Database](https://fki.tic.heia-fr.ch/databases/iam-handwriting-database)
- [RIMES](https://www.a2ialab.com/doku.php?id=rimes_database)
- [Bentham](https://www.cvc.uab.es/?s=publications&id=1809)
- [IAM-OnDB](https://www.fki.inf.unibe.ch/databases/iam-on-line-handwriting-database)
- [George Washington dataset](https://crowdai.org/challenges/handwritten-document-transcription)

### Layout, table, and forms

- [PubLayNet](https://github.com/ibm-aur-nlp/PubLayNet)
- [DocLayNet](https://github.com/DS4SD/DocLayNet)
- [FUNSD](https://guillaumejaume.github.io/FUNSD/)
- [XFUND](https://github.com/doc-analysis/XFUND)
- [CORD](https://github.com/clovaai/cord)
- [PubTables-1M](https://github.com/microsoft/table-transformer)

### Synthetic data

- [PaddleOCR synthetic data](https://github.com/PaddlePaddle/PaddleOCR)
- [SynthDoG](https://github.com/clovaai/syndog)
- [DeepSolo](https://github.com/ViTAE-Transformer/DeepSolo)
- [Donut synthetic data recipes](https://github.com/clovaai/donut)
- [Faker](https://faker.readthedocs.io/) for realistic field content before rendering to PDF/image

## Recommended corpus mix

- 20% clean PDFs
- 20% real financial filings
- 20% engineering/technical PDFs
- 20% forms/invoices/receipts
- 20% handwritten or degraded scans

## Agentic extraction stressors

Include these in the corpus:

- Multi-page docs
- Tables spanning pages
- Handwritten annotations
- Low-resolution scans
- Skewed/cropped pages
- Stamps, signatures, and seals
- Mixed text, charts, and figures
- Conflicting or missing fields
- Non-English samples

## Repo execution notes

- Prefer sources with explicit licensing and documented reuse terms.
- Keep each sample's source URL and license note in [README.md](README.md).
- When collecting from rate-limited hosts (for example Wikimedia), use paced downloads and verify each file by size/type before cataloging.

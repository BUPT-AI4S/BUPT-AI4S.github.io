# AI4S 2026 metadata cleaning report

Run date: 2026-10-15
Source: `metadata/metadata/2026/ai4s.json` (1,420 keyword-selected candidates)
Imported output: `data/imported/ai4s-2026.json`
Reproduce with `python tools/clean_ai4s_metadata.py --input metadata/metadata/2026/ai4s.json --output data/imported/ai4s-2026.json --report docs/ai4s-cleaning-report-2026-10-15.json --as-of 2026-10-15`.

## Results

- 1,386 candidates had explicit scientific-domain or science-research evidence; 15 same-title ICLR main/oral-index copies were merged into 1,371 imported records.
- 34 weak candidates were excluded from the site import and listed with their raw IDs, selection hits, and exclusion reasons in the JSON report. Examples include generic image dehazing/fusion and atmospheric-turbulence restoration papers where weather or physics appeared as background context.
- The repeated raw ID `d9d4f495e875a2e075a1a4a6e1b9770f` maps to “Mollifier Layers: Enabling Efficient High-Order Derivatives in Inverse PDE Learning” and “Training Dynamics of Learning 3D-Rotational Equivariance.” Both have independent scientific evidence and both are retained.
- Missing fields among imported records: 152 abstracts, 1 author list, and 59 source dates.
- Source date precision among imported records: 151 year-only, 59 month-only, 1,102 day-level, and 59 missing. Of the day-level dates, 306 are future as of the run date. Only 84 past full dates from the AAAI OJS publication source populate `published`; conference/session dates remain in `dateRaw` and `sourceDate`.
- PDF URLs: 1,180 match a direct-PDF URL pattern and are marked `candidate` (not remotely verified), 93 supplied URLs are unresolved, and 98 records have no PDF URL. No code URLs were supplied; all imported records have `codeAvailability: "unknown"`.
- Classification status: 1,288 have a rule-derived domain classification; 83 retain explicit scientific scope but need taxonomy review.

The complete count tables, duplicate examples, and all 34 excluded candidates are in [ai4s-cleaning-report-2026-10-15.json](ai4s-cleaning-report-2026-10-15.json).

Discipline assignments can overlap, so counts do not sum to the imported record count:

| Discipline | Records |
| --- | ---: |
| Life sciences | 692 |
| Matter sciences | 639 |
| Mathematical sciences | 354 |
| Earth and space sciences | 213 |
| Information sciences | 5 |
| Social sciences | 1 |
| Scientific data | 62 |
| Scientific knowledge models | 124 |
| Scientific foundation models | 115 |
| Scientific agents | 6 |
| Scientific evaluation | 6 |
| Autonomous laboratories | 0 |

## Decisions and limits

- IDs use `import-2026-<venue>-<normalized-title-sha256-prefix>`. Raw IDs and sanitized source URLs remain in provenance. Duplicates merge only within the same venue, combining unique authors and metadata and keeping the richer abstract.
- Classification uses title, abstract, and primary area, with contextual boundaries for terms such as `cell`, `PDE`, genes, transcripts, antibodies, materials, and scientific agents. Computer vision, general computer science, topology, economics, and generic dataset use do not independently establish AI4S scope. Information-science matches are limited to explicit topics such as 6G, chip/circuit design, EDA, wireless communication, and cybersecurity.
- A visual task is retained when it has a clear scientific target such as cell images, molecular/protein analysis, microstructure, remote sensing, or astronomy. Generic dehazing, super-resolution, or image fusion with only atmospheric or physics-prior context is excluded.
- Only controlled discipline and tag IDs are emitted. All rule-based assignments carry evidence in `metadataProvenance`; weak taxonomy choices use `classificationStatus: "needs-review"`. The source remains a keyword-selected bibliography, so included records and the exclusion list remain reviewable.
- Partial dates and conference/session dates are preserved without being promoted to publication dates. Full past dates from `ojs.aaai.org` retain `dateType: "public"`; future dates are not used as `published`.
- Direct-PDF URL patterns are candidates rather than verified downloads. The cleaner creates no translations, notes, author identities, code links, or arXiv verification.

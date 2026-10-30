# Update colleague-supplied AI4S metadata

Use ai4s2025.json and ai4s2026.json as metadata updates without keyword filtering. Keep the existing 12 disciplines, map supplied ai4s_tags to them, preserve unmapped source categories in provenance, and exclude explicit non-AI4S records. Do not generate notes or translations.

1. Add a tested import adapter in tools/import_ai4s_metadata.py. Reuse existing URL/date conversion, preserve existing IDs and notes, update matched metadata, prefer formal publication metadata over preprints, and report duplicates/exclusions/unmatched old records. Match strong identifiers or normalized title with compatible authors across years.
2. Update data/imported/ai4s-2025.json and ai4s-2026.json. Keep old records absent from the new snapshot. Update matching authored front matter only for supplied classification/publication metadata while preserving its body and ID.
3. Record an auditable import summary under docs/. Validate source coverage, classification mapping, ID uniqueness and authored-content preservation; run focused import/builder tests and build the site.
4. Review, commit only relevant files, push to GitHub Pages and verify the deployed catalog.

import importlib.util
from pathlib import Path
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "tools" / "clean_ai4s_metadata.py"
SPEC = importlib.util.spec_from_file_location("clean_ai4s_metadata", SCRIPT)
cleaner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cleaner)


def record(**overrides):
    base = {
        "id": "raw-id",
        "venue": "icml",
        "year": 2026,
        "title": "Learning a climate model",
        "authors": ["Doe, Jane"],
        "abstract": "We forecast climate patterns from atmospheric observations.",
        "keywords": [],
        "primary_area": "Applications->Climate",
        "url": "https://example.org/paper/1",
        "pdf_url": None,
        "code_url": None,
        "project_url": None,
        "published": None,
        "ai4s_hits": [r"\bclimate\b"],
    }
    return {**base, **overrides}


class CleanAi4sMetadataTests(unittest.TestCase):
    def test_unrelated_records_sharing_raw_id_are_both_kept_with_safe_ids(self):
        papers = cleaner.clean_records([
            record(title="Learning a climate model"),
            record(title="Protein design with diffusion", abstract="We design proteins using diffusion models.", primary_area="Applications->Health / Medicine"),
        ])

        self.assertEqual(len(papers), 2)
        self.assertEqual(len({paper["id"] for paper in papers}), 2)
        self.assertTrue(all(paper["id"].startswith("import-2026-icml-") for paper in papers))
        self.assertTrue(all(paper["metadataProvenance"]["originalIds"] == ["raw-id"] for paper in papers))


    def test_duplicate_title_merges_richer_fields_and_unique_authors(self):
        papers = cleaner.clean_records([
            record(abstract="Short abstract."),
            record(id="raw-id-2", title="  LEARNING A CLIMATE MODEL ", authors=["Doe, Jane", "Roe, Alex"], abstract="A substantially richer abstract describing climate prediction using satellite data."),
        ])

        self.assertEqual(len(papers), 1)
        self.assertEqual(papers[0]["authors"], ["Doe, Jane", "Roe, Alex"])
        self.assertIn("substantially richer", papers[0]["abstract"])
        self.assertEqual(set(papers[0]["metadataProvenance"]["originalIds"]), {"raw-id", "raw-id-2"})

    def test_same_title_at_different_venues_remains_separate(self):
        papers = cleaner.clean_records([
            record(title="A cross-venue scientific result", venue="icml"),
            record(id="other", title="A cross-venue scientific result", venue="neurips"),
        ])

        self.assertEqual(len(papers), 2)
        self.assertEqual({paper["venue"] for paper in papers}, {"ICML", "NEURIPS"})
        self.assertEqual(len({paper["id"] for paper in papers}), 2)


    def test_doi_link_is_paper_url_and_not_a_guessed_pdf(self):
        paper = cleaner.clean_records([record(url="https://doi.org/10.1234/example", pdf_url="https://doi.org/10.1234/example")])[0]

        self.assertEqual(paper["paperUrl"], "https://doi.org/10.1234/example")
        self.assertEqual(paper["pdfUrl"], "")
        self.assertEqual(paper["pdfAvailability"], "unresolved")

    def test_direct_pdf_pattern_is_candidate_not_verified_availability(self):
        paper = cleaner.clean_records([record(pdf_url="https://example.org/paper.pdf")])[0]

        self.assertEqual(paper["pdfUrl"], "https://example.org/paper.pdf")
        self.assertEqual(paper["pdfAvailability"], "candidate")

    def test_merge_recomputes_pdf_code_and_classification_status(self):
        papers = cleaner.clean_records([
            record(abstract="Short climate forecast."),
            record(id="richer", abstract="A richer abstract about climate forecasting.", pdf_url="https://example.org/paper.pdf", code_url="https://github.com/example/project"),
        ])

        self.assertEqual(len(papers), 1)
        self.assertEqual(papers[0]["pdfAvailability"], "candidate")
        self.assertEqual(papers[0]["codeAvailability"], "available")
        self.assertEqual(papers[0]["classificationStatus"], "rule-derived")


    def test_partial_and_future_dates_keep_raw_value_without_published_date(self):
        papers = cleaner.clean_records([
            record(published="2026", title="A climate paper"),
            record(id="future", title="Another climate paper", published="2026-12-08"),
            record(id="month", title="Monthly climate paper", published="2026/7"),
        ], as_of=cleaner.date(2026, 10, 15))

        by_title = {paper["title"]: paper for paper in papers}
        self.assertEqual(by_title["A climate paper"]["published"], "")
        self.assertEqual(by_title["A climate paper"]["datePrecision"], "year")
        self.assertEqual(by_title["A climate paper"]["dateRaw"], "2026")
        self.assertEqual(by_title["Another climate paper"]["published"], "")
        self.assertEqual(by_title["Another climate paper"]["datePrecision"], "day")
        self.assertEqual(by_title["Another climate paper"]["dateRaw"], "2026-12-08")
        self.assertEqual(by_title["Monthly climate paper"]["datePrecision"], "month")
        self.assertEqual(by_title["Monthly climate paper"]["dateRaw"], "2026/7")

    def test_conference_date_is_provenance_not_publication_date(self):
        paper = cleaner.clean_records([record(published="2026-07-07", source="icml.cc")], as_of=cleaner.date(2026, 10, 15))[0]

        self.assertEqual(paper["published"], "")
        self.assertNotIn("dateType", paper)
        self.assertEqual(paper["sourceDate"], "2026-07-07")

    def test_ojs_full_date_has_publication_semantics(self):
        paper = cleaner.clean_records([record(published="2026-03-14", source="ojs.aaai.org")], as_of=cleaner.date(2026, 10, 15))[0]

        self.assertEqual(paper["published"], "2026-03-14")
        self.assertEqual(paper["dateType"], "public")


    def test_taxonomy_uses_context_and_avoids_medical_substring_false_positives(self):
        phone = record(title="Cellphone network optimization", abstract="A new method for mobile communication networks.", primary_area=None)
        cell = record(id="2", title="Cell lineage prediction", abstract="We study cell differentiation and gene expression in biological samples.", primary_area=None)
        papers = cleaner.clean_records([cell])

        by_title = {paper["title"]: paper for paper in papers}
        self.assertIn("life-sciences", by_title["Cell lineage prediction"]["disciplines"])
        self.assertNotIn("life-sciences", cleaner.classify(phone)[0])
        self.assertFalse(cleaner.candidate_decision(phone)[0])

    def test_generic_dataset_use_is_not_scientific_data_and_creation_is(self):
        generic = record(title="Model evaluation on public datasets", abstract="We evaluate a method on three public datasets.", primary_area=None)
        scientific = record(id="2", title="A new climate benchmark dataset", abstract="We introduce a curated dataset for climate forecasting.", primary_area=None)

        self.assertNotIn("scientific-data", cleaner.classify(generic)[0])
        self.assertFalse(cleaner.candidate_decision(generic)[0])
        self.assertIn("scientific-data", cleaner.classify(scientific)[0])
        self.assertTrue(cleaner.candidate_decision(scientific)[0])

    def test_generic_cv_economics_topology_and_llm_candidates_are_excluded(self):
        records = [
            record(title="A new computer vision architecture", abstract="We improve image classification.", primary_area=None),
            record(id="2", title="Economic forecasting with language models", abstract="We forecast economic indicators.", primary_area=None),
            record(id="3", title="Topology-aware graph learning", abstract="A new graph learning method.", primary_area=None),
            record(id="4", title="A general large language model", abstract="We train a general language model.", primary_area=None),
        ]

        papers, excluded = cleaner.clean_candidates(records)

        self.assertEqual(papers, [])
        self.assertEqual(len(excluded), 4)

    def test_plural_protein_and_pde_terms_map_to_science_domains(self):
        papers = cleaner.clean_records([
            record(title="Predicting protein structures", abstract="We predict protein structures at scale.", primary_area=None),
            record(id="2", title="Surrogate solvers for PDEs", abstract="A neural operator solves fluid PDEs.", primary_area=None),
        ])
        by_title = {paper["title"]: paper for paper in papers}

        self.assertIn("life-sciences", by_title["Predicting protein structures"]["disciplines"])
        self.assertIn("mathematical-sciences", by_title["Surrogate solvers for PDEs"]["disciplines"])

    def test_gene_transcriptomics_antibody_and_therapeutic_cues_are_life_sciences(self):
        papers = cleaner.clean_records([
            record(title="Auxiliary Gene Learning", abstract="We estimate gene expression in spatial transcriptomics.", primary_area=None),
            record(id="2", title="Antibody design for therapeutic targets", abstract="A biomedical model generates antibodies.", primary_area=None),
        ])

        self.assertEqual(len(papers), 2)
        self.assertTrue(all("life-sciences" in paper["disciplines"] for paper in papers))

    def test_image_restoration_with_atmospheric_or_physics_prior_is_not_ai4s(self):
        records = [
            record(title="DehazeGS: Seeing Through Fog with 3D Gaussian Splatting", abstract="A physics-driven image restoration method models atmospheric scattering.", primary_area=None),
            record(id="2", title="MdaIF multi-degradation image fusion", abstract="Image fusion handles haze, rain, snow and atmospheric transmission.", primary_area=None),
            record(id="3", title="HATIR infrared video super-resolution", abstract="Heat-aware image restoration handles atmospheric turbulence.", primary_area=None),
        ]

        papers, excluded = cleaner.clean_candidates(records)

        self.assertEqual(papers, [])
        self.assertEqual(len(excluded), 3)

    def test_visual_tasks_with_explicit_biology_materials_or_astronomy_targets_are_kept(self):
        records = [
            record(title="MorphGen: Controllable Cell-Image Generation", abstract="Biological representation alignment for cell images.", primary_area=None),
            record(id="2", title="CARE: Molecular-Guided Foundation Model for Whole Slide Image Analysis", abstract="A molecular model for protein and RNA analysis.", primary_area=None),
            record(id="3", title="MicroEvoEval: Image-Based Microstructure Evolution Prediction", abstract="We predict material microstructure evolution.", primary_area=None),
            record(id="4", title="FluxFlow: Astronomical Image Super-Resolution", abstract="We restore astronomical observations.", primary_area=None),
        ]

        papers = cleaner.clean_records(records)

        self.assertEqual(len(papers), 4)
        self.assertTrue(all(paper["disciplines"] for paper in papers))

    def test_information_science_and_autonomous_lab_signals_are_included(self):
        records = [
            record(title="6G wireless circuit design", abstract="A new 6G circuit design method.", primary_area=None),
            record(id="2", title="An autonomous laboratory for materials discovery", abstract="A robotic laboratory conducts experiments.", primary_area=None),
        ]
        papers = cleaner.clean_records(records)
        by_title = {paper["title"]: paper for paper in papers}

        self.assertIn("information-sciences", by_title["6G wireless circuit design"]["disciplines"])
        self.assertIn("autonomous-labs", by_title["An autonomous laboratory for materials discovery"]["disciplines"])

    def test_explicit_mathematical_research_targets_are_classified(self):
        for title in ("Formal mathematics with proof assistants", "Theorem proving for mathematical problem solving"):
            with self.subTest(title=title):
                self.assertIn("mathematical-sciences", cleaner.classify(record(title=title, abstract="A formal proof method.", primary_area=None))[0])


if __name__ == "__main__":
    unittest.main()

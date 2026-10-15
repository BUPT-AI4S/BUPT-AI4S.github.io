#!/usr/bin/env python3
"""Normalize the curated 2026 AI4S candidate metadata for the site catalog."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import os
import sys
import unicodedata
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit


SOURCE = "metadata/metadata/2026/ai4s.json"
DISCIPLINES = {
    "scientific-data", "scientific-knowledge-models", "scientific-foundation-models",
    "scientific-agents", "scientific-evaluation", "autonomous-labs",
    "mathematical-sciences", "life-sciences", "matter-sciences",
    "earth-space-sciences", "information-sciences", "social-sciences",
}
TAGS = {"agents", "reasoning", "foundation-models", "pretraining", "climate", "graph-neural-networks"}
DOMAIN_DISCIPLINES = {"mathematical-sciences", "life-sciences", "matter-sciences", "earth-space-sciences", "information-sciences", "social-sciences"}


def clean_text(value):
    if value is None:
        return ""
    if not isinstance(value, str):
        value = str(value)
    value = unicodedata.normalize("NFKC", value)
    value = "".join(ch for ch in value if ch in "\t\n\r" or unicodedata.category(ch) != "Cc")
    return re.sub(r"\s+", " ", value).strip()


def unique_texts(values):
    result, seen = [], set()
    for value in values if isinstance(values, list) else []:
        value = clean_text(value)
        key = value.casefold()
        if value and key not in seen:
            seen.add(key)
            result.append(value)
    return result


def normalized_title(title):
    normalized = unicodedata.normalize("NFKC", clean_text(title)).casefold()
    chars = [ch if unicodedata.category(ch)[0] in ("L", "N") else " " for ch in normalized]
    return re.sub(r"\s+", " ", "".join(chars)).strip()


def safe_https(value):
    value = clean_text(value)
    if not value or any(ch.isspace() for ch in value):
        return ""
    try:
        parts = urlsplit(value)
        if parts.scheme.lower() != "https" or not parts.hostname or parts.username or parts.password:
            return ""
        return urlunsplit(("https", parts.netloc, parts.path, parts.query, parts.fragment))
    except ValueError:
        return ""


def paper_link(record):
    link = safe_https(record.get("url"))
    if link:
        return link
    doi = clean_text(record.get("doi"))
    if doi:
        doi = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", doi, flags=re.I).strip()
        if doi and not any(c.isspace() for c in doi):
            return safe_https("https://doi.org/" + doi)
    return ""


def direct_pdf(value):
    link = safe_https(value)
    if not link:
        return ""
    parsed = urlsplit(link)
    path = parsed.path.casefold().rstrip("/")
    if path.endswith(".pdf") or re.search(r"(?:^|/)pdf(?:/|$)", path):
        return link
    return ""


def source_date(value, as_of=None, source=""):
    raw = clean_text(value)
    if re.fullmatch(r"\d{4}", raw):
        return raw, "year", "", False
    month_value = re.fullmatch(r"(\d{4})-(\d{2})", raw) or re.fullmatch(r"(\d{4})/(\d{1,2})", raw)
    if month_value:
        try:
            datetime.strptime(f"{month_value.group(1)}-{int(month_value.group(2)):02d}", "%Y-%m")
            return raw, "month", "", False
        except ValueError:
            return raw, "unknown", "invalid-date", False
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw):
        try:
            parsed = date.fromisoformat(raw)
        except ValueError:
            return raw, "unknown", "invalid-date", False
        if parsed > (as_of or date.today()):
            return raw, "day", "future-date", False
        # OJS supplies a publication date; conference sites supply session dates.
        is_publication = bool(re.search(r"(?:^|\.)ojs\.[a-z0-9.-]+$", clean_text(source).casefold()))
        return raw, "day", "", is_publication
    return raw, ("unknown" if raw else "missing"), ("invalid-date" if raw else "missing-date"), False


def classify(record):
    title = clean_text(record.get("title"))
    abstract = clean_text(record.get("abstract"))
    area = clean_text(record.get("primary_area"))
    text = f"{title} {abstract} {area}".casefold()
    area_text = area.casefold()
    hits, evidence, tags = [], {}, []

    def add(discipline, patterns, *, areas=()):
        found = [p for p in patterns if re.search(p, text, flags=re.I)]
        area_found = [p for p in areas if p in area_text]
        if found or area_found:
            hits.append(discipline)
            evidence[discipline] = (found + [f"area:{p}" for p in area_found])[:6]

    add("life-sciences", [r"\bbiology\b", r"\bbiological\b", r"\bgenom\w*\b", r"\bgenes?\b", r"\btranscriptom\w*\b", r"\bproteins?\b", r"\bpeptides?\b", r"\bantibod\w*\b", r"\bbiomed\w*\b", r"\btherapeutic\w*\b", r"\bdna\b", r"\brna\b", r"\bcells?\b", r"\btissues?\b", r"\borganism\w*\b", r"\bdrug discovery\b", r"\bdrug design\b", r"\bbinding affinity\b", r"\bphotoplethysmograph\w*\b", r"\bcryo[- ]?(?:electron|em)\b", r"\bclinical\b"], areas=("health", "medicine", "genetics", "cell biology", "drug discovery"))
    add("matter-sciences", [r"\bchemistr\w*\b", r"\bchemicals?\b", r"\bmaterial\w*\b", r"\bmicrostructure\w*\b", r"\bmolecules?\b", r"\bmolecular\b", r"\bquantum\b", r"\bcatalyst\w*\b", r"\bforce field\b", r"\bcrystal structure\b", r"\bretrosynthesis\b", r"\bmany-body\b", r"\bhamiltonian\b", r"\bsolid state\b", r"\bcondensed matter\b", r"\bspectroscop\w*\b"], areas=("chemistry", "materials"))
    add("earth-space-sciences", [r"\bclimate\b", r"\bweather (?:forecast\w*|predict\w*)\b", r"\bmeteorolog\w*\b", r"\batmospheric science\b", r"\bair quality\b", r"\bair pollution\b", r"\bremote sensing\b", r"\bgeospatial\b", r"\bsatellite imagery\b", r"\bsatellite constellation\b", r"\bocean\w*\b", r"\bearth science\b", r"\bgeoscien\w*\b", r"\bastronom\w*\b", r"\bspace science\b"], areas=("earth sciences", "climate"))
    add("social-sciences", [r"\bsocial sciences?\b", r"\bsociolog\w*\b", r"\bpolitical science\b", r"\bpublic policy\b", r"\bhuman behavior\b"])
    add("mathematical-sciences", [r"\bpartial differential equations?\b", r"\bpdes?\b", r"\bpinns?\b", r"\bphysics-informed(?: neural networks?)?\b", r"\bphysics-constrained\b", r"\bphysics-based (?:model|simulation|learning)\b", r"\bneural operators?\b", r"\bquantum\b", r"\bfluid dynamics?\b", r"\bradiative transfer\b", r"\bscientific computing\b", r"\bmathematical sciences\b", r"\bformal mathematics\b", r"\btheorem proving\b", r"\bmathematical problem solving\b", r"\bneural differential equations?\b", r"\bdifferential equation solver\b", r"\brunge-kutta\b"], areas=("mathematics", "statistics"))
    add("information-sciences", [r"\bchip design\b", r"\b(?:electronic )?design automation\b", r"\beda\b", r"\bcircuit design\b", r"\bwireless communication\b", r"\b6g\b", r"\b5g\b", r"\btelecommunications?\b", r"\bcybersecurity\b", r"\binformation theory\b", r"\bsignal processing\b", r"\bcommunication systems?\b", r"\bnetwork protocols?\b", r"\binformation processing\b"])

    def meta(discipline, patterns, tag=None):
        found = [p for p in patterns if re.search(p, text, flags=re.I)]
        if found:
            hits.append(discipline)
            evidence[discipline] = found[:6]
            if tag and tag in TAGS:
                tags.append(tag)

    meta("scientific-data", [r"\bscientific data\b", r"\bdata curation\b", r"\bdata storage\b", r"\bdata assimilation\b", r"\b(?:introduc\w*|present\w*|releas\w*|creat\w*|construct\w*|curat\w*|assembl\w*|collect\w*|annotat\w*)\b(?:\W+\w+){0,4}\W+datasets?\b", r"\bnew datasets?\b", r"\bdatasets?\b(?:\W+\w+){0,3}\W+for (?:scientific|science|research)"])
    meta("scientific-knowledge-models", [r"\bscientific (?:knowledge|discovery|theor\w*|laws?)\b", r"\bknowledge graph\b", r"\bontology\b", r"\bknowledge representation\b"])
    meta("scientific-foundation-models", [r"\bfoundation model\w*\b", r"\bpretrained (?:scientific|science|weather|protein|molecular)\b", r"\bpre-training (?:on|for) (?:scientific|science|molecular|protein)\b"], "foundation-models")
    meta("scientific-agents", [r"\bscientific agent\w*\b", r"\btool-using scientific agent\w*\b", r"\b(?:research|discovery) agent\w* for scientific (?:research|discovery)\b", r"\bagents? for (?:science|scientific discovery)\b"], "agents")
    meta("scientific-evaluation", [r"\bscientific benchmark\w*\b", r"\bevaluation of (?:scientific|science|research|discovery)\b", r"\bbenchmark\w* for (?:science|scientific|biology|chemistry|weather|climate)\b"])
    meta("autonomous-labs", [r"\bautonomous laborator\w*\b", r"\bself-driving laborator\w*\b", r"\brobotic laborator\w*\b"])
    meta("scientific-agents", [r"\bmulti-agent (?:scientific|science|research|discovery)\b"], "agents")
    for pattern, tag in [
        (r"\breasoning\b", "reasoning"), (r"\bpretraining\b|\bpre-training\b", "pretraining"),
        (r"\bgraph neural network\w*\b|\bgnn\b", "graph-neural-networks"), (r"\bclimate\b", "climate"),
    ]:
        if tag in TAGS and re.search(pattern, text, re.I):
            tags.append(tag)
    hits = list(dict.fromkeys(h for h in hits if h in DISCIPLINES))
    tags = list(dict.fromkeys(tags))
    return hits, tags, evidence


def candidate_decision(raw):
    """Return whether the keyword candidate has concrete scientific evidence."""
    disciplines, _, _ = classify(raw)
    domains = [discipline for discipline in disciplines if discipline in DOMAIN_DISCIPLINES]
    text = " ".join(clean_text(raw.get(field)) for field in ("title", "abstract", "primary_area")).casefold()
    if "autonomous-labs" in disciplines:
        return True, "explicit-autonomous-laboratory"
    visual_recovery = bool(re.search(r"\b(?:image|video)\b|\bdehaz\w*\b|\bsuper[ -]?resolution\b|\bimage fusion\b|\bweather synthesis\b", clean_text(raw.get("title")).casefold()))
    non_math_domains = domains and any(domain != "mathematical-sciences" for domain in domains)
    math_target = bool(re.search(r"\b(?:pdes?|partial differential equations?|pinns?|neural operators?|fluid dynamics?|radiative transfer|scientific computing|formal mathematics|theorem proving|mathematical problem solving|neural differential equations?|differential equation solver|runge-kutta)\b", text))
    if visual_recovery and not (non_math_domains or math_target):
        return False, "generic-visual-restoration-task-without-scientific-target"
    if domains:
        return True, "explicit-domain:" + ",".join(domains)
    scientific_context = bool(re.search(r"\bscientific\b|\bscience (?:research|discovery|data|benchmark|agent|model)\b|\bfor science\b", text))
    metadata_work = {"scientific-data", "scientific-knowledge-models", "scientific-foundation-models", "scientific-agents", "scientific-evaluation", "autonomous-labs"}
    matched_work = metadata_work.intersection(disciplines)
    if scientific_context and matched_work:
        return True, "explicit-science-contribution:" + ",".join(sorted(matched_work))
    if re.search(r"\bai4science\b|\bai for science\b|\bscientific machine learning\b", text):
        return True, "explicit-ai-for-science"
    return False, "no-explicit-scientific-domain-or-science-contribution"


def _pick_richer(old, new):
    old_text = clean_text(old)
    new_text = clean_text(new)
    return new_text if len(new_text) > len(old_text) else old_text


def _normalized_record(raw, as_of=None):
    title = clean_text(raw.get("title"))
    venue = clean_text(raw.get("venue")).upper()
    year = clean_text(raw.get("year")) or clean_text(raw.get("published"))[:4]
    authors = unique_texts(raw.get("authors"))
    abstract = clean_text(raw.get("abstract"))
    paper_url = paper_link(raw)
    raw_pdf = safe_https(raw.get("pdf_url"))
    pdf_url = direct_pdf(raw.get("pdf_url"))
    raw_code = safe_https(raw.get("code_url"))
    project_url = safe_https(raw.get("project_url"))
    raw_date, precision, date_flag, semantic_publication_date = source_date(raw.get("published"), as_of, raw.get("source"))
    disciplines, tags, evidence = classify(raw)
    normalized = normalized_title(title)
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:12]
    venue_slug = re.sub(r"[^a-z0-9]+", "-", venue.casefold()).strip("-") or "unknown"
    source_urls = list(dict.fromkeys(url for url in [safe_https(raw.get("url")), safe_https(raw.get("pdf_url")), safe_https(raw.get("project_url")), safe_https(raw.get("code_url"))] if url))
    flags = []
    if not title:
        flags.append("missing-title")
    if not authors:
        flags.append("missing-authors")
    if not abstract:
        flags.append("missing-abstract")
    if not paper_url:
        flags.append("missing-paper-url")
    if date_flag:
        flags.append(date_flag)
    if raw.get("pdf_url") and not pdf_url:
        flags.append("unresolved-pdf-url")
    if not disciplines or any(d.startswith(("scientific-", "autonomous-")) for d in disciplines):
        flags.append("taxonomy-rule-derived")
    else:
        flags.append("taxonomy-rule-derived")
    published = raw_date if semantic_publication_date and precision == "day" and not date_flag else ""
    item = {
        "id": f"import-2026-{venue_slug}-{digest}", "title": title, "authors": authors,
        "venue": venue, "year": year, "abstract": abstract, "paperUrl": paper_url,
        "pdfUrl": pdf_url, "codeUrl": raw_code, "projectUrl": project_url,
        "keywords": unique_texts(raw.get("keywords")), "disciplines": disciplines, "tags": tags,
        "imported": True, "hasNotes": False, "published": published,
        "dateRaw": raw_date, "datePrecision": precision, "sourceDate": raw_date,
        "pdfAvailability": "candidate" if pdf_url else ("unresolved" if raw_pdf else "unknown"),
        "codeAvailability": "available" if raw_code else "unknown",
        "classificationStatus": "rule-derived" if any(d in disciplines for d in DOMAIN_DISCIPLINES) else "needs-review",
        "recordFlags": list(dict.fromkeys(flags)),
        "metadataProvenance": {
            "source": SOURCE, "originalIds": [clean_text(raw.get("id"))] if clean_text(raw.get("id")) else [],
            "sourceUrls": source_urls, "rawPublishedValues": [raw_date] if raw_date else [],
            "selectionReason": clean_text(raw.get("ai4s_reason")),
            "selectionHits": unique_texts(raw.get("ai4s_hits")),
            "classificationMethod": "rules-v1", "classificationEvidence": evidence,
        },
        "_titleKey": normalized,
        "_rawPdfPresent": bool(raw.get("pdf_url")),
        "_rawCodePresent": bool(raw.get("code_url")),
    }
    if published:
        item["dateType"] = "public"
    return item


def _merge(group):
    group = sorted(group, key=lambda p: (p["title"].casefold(), p["abstract"], p["metadataProvenance"]["originalIds"]))
    merged = dict(group[0])
    for item in group[1:]:
        merged["title"] = _pick_richer(merged["title"], item["title"])
        merged["abstract"] = _pick_richer(merged["abstract"], item["abstract"])
        for key in ("paperUrl", "pdfUrl", "codeUrl", "projectUrl"):
            merged[key] = merged[key] or item[key]
        merged["keywords"] = unique_texts(merged["keywords"] + item["keywords"])
        merged["authors"] = unique_texts(merged["authors"] + item["authors"])
        merged["disciplines"] = list(dict.fromkeys(merged["disciplines"] + item["disciplines"]))
        merged["tags"] = list(dict.fromkeys(merged["tags"] + item["tags"]))
        merged["recordFlags"] = list(dict.fromkeys(merged["recordFlags"] + item["recordFlags"]))
        provenance = merged["metadataProvenance"]
        other = item["metadataProvenance"]
        for key in ("originalIds", "sourceUrls", "rawPublishedValues", "selectionHits"):
            provenance[key] = list(dict.fromkeys(provenance[key] + other[key]))
        reasons = unique_texts([provenance["selectionReason"], other["selectionReason"]])
        provenance["selectionReason"] = "; ".join(reasons)
        for field, values in other["classificationEvidence"].items():
            provenance["classificationEvidence"].setdefault(field, [])
            provenance["classificationEvidence"][field] = list(dict.fromkeys(provenance["classificationEvidence"][field] + values))[:6]
        merged["_rawPdfPresent"] |= item["_rawPdfPresent"]
        merged["_rawCodePresent"] |= item["_rawCodePresent"]
        if item["datePrecision"] == "day" and merged["datePrecision"] != "day":
            for key in ("dateRaw", "sourceDate", "datePrecision", "published", "dateType"):
                if key in item:
                    merged[key] = item[key]
                else:
                    merged.pop(key, None)
        elif not merged["dateRaw"] and item["dateRaw"]:
            for key in ("dateRaw", "sourceDate", "datePrecision"):
                merged[key] = item[key]
    merged["pdfAvailability"] = "candidate" if merged["pdfUrl"] else ("unresolved" if merged["_rawPdfPresent"] else "unknown")
    merged["codeAvailability"] = "available" if merged["codeUrl"] else "unknown"
    merged["classificationStatus"] = "rule-derived" if any(d in merged["disciplines"] for d in DOMAIN_DISCIPLINES) else "needs-review"
    merged["recordFlags"] = [flag for flag in merged["recordFlags"] if not (
        (flag == "missing-authors" and merged["authors"])
        or (flag == "missing-abstract" and merged["abstract"])
        or (flag == "unresolved-pdf-url" and merged["pdfUrl"])
    )]
    if len(merged["authors"]) == 0 and "missing-authors" not in merged["recordFlags"]:
        merged["recordFlags"].append("missing-authors")
    if not merged["abstract"] and "missing-abstract" not in merged["recordFlags"]:
        merged["recordFlags"].append("missing-abstract")
    for key in ("_titleKey", "_rawPdfPresent", "_rawCodePresent"):
        merged.pop(key, None)
    return merged


def clean_candidates(records, as_of=None):
    groups = defaultdict(list)
    excluded = []
    for raw in records:
        raw = raw if isinstance(raw, dict) else {}
        eligible, reason = candidate_decision(raw)
        if not eligible:
            excluded.append({
                "originalId": clean_text(raw.get("id")), "venue": clean_text(raw.get("venue")).upper(),
                "title": clean_text(raw.get("title")), "selectionReason": clean_text(raw.get("ai4s_reason")),
                "selectionHits": unique_texts(raw.get("ai4s_hits")), "exclusionReason": reason,
            })
            continue
        item = _normalized_record(raw if isinstance(raw, dict) else {}, as_of)
        key = (item["venue"].casefold(), item["_titleKey"])
        if item["_titleKey"]:
            groups[key].append(item)
        else:
            groups[(key[0], f"__empty-{len(groups)}-{len(groups[key])}")].append(item)
    return [_merge(groups[key]) for key in sorted(groups)], excluded


def clean_records(records, as_of=None):
    return clean_candidates(records, as_of)[0]


def build_report(records, papers, excluded=None):
    excluded = excluded or []
    raw_id_titles = defaultdict(set)
    for raw in records:
        raw_id = clean_text(raw.get("id"))
        if raw_id:
            raw_id_titles[raw_id].add(clean_text(raw.get("title")))
    collisions = [{"id": key, "titles": sorted(titles)} for key, titles in sorted(raw_id_titles.items()) if len(titles) > 1]
    categories = Counter(d for paper in papers for d in paper["disciplines"])
    flags = Counter(flag for paper in papers for flag in paper["recordFlags"])
    duplicate_records = defaultdict(list)
    for raw in records:
        key = (clean_text(raw.get("venue")).casefold(), normalized_title(raw.get("title")))
        duplicate_records[key].append(raw)
    main_oral = []
    duplicate_examples = []
    for (venue, title), items in sorted(duplicate_records.items()):
        if not title or len(items) < 2:
            continue
        duplicate_examples.append({"venue": venue.upper(), "title": clean_text(items[0].get("title")), "count": len(items), "rawIds": unique_texts([item.get("id") for item in items])})
        tracks = [clean_text(item.get("track")) for item in items]
        # OpenReview's oral-list copies use a separate 2026-Oral-- id namespace.
        kinds = ["oral-index" if clean_text(item.get("id")).startswith("2026-Oral--") else "main-index" for item in items]
        if "oral-index" in kinds and "main-index" in kinds:
            main_oral.append({"venue": venue.upper(), "title": clean_text(items[0].get("title")), "sourceRecordKinds": kinds, "rawIds": unique_texts([item.get("id") for item in items]), "tracks": tracks})
    return {
        "inputCount": len(records), "eligibleCount": len(records) - len(excluded), "outputCount": len(papers),
        "mergedRecords": len(records) - len(excluded) - len(papers), "excludedCount": len(excluded),
        "badPdfCandidates": flags["unresolved-pdf-url"], "missingFields": {flag: count for flag, count in sorted(flags.items()) if flag.startswith("missing-")},
        "dateFlags": {flag: count for flag, count in sorted(flags.items()) if flag.endswith("date")},
        "datePrecisionCounts": dict(sorted(Counter(p["datePrecision"] for p in papers).items())),
        "rawIdConflicts": collisions, "disciplineCounts": dict(sorted(categories.items())),
        "mainOralDuplicateExamples": main_oral[:20],
        "duplicateTitleExamples": duplicate_examples[:20],
        "classificationStatusCounts": dict(sorted(Counter(p["classificationStatus"] for p in papers).items())),
        "recordFlagCounts": dict(sorted(flags.items())),
        "excludedCandidates": excluded,
    }


def run(input_path, output_path, report_path=None, as_of=None):
    records = json.loads(Path(input_path).read_text(encoding="utf-8-sig"))
    if not isinstance(records, list):
        raise ValueError("Input must be a JSON array of paper records")
    papers, excluded = clean_candidates(records, as_of)
    output = {"schemaVersion": 1, "source": SOURCE, "papers": papers}
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temp_output = output_path.with_name(output_path.name + ".tmp")
    temp_output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temp_output, output_path)
    report = build_report(records, papers, excluded)
    if report_path:
        Path(report_path).parent.mkdir(parents=True, exist_ok=True)
        Path(report_path).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Source JSON file")
    parser.add_argument("--output", required=True, help="Normalized JSON output")
    parser.add_argument("--report", help="Optional JSON report output")
    parser.add_argument("--as-of", help="Date used to identify future dates (YYYY-MM-DD)")
    args = parser.parse_args()
    as_of = date.fromisoformat(args.as_of) if args.as_of else None
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    report = run(args.input, args.output, args.report, as_of)
    summary = {key: value for key, value in report.items() if key != "excludedCandidates"}
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

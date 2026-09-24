"""
Structured export formats for LIMS/EMR integration.
- FHIR R4 Bundle: DiagnosticReport + Observations (Epic, Cerner, modern EHRs)
- JSON (custom lab integrations)
- HL7 v2 ORU^R01 (legacy hospital systems)
"""
import json
from datetime import datetime, timezone
from hashlib import sha256


# LOINC codes for genes (partial — extend as needed)
GENE_LOINC = {
    "BRCA1": "21638-6",
    "BRCA2": "21639-4",
    "TP53": "21645-1",
    "CFTR": "21643-6",
    "MLH1": "21644-4",
    "MSH2": "21646-9",
    "APC": "21642-8",
    "VHL": "21647-7",
    "PTEN": "21640-2",
}

# ACMG classification -> SNOMED CT code
ACMG_SNOMED = {
    "Pathogenic": "10828004",
    "Likely Pathogenic": "442008006",
    "VUS": "443263003",
    "Likely Benign": "442006004",
    "Benign": "10828004",
}


def _provenance_hash(sample: dict, variant: dict) -> str:
    parts = [
        str(sample.get("id", "")),
        str(variant.get("id", "")),
        str(sample.get("reference_build", "GRCh38")),
        str(sample.get("pipeline_version", "0.1.0")),
    ]
    return sha256("|".join(parts).encode()).hexdigest()[:16]


def _is_actionable(v: dict) -> bool:
    return (v.get("acmg_classification") or "VUS").lower() in ("pathogenic", "likely pathogenic")


def to_fhir_bundle(sample: dict, variants: list[dict]) -> dict:
    """
    FHIR R4 Bundle containing:
    - One DiagnosticReport (the genomic report)
    - One Observation per clinically significant variant
    - Provenance + RUO disclaimer extensions on each
    """
    now = datetime.now(timezone.utc).isoformat()
    actionable = [v for v in variants if _is_actionable(v)]

    entries = []

    # ---------- DiagnosticReport ----------
    report_id = f"report-{sample.get('id', '')[:8]}"
    report = {
        "resourceType": "DiagnosticReport",
        "id": report_id,
        "meta": {
            "lastUpdated": now,
            "profile": ["http://hl7.org/fhir/StructureDefinition/genomics-reporting"],
        },
        "status": "final",
        "category": [{
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/v2-0074",
                "code": "GE",
                "display": "Genetics",
            }],
        }],
        "code": {
            "coding": [{
                "system": "http://loinc.org",
                "code": "81247-9",
                "display": "Master HL7 genetic variant reporting panel",
            }],
            "text": f"Genomic Variant Report — {sample.get('name')}",
        },
        "subject": {
            "reference": f"Patient/{sample.get('id')}",
            "display": sample.get("name"),
        },
        "effectiveDateTime": now,
        "issued": now,
        "conclusion": (
            f"{len(actionable)} clinically significant variant(s) identified. "
            f"Total variants analyzed: {len(variants)}. "
            "Research use only — not for clinical diagnosis."
        ),
        "result": [{"reference": f"Observation/{v.get('id')}"} for v in actionable],
        "extension": [
            {
                "url": "https://genomicsops.io/fhir/ruo-disclaimer",
                "valueString": "Research Use Only. Not for clinical diagnosis or patient management.",
            },
            {
                "url": "https://genomicsops.io/fhir/reference-build",
                "valueString": sample.get("reference_build", "GRCh38"),
            },
        ],
    }
    entries.append({"fullUrl": f"urn:uuid:{report_id}", "resource": report})

    # ---------- Observations ----------
    for v in actionable:
        prov_hash = _provenance_hash(sample, v)
        gene = v.get("gene") or "Unknown"

        obs = {
            "resourceType": "Observation",
            "id": str(v.get("id")),
            "meta": {
                "lastUpdated": now,
                "profile": ["http://hl7.org/fhir/StructureDefinition/genomics-reporting"],
            },
            "status": "final",
            "category": [{
                "coding": [{
                    "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                    "code": "laboratory",
                    "display": "Laboratory",
                }],
            }],
            "code": {
                "coding": [{
                    "system": "http://loinc.org",
                    "code": GENE_LOINC.get(gene, "81247-9"),
                    "display": f"{gene} gene variant analysis",
                }],
                "text": f"{gene} variant at {v.get('chrom')}:{v.get('pos')}",
            },
            "subject": {
                "reference": f"Patient/{sample.get('id')}",
                "display": sample.get("name"),
            },
            "effectiveDateTime": now,
            "valueCodeableConcept": {
                "coding": [{
                    "system": "http://snomed.info/sct",
                    "code": ACMG_SNOMED.get(v.get("acmg_classification"), "443263003"),
                    "display": v.get("acmg_classification"),
                }],
                "text": v.get("acmg_classification"),
            },
            "component": [{
                "code": {"coding": [{"system": "http://loinc.org", "code": "48018-6"}]},
                "valueString": f"{v.get('chrom')}:{v.get('pos')} {v.get('ref')}>{v.get('alt')}",
            }],
            "note": [{"text": v.get("acmg_summary") or v.get("evidence_summary") or ""}],
            "extension": [
                {
                    "url": "https://genomicsops.io/fhir/provenance-hash",
                    "valueString": prov_hash,
                },
                {
                    "url": "https://genomicsops.io/fhir/reference-build",
                    "valueString": sample.get("reference_build", "GRCh38"),
                },
                {
                    "url": "https://genomicsops.io/fhir/pipeline-version",
                    "valueString": sample.get("pipeline_version", "0.1.0"),
                },
            ],
        }
        entries.append({"fullUrl": f"urn:uuid:{v.get('id')}", "resource": obs})

    return {
        "resourceType": "Bundle",
        "id": str(sample.get("id")),
        "type": "collection",
        "timestamp": now,
        "total": len(entries),
        "entry": entries,
    }


def to_json_payload(sample: dict, variants: list[dict]) -> dict:
    """Clean JSON for custom lab integrations."""
    actionable = [v for v in variants if _is_actionable(v)]

    return {
        "schema_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generator": {
            "name": "GenomicsOps",
            "version": "0.1.0",
            "intended_use": "Research Use Only",
        },
        "sample": {
            "id": sample.get("id"),
            "name": sample.get("name"),
            "reference_build": sample.get("reference_build", "GRCh38"),
            "species": sample.get("species", "Homo sapiens"),
            "provenance_hash": sample.get("provenance_hash"),
        },
        "summary": {
            "total_variants": len(variants),
            "actionable_count": len(actionable),
        },
        "actionable_variants": [
            {
                "id": v.get("id"),
                "position": f"{v.get('chrom')}:{v.get('pos')}",
                "ref": v.get("ref"),
                "alt": v.get("alt"),
                "gene": v.get("gene"),
                "consequence": v.get("consequence"),
                "impact": v.get("impact"),
                "clinvar_significance": v.get("clinvar_significance"),
                "acmg": {
                    "classification": v.get("acmg_classification"),
                    "confidence": v.get("acmg_confidence"),
                    "evidence_summary": v.get("acmg_summary"),
                },
                "mane_select": v.get("mane_select"),
            }
            for v in actionable
        ],
    }


def to_hl7_oru(sample: dict, variants: list[dict], sending_facility: str = "GENOMICSOPS") -> str:
    """
    HL7 v2.5.1 ORU^R01 message.
    One OBX segment per actionable variant.
    Pipe-delimited, \\r line endings.
    """
    now = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    msg_id = f"MSG{sample.get('id', '')[:8].upper()}{now}"

    msh = f"MSH|^~\\&|{sending_facility}|{sending_facility}|EMR|EMR|{now}||ORU^R01|{msg_id}|P|2.5.1"
    pid = f"PID|1||{sample.get('id', '')}||{sample.get('name', 'Unknown')}"
    obr = f"OBR|1||{sample.get('id', '')}|GENOMIC^Genomic Variant Report^L|||{now}"

    segments = [msh, pid, obr]

    actionable = [v for v in variants if _is_actionable(v)]

    for i, v in enumerate(actionable, start=1):
        gene = (v.get("gene") or "UNKNOWN").upper()
        acmg = v.get("acmg_classification") or "VUS"
        change = f"{v.get('ref')}>{v.get('alt')}"

        obx = f"OBX|{i}|ST|GENE^Gene^L||{gene}|{change}|{acmg}|||F|||{now}"
        segments.append(obx)

    segments.append(f"FTS|1|{len(actionable)}")

    return "\r".join(segments) + "\r"


def detect_format(filename: str) -> str:
    f = filename.lower()
    if "fhir" in f:
        return "fhir"
    if "hl7" in f or "oru" in f:
        return "hl7"
    return "json"

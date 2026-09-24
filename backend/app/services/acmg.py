"""
ACMG/AMP 2015 variant classification engine.
Every classification carries engine version + evidence snapshot hash for reproducibility.

Reference: Richards et al., Genet Med 2015.
"""
import hashlib
import json
from typing import Optional
from app.config import settings


CRITERIA = {
    "PVS1": {"weight": "very_strong", "category": "pathogenic", "desc": "Null variant where LOF is a known disease mechanism"},
    "PS1":  {"weight": "strong",      "category": "pathogenic", "desc": "Same amino acid change as an established pathogenic variant"},
    "PS2":  {"weight": "strong",      "category": "pathogenic", "desc": "De novo (confirmed parentage)"},
    "PS3":  {"weight": "strong",      "category": "pathogenic", "desc": "Functional studies show damaging effect"},
    "PS4":  {"weight": "strong",      "category": "pathogenic", "desc": "Prevalence in affected individuals significantly increased"},
    "PM1":  {"weight": "moderate",    "category": "pathogenic", "desc": "Mutational hotspot / critical functional domain"},
    "PM2":  {"weight": "moderate",    "category": "pathogenic", "desc": "Absent from controls (gnomAD)"},
    "PM3":  {"weight": "moderate",    "category": "pathogenic", "desc": "For recessive: detected in trans with a pathogenic variant"},
    "PM4":  {"weight": "moderate",    "category": "pathogenic", "desc": "Protein length change (non-repeat region)"},
    "PM5":  {"weight": "moderate",    "category": "pathogenic", "desc": "Different missense at same position as known pathogenic"},
    "PM6":  {"weight": "moderate",    "category": "pathogenic", "desc": "Assumed de novo (parentage unconfirmed)"},
    "PP1":  {"weight": "supporting",  "category": "pathogenic", "desc": "Cosegregation with disease in family"},
    "PP2":  {"weight": "supporting",  "category": "pathogenic", "desc": "Missense in gene with low rate of benign missense"},
    "PP3":  {"weight": "supporting",  "category": "pathogenic", "desc": "Computational evidence supports damaging effect"},
    "PP4":  {"weight": "supporting",  "category": "pathogenic", "desc": "Phenotype highly specific for gene"},
    "BA1":  {"weight": "standalone",  "category": "benign",     "desc": "Allele frequency >5% in a population database"},
    "BS1":  {"weight": "strong",      "category": "benign",     "desc": "Allele frequency greater than expected for disease"},
    "BS2":  {"weight": "strong",      "category": "benign",     "desc": "Observed in healthy adults"},
    "BS3":  {"weight": "strong",      "category": "benign",     "desc": "Functional studies show no damaging effect"},
    "BS4":  {"weight": "strong",      "category": "benign",     "desc": "Lack of segregation in affected family members"},
    "BP1":  {"weight": "supporting",  "category": "benign",     "desc": "Missense in gene where only truncating cause disease"},
    "BP2":  {"weight": "supporting",  "category": "benign",     "desc": "In trans with pathogenic (dominant) or in cis"},
    "BP3":  {"weight": "supporting",  "category": "benign",     "desc": "In-frame indel in repetitive region"},
    "BP4":  {"weight": "supporting",  "category": "benign",     "desc": "Computational evidence supports no impact"},
    "BP5":  {"weight": "supporting",  "category": "benign",     "desc": "Found in case with alternate molecular cause"},
    "BP6":  {"weight": "supporting",  "category": "benign",     "desc": "Reported as benign by reputable source"},
    "BP7":  {"weight": "supporting",  "category": "benign",     "desc": "Synonymous with no predicted splice impact"},
}

LOF_GENES = {
    "BRCA1", "BRCA2", "TP53", "CFTR", "MLH1", "MSH2", "MSH6", "PMS2",
    "APC", "VHL", "PTEN", "RB1", "NF1", "NF2", "STK11", "PALB2", "ATM",
    "CHEK2", "CDH1", "BMPR1A", "SMAD4", "MUTYH", "MEN1", "RET",
}

NULL_CONSEQUENCES = {
    "frameshift_variant", "stop_gained", "splice_acceptor_variant",
    "splice_donor_variant", "start_lost", "transcript_ablation",
}


def auto_fire_criteria(variant: dict) -> list[dict]:
    fired = []
    consequence = (variant.get("consequence") or "").lower()
    impact = (variant.get("impact") or "").upper()
    gene = (variant.get("gene") or "").upper()
    gnomad_af = variant.get("gnomad_af")
    clinvar = (variant.get("clinvar_significance") or "").lower()

    if consequence in NULL_CONSEQUENCES and gene in LOF_GENES:
        fired.append({
            "code": "PVS1", "source": "auto",
            "evidence": f"{consequence.replace('_', ' ')} in {gene}, a gene where LOF is a known mechanism",
        })

    if gnomad_af is not None and gnomad_af < 0.0001:
        fired.append({"code": "PM2", "source": "auto",
                      "evidence": f"gnomAD AF = {gnomad_af:.2e} (absent/ultra-rare)"})

    if gnomad_af is not None and gnomad_af > 0.05:
        fired.append({"code": "BA1", "source": "auto",
                      "evidence": f"gnomAD AF = {gnomad_af:.4f} (>5%, standalone benign)"})
    elif gnomad_af is not None and gnomad_af > 0.01:
        fired.append({"code": "BS1", "source": "auto",
                      "evidence": f"gnomAD AF = {gnomad_af:.4f} (>1%, greater than expected for disease)"})

    if impact in ("HIGH", "MODERATE"):
        fired.append({"code": "PP3", "source": "auto",
                      "evidence": f"SnpEff impact: {impact}"})

    if impact in ("LOW", "MODIFIER") and consequence in ("synonymous_variant", "intron_variant"):
        fired.append({"code": "BP4", "source": "auto",
                      "evidence": f"SnpEff impact: {impact}, consequence: {consequence}"})

    if consequence == "synonymous_variant" and impact == "LOW":
        fired.append({"code": "BP7", "source": "auto",
                      "evidence": "Synonymous variant, no predicted splice impact"})

    if "pathogenic" in clinvar and "benign" not in clinvar:
        fired.append({"code": "PP4", "source": "auto",
                      "evidence": f"ClinVar record: {variant.get('clinvar_significance')}"})

    if "benign" in clinvar:
        fired.append({"code": "BP6", "source": "auto",
                      "evidence": f"ClinVar record: {variant.get('clinvar_significance')}"})

    return fired


def classify(fired_criteria: list[dict]) -> tuple[str, str]:
    codes = {c["code"] for c in fired_criteria}

    if "BA1" in codes:
        return "Benign", "high"

    pvs = sum(1 for c in codes if c.startswith("PVS"))
    ps = sum(1 for c in codes if c.startswith("PS"))
    pm = sum(1 for c in codes if c.startswith("PM"))
    pp = sum(1 for c in codes if c.startswith("PP"))
    bs = sum(1 for c in codes if c.startswith("BS"))
    bp = sum(1 for c in codes if c.startswith("BP"))

    if bs >= 2:
        return "Benign", "high"
    if bs == 1 and bp >= 1:
        return "Likely Benign", "medium"
    if bp >= 2:
        return "Likely Benign", "medium"

    if pvs >= 1 and ps >= 1:
        return "Pathogenic", "high"
    if ps >= 2:
        return "Pathogenic", "high"
    if pvs >= 1 and pm >= 2:
        return "Pathogenic", "medium"
    if pvs >= 1 and pm >= 1 and pp >= 1:
        return "Pathogenic", "medium"
    if ps >= 1 and pm >= 3:
        return "Pathogenic", "medium"
    if ps >= 1 and pm >= 2 and pp >= 2:
        return "Pathogenic", "medium"
    if ps >= 1 and pm >= 1 and pp >= 4:
        return "Pathogenic", "low"

    if pvs >= 1 and pm == 1:
        return "Likely Pathogenic", "medium"
    if ps >= 1 and pm <= 2:
        return "Likely Pathogenic", "medium"
    if ps >= 1 and pp >= 2:
        return "Likely Pathogenic", "low"
    if pm >= 3:
        return "Likely Pathogenic", "low"
    if pm >= 2 and pp >= 2:
        return "Likely Pathogenic", "low"
    if pm >= 1 and pp >= 4:
        return "Likely Pathogenic", "low"

    return "VUS", "high"


def classify_variant(variant: dict) -> dict:
    """Full pipeline: auto-fire criteria, classify, summarize. Includes engine version."""
    auto_fired = auto_fire_criteria(variant)
    classification, confidence = classify(auto_fired)

    codes = [c["code"] for c in auto_fired]
    summary = f"{classification} based on {', '.join(codes)}" if codes else f"{classification} — no criteria fired automatically"

    snapshot_input = {
        "chrom": variant.get("chrom"),
        "pos": variant.get("pos"),
        "ref": variant.get("ref"),
        "alt": variant.get("alt"),
        "gene": variant.get("gene"),
        "consequence": variant.get("consequence"),
        "impact": variant.get("impact"),
        "gnomad_af": variant.get("gnomad_af"),
        "clinvar_significance": variant.get("clinvar_significance"),
        "criteria": [c["code"] for c in auto_fired],
    }
    snapshot_hash = hashlib.sha256(
        json.dumps(snapshot_input, sort_keys=True, default=str).encode()
    ).hexdigest()[:16]

    return {
        "classification": classification,
        "confidence": confidence,
        "criteria_fired": auto_fired,
        "evidence_summary": summary,
        "auto_classification": classification,
        "engine_version": settings.ACMG_ENGINE_VERSION,
        "rule_set_version": settings.ACMG_RULE_SET_VERSION,
        "evidence_snapshot_hash": snapshot_hash,
    }


def what_would_change_it(variant: dict) -> list[str]:
    suggestions = []
    consequence = (variant.get("consequence") or "").lower()
    gene = (variant.get("gene") or "").upper()
    impact = (variant.get("impact") or "").upper()
    gnomad = variant.get("gnomad_af")

    if consequence == "missense_variant" and impact == "MODERATE":
        suggestions.append("PS3: A functional study showing damaging effect would move this toward Likely Pathogenic")
    if gnomad is None:
        suggestions.append("PM2/BA1: Population frequency data (gnomAD) is required to assess rarity")
    if gene in LOF_GENES and impact in ("HIGH", "MODERATE"):
        suggestions.append("PVS1 may apply if the variant is confirmed as a null allele via RNA/splicing assay")
    if "uncertain" in (variant.get("clinvar_significance") or "").lower():
        suggestions.append("ClinVar VUS — additional segregation or functional data would resolve it")
    suggestions.append("PS2/PM6: Confirm parental testing to assess de novo status")
    return suggestions

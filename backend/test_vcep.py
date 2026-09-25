"""Test that the VCEP-aware engine works."""
from app.services.acmg import classify_variant, get_vcep_for_gene

print()
print("=" * 60)
print("VCEP-Aware Engine Test")
print("=" * 60)
print()

# 1. Confirm VCEP rules loaded
print("Loading VCEP rules:")
for gene in ("BRCA1", "TP53", "MLH1"):
    v = get_vcep_for_gene(gene)
    if v:
        print(f"  {gene}: {v['vcep_name']} v{v['spec_version']}")
    else:
        print(f"  {gene}: NO VCEP (using generic)")
print()

# 2. Test a BRCA1 variant with gnomAD AF = 0.001
brca1 = {
    "chrom": "17", "pos": 43092919, "ref": "G", "alt": "A",
    "gene": "BRCA1",
    "consequence": "missense_variant",
    "impact": "MODERATE",
    "gnomad_af": 0.001,
    "clinvar_significance": "Pathogenic",
}
r1 = classify_variant(brca1)
print("BRCA1 variant (gnomAD AF = 0.001, ClinVar = Pathogenic):")
print(f"  classification: {r1['classification']}")
print(f"  vcep_applied:   {r1.get('vcep_applied')}")
print(f"  criteria fired: {[c['code'] for c in r1['criteria_fired']]}")
for c in r1['criteria_fired']:
    if c['code'] in ('BS1', 'BA1', 'PM2'):
        print(f"    {c['code']}: {c['evidence']}")
print()

# 3. Same variant as MLH1
mlh1 = dict(brca1)
mlh1["gene"] = "MLH1"
r2 = classify_variant(mlh1)
print("MLH1 variant (same AF, same ClinVar):")
print(f"  classification: {r2['classification']}")
print(f"  vcep_applied:   {r2.get('vcep_applied')}")
print(f"  criteria fired: {[c['code'] for c in r2['criteria_fired']]}")
for c in r2['criteria_fired']:
    if c['code'] in ('BS1', 'BA1', 'PM2'):
        print(f"    {c['code']}: {c['evidence']}")
print()

# 4. Same variant as TP53
tp53 = dict(brca1)
tp53["gene"] = "TP53"
r3 = classify_variant(tp53)
print("TP53 variant (same AF, same ClinVar):")
print(f"  classification: {r3['classification']}")
print(f"  vcep_applied:   {r3.get('vcep_applied')}")
print(f"  criteria fired: {[c['code'] for c in r3['criteria_fired']]}")
print()

# 5. Same variant as an unknown gene (no VCEP spec)
unknown = dict(brca1)
unknown["gene"] = "SOMEOTHERGENE"
r4 = classify_variant(unknown)
print("Unknown gene (no VCEP spec):")
print(f"  classification: {r4['classification']}")
print(f"  vcep_applied:   {r4.get('vcep_applied')}")
print(f"  criteria fired: {[c['code'] for c in r4['criteria_fired']]}")
print()

from app.supabase_client import supabase

def parse_and_store_vcf(sample_id: str, file_path: str, max_variants: int = 100000):
    batch = []
    count = 0
    
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            # Skip headers
            if line.startswith('#'):
                continue
            
            parts = line.strip().split('\t')
            if len(parts) < 8:
                continue
            
            chrom = parts[0]
            try:
                pos = int(parts[1])
            except ValueError:
                continue
            ref = parts[3]
            alt = parts[4]
            try:
                qual = float(parts[5]) if parts[5] != '.' else None
            except ValueError:
                qual = None
            filter_val = parts[6] if parts[6] != '.' else None
            info = parts[7] if len(parts) > 7 else ""
            
            # Extract gene / consequence from ANN field if present
            gene = consequence = impact = clinvar = None
            for field in info.split(';'):
                if field.startswith('ANN='):
                    ann_val = field[4:]
                    ann_parts = ann_val.split('|')
                    if len(ann_parts) > 3:
                        consequence = ann_parts[1] or None
                        impact = ann_parts[2] or None
                        gene = ann_parts[3] or None
                elif field.startswith('CLNSIG='):
                    clinvar = field[7:]
            
            batch.append({
                "sample_id": sample_id,
                "chrom": chrom,
                "pos": pos,
                "ref": ref,
                "alt": alt,
                "qual": qual,
                "filter": filter_val,
                "gene": gene,
                "consequence": consequence,
                "impact": impact,
                "clinvar_significance": clinvar,
            })
            
            if len(batch) >= 1000:
                supabase.table("variants").insert(batch).execute()
                batch = []
            
            count += 1
            if count >= max_variants:
                break
    
    if batch:
        supabase.table("variants").insert(batch).execute()
    
    return count

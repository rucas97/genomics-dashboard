# GenomicsOps

A research-use-only variant interpretation workbench for VCF-based genomics.

Ingests VCF files, annotates variants with gene and ClinVar data, classifies them using a transparent ACMG/AMP engine (with ClinGen VCEP specifications for select genes), and exports clinically significant findings as FHIR R4, custom JSON, or HL7 v2.

Runs in two deployment modes from a single codebase: cloud (Supabase + FastAPI + Next.js) and local (SQLite + same FastAPI + static Next.js).

## What it does

### Ingestion
- Upload VCF files (uncompressed .vcf). Compressed .vcf.gz is decompressed server-side.
- Multi-file upload supported.
- Small files (under 10 MB) parsed with a pure-Python VCF reader.
- Large files parsed with DuckDB for speed.
- Files stored in Supabase Storage (cloud) or local disk (local).

### Annotation
- Calls MyVariant.info (aggregates ClinVar, dbSNP, SnpEff) for gene, consequence, and clinical significance.
- Falls back to Ensembl VEP REST for functional consequence.
- Results cached in a variant_cache table. Re-annotation is instant.
- Annotation is optional. Offline mode still works on pre-annotated VCFs.

### ACMG classification
- Implements the 27 criteria from ACMG/AMP 2015 guidelines.
- Fires criteria automatically from variant data: consequence, gene, gnomAD frequency, ClinVar significance.
- Applies the standard combining rule matrix.
- VCEP-aware for 3 genes:
  - BRCA1: ENIGMA BRCA1/2 v1.2
  - TP53: TP53 VCEP v2.4
  - MLH1: InSiGHT Hereditary Colorectal Cancer/Polyposis v2.0
- VCEP thresholds replace generic defaults for BA1, BS1, and PM2.
- VCEP-suppressed criteria are honored.
- Engine version (1.0.0) and rule set version (ACMG-AMP-2015) stored with every classification.
- Evidence snapshot hash (SHA-256) recorded for reproducibility.
- Interactive ACMG panel: view, add, or remove criteria; watch the classification recompute; simulate what-if scenarios.

### Cohort analysis
- Group samples into cohorts.
- PCA clustering across variants (binary presence matrix, scikit-learn).
- Gene enrichment table.
- Shared variant table.
- Cohort PDF report.

### Variant explorer
- Filter by gene, gene panel, chromosome, ClinVar class, ACMG class, impact, or prioritised.
- Multi-sample selection with union or intersection modes.
- Clinical summary cards.
- Click any variant to open the ACMG workbench panel.

### Reports
- Sample reports: metadata, QC charts, classification summary, prioritized variant details with full ACMG criteria.
- Cohort reports: cohort metadata, classification breakdown, gene enrichment, samples.
- Generated via xhtml2pdf. Dark header with embedded logo.
- Stored in Supabase Storage (cloud) or ~/.genomicsops/data/ (local).
- Downloadable and deletable.

### Export
- FHIR R4: one DiagnosticReport plus one Observation per pathogenic or likely-pathogenic variant.
- Custom JSON: flat structure for any LIMS with a REST API.
- HL7 v2 ORU^R01: pipe-delimited with one OBX per actionable variant.

### Audit log
- Every action writes a row with user, action, resource, timestamp, details.
- Hash-chained: each row stores previous_hash and row_hash. Tampering breaks the chain.
- Verify Integrity button recomputes the chain and reports OK or the broken row.
- Filterable by user.
- Export as CSV.

### License system
- Three tiers: unlicensed, trial, standard, enterprise.
- Ed25519-signed JSON tokens with license_id, email, tier, expires_at, machine_fingerprint.
- Offline verification: public key embedded. No server call needed after activation.
- Machine fingerprint: SHA-256 of a persisted random UUID + hostname + OS.
- Network policy from license tier:
  - Unlicensed: all outbound blocked
  - Trial/Standard: only annotation hosts allowed
  - Enterprise: full network
- Every outbound call logged.
- Mint licenses via backend/mint_web.py (Flask tool at localhost:5555).

### Multi-tenancy (cloud mode)
- Organizations with roles: owner, admin, analyst, viewer.
- Postgres Row-Level Security scopes queries by org.
- Email invitations with expiry.

### Local mode
- SQLite at ~/.genomicsops/genomics.db.
- Local users with bcrypt-hashed passwords.
- JWT sessions in localStorage with auto-redirect on expiry.
- Files at ~/.genomicsops/data/.

### Job runner
- Long-running work runs in a separate process via a DB-polling job runner.
- API stays responsive during uploads.
- Job status in jobs table; polled via /jobs/.
- Start with: python -m app.jobs.runner.

## Architecture

Cloud mode: Next.js on Vercel + FastAPI on Render + Supabase Postgres.

Local mode: Same code, MODE=local, SQLite at ~/.genomicsops/genomics.db.

Mode is switched by changing one environment variable.

## Data model

Key tables (SQLite local; same shape in Postgres cloud):

- users: Local accounts with hashed passwords and roles
- samples: VCF uploads with metadata and status
- variants: Parsed variant records
- qc_metrics: Per-sample variant counts
- variant_acmg: Classifications with criteria, engine version, snapshot hash
- cohorts: Sample groupings
- pipeline_runs: Pipeline execution records
- reports: Generated PDFs
- audit_log: Hash-chained action log
- provenance: Tool versions and reference builds
- consent_records: GDPR consent tracking
- variant_cache: Cached annotations
- vcep_specifications: VCEP rules per gene
- vcep_criteria: Criterion overrides per spec
- jobs: Background job queue
- mane_transcripts: MANE Select references

## Setup

### Supabase (cloud)

1. Create a project at supabase.com.
2. SQL Editor: paste infrastructure/supabase/schema.sql and Run.
3. Project Settings, API: copy URL, anon key, service_role key.
4. Authentication, Providers: enable Email and Anonymous sign-ins.
5. Authentication, URL Configuration: Site URL http://localhost:3000, add http://localhost:3000/** to redirect URLs.

### Backend

    cd backend
    cp .env.example .env
    # Fill in SUPABASE_URL, SUPABASE_SERVICE_KEY, SUPABASE_ANON_KEY
    python -m venv .venv
    source .venv/Scripts/activate
    pip install -r requirements.txt
    uvicorn app.main:app --reload --port 8000

Health check: http://localhost:8000/health

### Frontend

    cd frontend
    cp .env.local.example .env.local
    # Fill in NEXT_PUBLIC_SUPABASE_URL, NEXT_PUBLIC_SUPABASE_ANON_KEY, NEXT_PUBLIC_API_URL
    npm install
    npm run dev

Open http://localhost:3000.

### Job runner (separate terminal)

    cd backend
    source .venv/Scripts/activate
    python -m app.jobs.runner

### License minting (as needed)

    cd backend
    source .venv/Scripts/activate
    python mint_web.py

Open http://localhost:5555.

## Usage

1. Sign in (local: admin@local / admin on first run).
2. Samples: Upload a VCF. Status flips processing to ready.
3. Annotate on sample detail page to pull gene and ClinVar data.
4. Variant Explorer: filter, prioritize, click a variant to open the ACMG panel.
5. Cohorts: group samples, run PCA, generate gene enrichment.
6. Reports: generate and download PDFs.
7. Audit Log: view every action, verify chain integrity.
8. License: view status, activate, copy machine fingerprint.
9. FAQ: common questions.
10. Settings: manage users (local) or organization (cloud).

## Limitations

GenomicsOps is Research Use Only. Not clinically validated. Not intended for clinical diagnosis, treatment, or patient management. Classifications follow ACMG/AMP 2015 applied automatically and must be verified by a qualified clinical scientist before any clinical use.

### Not implemented

- Gene-specific ACMG for most genes. VCEP specifications for BRCA1, TP53, MLH1 only. Others fall back to generic ACMG.
- VCEP combining logic. VCEP thresholds applied, but combining uses generic ACMG rules. Some VCEPs use points-based logic not yet implemented.
- PVS1 decision trees. VCEP-specific trees based on protein domain and NMD are not implemented.
- Trio / family analysis. No inheritance modeling or pedigree support.
- Phenotype matching. No HPO terms or gene-disease databases.
- CNV / SV detection. SNPs and small indels only.
- Literature integration. Does not pull PubMed or link functional evidence to criteria.
- Statistical gene enrichment. Counts only. No Fisher exact test or FDR correction.
- PCA projection. Binary presence matrix. No LD pruning or 1000 Genomes projection.
- Local annotation database. Annotation always calls external APIs.
- Real pipeline engine. Pipeline runner executes lightweight Python scripts, not Nextflow or Snakemake.

### Security boundary

netgate.py blocks outbound HTTP calls at the Python level. This is policy enforcement, not security enforcement. It does not prevent:
- An OS-level process from making network calls
- A malicious dependency from making network calls
- A firewall or egress policy from being needed

For true air-gapped deployments, use container egress policy or an OS firewall in addition.

### Scalability

- Long-running tasks run in a separate process via a DB-polling job runner. No Redis or RQ queue.
- Job runner polls every 2 seconds. Multiple runners would contend for the same jobs.
- Annotation makes 2 network calls per variant on cache miss.
- PCA matrix caps at 5,000 variants.
- Audit log loads up to 500 entries. No pagination.
- SQLite writes are single-threaded.

### Compliance

- Audit log is hash-chained for tamper evidence.
- Not SOC 2, HIPAA-certified, or GDPR-compliant at the organizational level.
- No BAA support. No QMS. No clinical validation study.
- Local mode stores JWT in localStorage.

### Known issues

- xhtml2pdf does not support flexbox. Report layout uses tables.
- mean_variant_quality is the mean of variant QUAL scores, not read depth or coverage.
- MAC addresses deliberately not used for machine fingerprinting. A persisted UUID is used instead.

## Testing

ACMG engine validation:

    cd backend
    source .venv/Scripts/activate
    python validate_acmg.py

Runs the engine against expert-classified variants in tests/validation/clingen_corpus.json and reports agreement.

VCEP engine test:

    cd backend
    source .venv/Scripts/activate
    python test_vcep.py

Verifies VCEP thresholds, suppressed criteria, and per-gene behavior.

## Maintenance

A Windows Scheduled Task (GenomicsOps VCEP Update Check) runs on the 1st of every month at 3 AM. It compares cached spec versions and logs changes to backend/logs/vcep_check.log.

To refresh manually:

    cd backend
    source .venv/Scripts/activate
    python scripts/fetch_vcep_specs.py
    python scripts/parse_vcep_thresholds.py

Then re-run validation to see if classifications shifted.

## Stack

- Frontend: Next.js 14, React 18, Tailwind CSS, Recharts, lucide-react
- Backend: FastAPI, Pydantic v2, Uvicorn, httpx
- Database: SQLite (local) or PostgreSQL via Supabase (cloud)
- VCF parsing: Pure Python (small), DuckDB (large)
- ACMG data: MyVariant.info, Ensembl VEP REST
- Auth: Supabase (cloud), bcrypt + JWT (local)
- PDF: xhtml2pdf
- PCA: scikit-learn
- License signing: Ed25519 via cryptography
- Deployment: Vercel + Render + Supabase (cloud), or fully local

## License

MIT License. See LICENSE.

## Support

- Support: support@genomicsops.io
- Sales: sales@genomicsops.io
- Security: security@genomicsops.io

# Frequently Asked Questions

## What is GenomicsOps?

GenomicsOps is a variant interpretation workbench for research labs and bioinformatics teams. It ingests VCF files, annotates variants with gene and ClinVar data, classifies them using a transparent ACMG/AMP engine, and exports clinically significant findings as FHIR R4, custom JSON, or HL7 v2 for LIMS integration.

## Is it a clinical tool?

**No.** GenomicsOps is **Research Use Only (RUO)**. It is not intended for clinical diagnosis, treatment, or patient management. Classifications follow ACMG/AMP 2015 guidelines applied automatically and must be verified by a qualified clinical scientist before any clinical use. This tool does not replace expert review.

## How is this different from VarSome, Geneyx, or Fabric?

Three ways:

1. **Transparency.** Every ACMG classification shows exactly which criteria fired, the evidence behind each criterion, and what would change the call. You can add or remove criteria and watch the classification recompute in real time.
2. **Offline-capable.** Runs on your machine with no cloud dependency. In offline mode, every outbound network call is blocked at the application layer and audited. Patient data never leaves your infrastructure.
3. **Structured export.** Pushes FHIR R4 DiagnosticReport + Observations directly to your EHR/LIMS — not a PDF you have to copy-paste.

## Does it work on real VCF files?

Yes. It has been tested on the GIAB NA12878 benchmark VCF (GRCh38) and synthetic multi-sample cohorts. It handles VCFs up to ~2 GB uncompressed via DuckDB streaming.

## What annotation sources does it use?

Currently MyVariant.info (aggregates ClinVar, dbSNP, SnpEff) and Ensembl VEP. All annotation is optional — if you're fully offline, you can disable it entirely and still use the ACMG engine on pre-annotated VCFs.

## Is my data safe?

Yes.

- **Offline mode:** No data leaves your machine. Every outbound call is blocked and logged.
- **Cloud mode:** Each customer is isolated at the database level via Postgres Row-Level Security.
- **Audit trail:** Every action is logged with user attribution and timestamp.
- **GDPR:** Right-to-erasure is a single API call. Legal holds protect samples under review.
- **PHI tagging:** Mark samples that contain PHI so stricter retention applies.

## What formats can I export?

- **FHIR R4** — DiagnosticReport + Observations for Epic, Cerner, modern EHRs
- **Custom JSON** — for any LIMS with a REST API
- **HL7 v2 ORU^R01** — for legacy hospital systems
- **PDF reports** — professional clinical-style layout with full ACMG evidence per variant

## Does it support cohort analysis?

Yes. Upload multiple samples, group them into a cohort, and run:
- **PCA clustering** — see which samples group together based on shared variants
- **Gene enrichment** — which genes are mutated across the cohort, and in what fraction of samples
- **Shared variants** — variants present in multiple samples

## Can I use it offline?

Yes, in local mode. Activate an offline license and the app runs entirely on your machine with a local SQLite database. The only feature requiring internet is optional variant annotation.

## How does licensing work?

Three tiers:

- **Trial** — 7 days, full access
- **Standard** — for individual researchers and small labs
- **Enterprise** — for labs with integration and compliance needs

Licenses are signed tokens bound to a machine fingerprint. Activation is offline — you send us your fingerprint, we send back a token. No server call is required after activation.

## Can I run it on-premise?

Yes. The desktop build runs entirely on a lab workstation with no cloud dependency. For larger deployments, contact us about an enterprise license with Helm chart deployment.

## What's the pipeline runner?

The pipeline runner executes lightweight Python scripts against your data (variant statistics, deep QC, annotation refresh). It is not a Nextflow/Snakemake replacement. For full pipeline orchestration, use GenomicsOps alongside your existing workflow engine.

## Can I request a feature?

Yes. Beta users get priority access to our roadmap. Email support@genomicsops.io with what you need and why.

## How do I get started?

1. Download the app (link coming soon)
2. Launch it — you'll see a machine fingerprint on the license page
3. Email the fingerprint to support@genomicsops.io
4. We send back a 7-day trial token
5. Paste the token into the license page and start uploading VCFs

## Who is this for?

- Research labs doing variant interpretation
- Bioinformatics core facilities
- Academic genomics groups
- Biotech R&D teams
- Anyone tired of Excel + scripting for variant review

## Who is this NOT for?

- Clinical diagnostics (see "Is it a clinical tool?")
- Full genome alignment/calling (use your existing pipeline)
- Large-scale population genomics (designed for lab-scale, not 100k-genome studies)
- Anyone who needs FDA-cleared software

## Contact

- **Support:** support@genomicsops.io
- **Sales:** sales@genomicsops.io
- **Security disclosures:** security@genomicsops.io

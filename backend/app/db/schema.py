"""
SQLite schema for the local (desktop) mode.
Mirrors the Supabase tables minus orgs — users replace orgs.
"""
import sqlite3
from pathlib import Path
from app.config import settings


SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    name TEXT,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'viewer'
        CHECK (role IN ('admin','analyst','viewer')),
    is_active INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now')),
    last_login TEXT
);

CREATE TABLE IF NOT EXISTS sessions (
    token TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TEXT DEFAULT (datetime('now')),
    expires_at TEXT NOT NULL,
    last_activity TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS samples (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    species TEXT DEFAULT 'Homo sapiens',
    reference_genome TEXT DEFAULT 'GRCh38',
    file_path TEXT,
    file_type TEXT,
    file_size_bytes INTEGER,
    status TEXT DEFAULT 'uploaded',
    metadata TEXT DEFAULT '{}',
    reference_build TEXT DEFAULT 'GRCh38',
    pipeline_version TEXT,
    provenance_hash TEXT,
    contains_phi INTEGER DEFAULT 0,
    phi_categories TEXT DEFAULT '[]',
    retention_days INTEGER,
    legal_hold INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_samples_user ON samples(user_id);
CREATE INDEX IF NOT EXISTS idx_samples_status ON samples(status);

CREATE TABLE IF NOT EXISTS variants (
    id TEXT PRIMARY KEY,
    sample_id TEXT NOT NULL REFERENCES samples(id) ON DELETE CASCADE,
    chrom TEXT NOT NULL,
    pos INTEGER NOT NULL,
    ref TEXT,
    alt TEXT,
    qual REAL,
    filter TEXT,
    genotype TEXT,
    depth INTEGER,
    gene TEXT,
    consequence TEXT,
    impact TEXT,
    clinvar_significance TEXT,
    gnomad_af REAL,
    rsid TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_var_sample ON variants(sample_id);
CREATE INDEX IF NOT EXISTS idx_var_pos ON variants(chrom, pos);
CREATE INDEX IF NOT EXISTS idx_var_gene ON variants(gene);
CREATE INDEX IF NOT EXISTS idx_var_clinvar ON variants(clinvar_significance);

CREATE TABLE IF NOT EXISTS qc_metrics (
    id TEXT PRIMARY KEY,
    sample_id TEXT NOT NULL REFERENCES samples(id) ON DELETE CASCADE,
    total_reads INTEGER,
    mapped_reads INTEGER,
    mean_variant_quality REAL,
    duplication_rate REAL,
    contamination_rate REAL,
    q30_rate REAL,
    gc_content REAL,
    variant_count INTEGER,
    snp_count INTEGER,
    indel_count INTEGER,
    computed_at TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_qc_sample ON qc_metrics(sample_id);

CREATE TABLE IF NOT EXISTS variant_acmg (
    id TEXT PRIMARY KEY,
    variant_id TEXT UNIQUE NOT NULL REFERENCES variants(id) ON DELETE CASCADE,
    classification TEXT,
    criteria_fired TEXT DEFAULT '[]',
    auto_classification TEXT,
    evidence_summary TEXT,
    confidence TEXT,
    engine_version TEXT,
    rule_set_version TEXT,
    evidence_snapshot_hash TEXT,
    notes TEXT,
    reviewed_by TEXT REFERENCES users(id),
    reviewed_at TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_acmg_variant ON variant_acmg(variant_id);
CREATE INDEX IF NOT EXISTS idx_acmg_class ON variant_acmg(classification);

CREATE TABLE IF NOT EXISTS cohorts (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    description TEXT,
    sample_ids TEXT DEFAULT '[]',
    created_at TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_cohorts_user ON cohorts(user_id);

CREATE TABLE IF NOT EXISTS pipeline_runs (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    sample_id TEXT REFERENCES samples(id) ON DELETE CASCADE,
    pipeline_name TEXT NOT NULL,
    status TEXT DEFAULT 'queued',
    logs TEXT,
    started_at TEXT,
    finished_at TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_runs_user ON pipeline_runs(user_id);
CREATE INDEX IF NOT EXISTS idx_runs_status ON pipeline_runs(status);

CREATE TABLE IF NOT EXISTS reports (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    sample_id TEXT REFERENCES samples(id) ON DELETE SET NULL,
    title TEXT NOT NULL,
    type TEXT DEFAULT 'sample',
    file_path TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_reports_user ON reports(user_id);

CREATE TABLE IF NOT EXISTS audit_log (
    id TEXT PRIMARY KEY,
    user_id TEXT REFERENCES users(id) ON DELETE SET NULL,
    action TEXT NOT NULL,
    resource_type TEXT,
    resource_id TEXT,
    details TEXT DEFAULT '{}',
    ip_address TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_log(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_log(created_at DESC);

CREATE TABLE IF NOT EXISTS provenance (
    id TEXT PRIMARY KEY,
    resource_type TEXT NOT NULL,
    resource_id TEXT NOT NULL,
    reference_genome TEXT,
    pipeline_version TEXT,
    tool_versions TEXT DEFAULT '{}',
    annotation_db_version TEXT,
    container_hash TEXT,
    command TEXT,
    inputs TEXT DEFAULT '{}',
    outputs TEXT DEFAULT '{}',
    created_at TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_prov_resource ON provenance(resource_type, resource_id);

CREATE TABLE IF NOT EXISTS consent_records (
    id TEXT PRIMARY KEY,
    sample_id TEXT REFERENCES samples(id) ON DELETE CASCADE,
    subject_id TEXT,
    consent_type TEXT NOT NULL,
    granted INTEGER DEFAULT 1,
    granted_at TEXT DEFAULT (datetime('now')),
    granted_by TEXT,
    expires_at TEXT,
    revoked_at TEXT,
    notes TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_consent_sample ON consent_records(sample_id);
CREATE INDEX IF NOT EXISTS idx_consent_subject ON consent_records(subject_id);

CREATE TABLE IF NOT EXISTS mane_transcripts (
    gene_symbol TEXT PRIMARY KEY,
    mane_select TEXT NOT NULL,
    mane_plus_clinical TEXT,
    refseq_protein TEXT,
    chrom TEXT,
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS retention_runs (
    id TEXT PRIMARY KEY,
    run_at TEXT DEFAULT (datetime('now')),
    policy_days INTEGER,
    samples_deleted INTEGER DEFAULT 0,
    samples_retained INTEGER DEFAULT 0,
    legal_holds_skipped INTEGER DEFAULT 0,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS system_settings (
    key TEXT PRIMARY KEY,
    value TEXT,
    updated_at TEXT DEFAULT (datetime('now'))
);
"""


MANE_SEED = [
    ("BRCA1", "NM_007294.4", "NM_007294.4", "NP_009225.1"),
    ("BRCA2", "NM_000059.4", "NM_000059.4", "NP_000050.3"),
    ("TP53", "NM_000546.6", "NM_000546.6", "NP_000537.3"),
    ("CFTR", "NM_000492.4", "NM_000492.4", "NP_000483.3"),
    ("MLH1", "NM_000249.4", "NM_000249.4", "NP_000240.1"),
    ("MSH2", "NM_000251.3", "NM_000251.3", "NP_000242.1"),
    ("MSH6", "NM_000179.3", "NM_000179.3", "NP_000170.1"),
    ("PMS2", "NM_000535.7", "NM_000535.7", "NP_000526.2"),
    ("APC", "NM_000038.6", "NM_000038.6", "NP_000029.2"),
    ("VHL", "NM_000551.4", "NM_000551.4", "NP_000542.1"),
    ("PTEN", "NM_000314.8", "NM_000314.8", "NP_000305.3"),
    ("RB1", "NM_000321.3", "NM_000321.3", "NP_000312.2"),
    ("NF1", "NM_000267.3", "NM_000267.3", "NP_000258.1"),
    ("NF2", "NM_000268.4", "NM_000268.4", "NP_000259.1"),
    ("RET", "NM_020975.6", "NM_020975.6", "NP_066124.1"),
    ("MEN1", "NM_000244.4", "NM_000244.4", "NP_000235.3"),
    ("STK11", "NM_000455.5", "NM_000455.5", "NP_000446.1"),
    ("PALB2", "NM_024675.4", "NM_024675.4", "NP_078951.2"),
    ("ATM", "NM_000051.4", "NM_000051.4", "NP_000042.3"),
    ("CHEK2", "NM_007194.4", "NM_007194.4", "NP_009125.1"),
    ("CDH1", "NM_004360.5", "NM_004360.5", "NP_004351.1"),
    ("BMPR1A", "NM_004329.3", "NM_004329.3", "NP_004320.2"),
    ("SMAD4", "NM_005359.6", "NM_005359.6", "NP_005350.1"),
    ("MUTYH", "NM_001128425.2", "NM_001048171.2", "NP_001121897.1"),
    ("MTHFR", "NM_005957.5", "NM_005957.5", "NP_005948.3"),
    ("DNMT3A", "NM_022552.5", "NM_022552.5", "NP_072046.2"),
]


def init_schema(db_path: str = None):
    """Create all tables and seed MANE transcripts if empty."""
    path = db_path or settings.LOCAL_DB_PATH
    Path(path).parent.mkdir(parents=True, exist_ok=True)

    con = sqlite3.connect(path)
    con.executescript(SCHEMA_SQL)

    # Seed MANE if empty
    cur = con.execute("SELECT COUNT(*) FROM mane_transcripts")
    if cur.fetchone()[0] == 0:
        con.executemany(
            "INSERT INTO mane_transcripts (gene_symbol, mane_select, mane_plus_clinical, refseq_protein) VALUES (?,?,?,?)",
            MANE_SEED,
        )

    con.commit()
    con.close()
    return path

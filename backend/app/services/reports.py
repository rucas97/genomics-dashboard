"""
PDF report generation using xhtml2pdf (pure Python, no GTK needed).
Generates HTML from sample/cohort data, converts to PDF, uploads to Supabase Storage.
"""
import uuid
from datetime import datetime
from io import BytesIO
from app.supabase_client import supabase


def _html_shell(title: str, body: str) -> str:
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
    <meta charset="utf-8">
    <style>
      @page {{ size: A4; margin: 2cm; }}
      body {{ font-family: Helvetica, Arial, sans-serif; color: #1e293b; font-size: 11px; }}
      h1 {{ font-size: 22px; color: #059669; margin: 0 0 4px 0; }}
      h2 {{ font-size: 14px; color: #0f172a; margin: 20px 0 8px 0; border-bottom: 1px solid #e2e8f0; padding-bottom: 4px; }}
      .sub {{ color: #64748b; font-size: 11px; margin-bottom: 20px; }}
      table {{ width: 100%; border-collapse: collapse; margin-top: 8px; }}
      th {{ background: #f1f5f9; text-align: left; padding: 6px; font-size: 10px; color: #475569; }}
      td {{ padding: 6px; border-bottom: 1px solid #e2e8f0; font-size: 10px; }}
      .badge {{ display: inline-block; padding: 2px 6px; border-radius: 3px; font-size: 9px; }}
      .pathogenic {{ background: #fee2e2; color: #991b1b; }}
      .vus {{ background: #fef3c7; color: #92400e; }}
      .benign {{ background: #d1fae5; color: #065f46; }}
      .other {{ background: #e2e8f0; color: #475569; }}
      .high {{ background: #fee2e2; color: #991b1b; }}
      .moderate {{ background: #fef3c7; color: #92400e; }}
      .grid {{ width: 100%; }}
      .kv {{ padding: 4px 0; border-bottom: 1px dotted #e2e8f0; }}
      .kv .k {{ color: #64748b; }}
      .footer {{ margin-top: 30px; padding-top: 10px; border-top: 1px solid #e2e8f0; color: #94a3b8; font-size: 9px; text-align: center; }}
      .card {{ width: 22%; padding: 8px; border: 1px solid #e2e8f0; border-radius: 4px; display: inline-block; margin-right: 1%; vertical-align: top; }}
      .card .label {{ color: #64748b; font-size: 9px; text-transform: uppercase; }}
      .card .value {{ font-size: 18px; font-weight: bold; }}
    </style>
    </head>
    <body>
      <h1>{title}</h1>
      <div class="sub">Generated {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')} · GenomicsOps</div>
      {body}
      <div class="footer">GenomicsOps · Automated Report · Not for clinical use without verification</div>
    </body>
    </html>
    """


def _classify(cs: str | None) -> str:
    if not cs:
        return "other"
    c = cs.lower()
    if "pathogenic" in c or "likely pathogenic" in c or "likely_pathogenic" in c:
        return "pathogenic"
    if "benign" in c:
        return "benign"
    if "uncertain" in c:
        return "vus"
    return "other"


def generate_sample_report_html(sample: dict, qc: dict | None, variants: list[dict]) -> str:
    total = len(variants)
    counts = {"pathogenic": 0, "vus": 0, "benign": 0, "other": 0}
    for v in variants:
        counts[_classify(v.get("clinvar_significance"))] += 1

    prioritized = [
        v for v in variants
        if _classify(v.get("clinvar_significance")) == "pathogenic"
        or (v.get("impact") or "").upper() == "HIGH"
    ]

    qc_html = ""
    if qc:
        qc_html = f"""
        <h2>QC Metrics</h2>
        <div class="card"><div class="label">Total Variants</div><div class="value">{qc.get('variant_count', '—')}</div></div>
        <div class="card"><div class="label">SNPs</div><div class="value">{qc.get('snp_count', '—')}</div></div>
        <div class="card"><div class="label">Indels</div><div class="value">{qc.get('indel_count', '—')}</div></div>
        <div class="card"><div class="label">Mean Quality</div><div class="value">{round(qc.get('mean_coverage') or 0, 1)}</div></div>
        <div style="clear:both"></div>
        """

    summary_html = f"""
    <h2>Clinical Summary</h2>
    <div class="card"><div class="label">Total</div><div class="value">{total}</div></div>
    <div class="card"><div class="label">Pathogenic</div><div class="value" style="color:#991b1b">{counts['pathogenic']}</div></div>
    <div class="card"><div class="label">VUS</div><div class="value" style="color:#92400e">{counts['vus']}</div></div>
    <div class="card"><div class="label">Benign</div><div class="value" style="color:#065f46">{counts['benign']}</div></div>
    <div style="clear:both"></div>
    """

    prio_rows = ""
    for v in prioritized[:50]:
        cls = _classify(v.get("clinvar_significance"))
        impact = (v.get("impact") or "").upper()
        impact_cls = "high" if impact == "HIGH" else "moderate" if impact == "MODERATE" else "other"
        prio_rows += f"""
        <tr>
          <td>{v.get('chrom')}:{v.get('pos')}</td>
          <td style="font-family:monospace">{v.get('ref')}/{v.get('alt')}</td>
          <td><b>{v.get('gene') or '—'}</b></td>
          <td>{v.get('consequence') or '—'}</td>
          <td><span class="badge {impact_cls}">{impact or '—'}</span></td>
          <td><span class="badge {cls}">{v.get('clinvar_significance') or '—'}</span></td>
        </tr>
        """

    if not prio_rows:
        prio_rows = '<tr><td colspan="6" style="text-align:center;color:#94a3b8">No prioritized variants</td></tr>'

    body = f"""
    <h2>Sample Info</h2>
    <table>
      <tr><td style="width:30%;color:#64748b">Name</td><td>{sample.get('name', '—')}</td></tr>
      <tr><td style="color:#64748b">Status</td><td>{sample.get('status', '—')}</td></tr>
      <tr><td style="color:#64748b">File type</td><td>{sample.get('file_type', '—')}</td></tr>
      <tr><td style="color:#64748b">Reference genome</td><td>{sample.get('reference_genome', '—')}</td></tr>
      <tr><td style="color:#64748b">Species</td><td>{sample.get('species', '—')}</td></tr>
      <tr><td style="color:#64748b">Created</td><td>{str(sample.get('created_at', '—'))[:19]}</td></tr>
    </table>

    {qc_html}
    {summary_html}

    <h2>Prioritized Variants (Pathogenic + High Impact)</h2>
    <table>
      <thead><tr><th>Position</th><th>Ref/Alt</th><th>Gene</th><th>Consequence</th><th>Impact</th><th>ClinVar</th></tr></thead>
      <tbody>{prio_rows}</tbody>
    </table>
    """

    return _html_shell(f"Sample Report · {sample.get('name', '')}", body)


def generate_cohort_report_html(cohort: dict, samples: list[dict], variants: list[dict], stats: dict) -> str:
    sample_count = len(samples)
    sample_rows = "".join(
        f"<tr><td>{s.get('name')}</td><td>{s.get('status')}</td><td>{s.get('file_type')}</td></tr>"
        for s in samples
    )

    gene_rows = "".join(
        f"<tr><td><b>{g['gene']}</b></td><td>{g['count']}</td><td>{g['sample_count']}/{sample_count}</td><td>{g['sample_pct']}%</td></tr>"
        for g in stats.get("top_genes", [])[:15]
    )

    counts = stats.get("classification", {})

    body = f"""
    <h2>Cohort Info</h2>
    <table>
      <tr><td style="width:30%;color:#64748b">Name</td><td>{cohort.get('name', '—')}</td></tr>
      <tr><td style="color:#64748b">Samples</td><td>{sample_count}</td></tr>
      <tr><td style="color:#64748b">Total variants</td><td>{stats.get('n_variants', 0)}</td></tr>
      <tr><td style="color:#64748b">Created</td><td>{str(cohort.get('created_at', '—'))[:19]}</td></tr>
    </table>

    <h2>Classification Breakdown</h2>
    <div class="card"><div class="label">Pathogenic</div><div class="value" style="color:#991b1b">{counts.get('pathogenic', 0)}</div></div>
    <div class="card"><div class="label">VUS</div><div class="value" style="color:#92400e">{counts.get('vus', 0)}</div></div>
    <div class="card"><div class="label">Benign</div><div class="value" style="color:#065f46">{counts.get('benign', 0)}</div></div>
    <div class="card"><div class="label">Other</div><div class="value">{counts.get('other', 0)}</div></div>
    <div style="clear:both"></div>

    <h2>Gene Enrichment</h2>
    <table>
      <thead><tr><th>Gene</th><th>Variants</th><th>Samples</th><th>Frequency</th></tr></thead>
      <tbody>{gene_rows or '<tr><td colspan="4" style="text-align:center;color:#94a3b8">No gene data</td></tr>'}</tbody>
    </table>

    <h2>Samples in Cohort</h2>
    <table>
      <thead><tr><th>Name</th><th>Status</th><th>Type</th></tr></thead>
      <tbody>{sample_rows}</tbody>
    </table>
    """

    return _html_shell(f"Cohort Report · {cohort.get('name', '')}", body)


def render_pdf(html: str) -> bytes:
    """Convert HTML to PDF bytes via xhtml2pdf (pure Python)."""
    from xhtml2pdf import pisa
    buf = BytesIO()
    result = pisa.CreatePDF(html, dest=buf, encoding="utf-8")
    if result.err:
        raise RuntimeError(f"xhtml2pdf failed with {result.err} error(s)")
    return buf.getvalue()


def upload_report(user_id: str, title: str, pdf_bytes: bytes) -> str:
    """Upload PDF to Supabase Storage, return the storage path."""
    report_id = str(uuid.uuid4())
    path = f"{user_id}/reports/{report_id}.pdf"
    supabase.storage.from_("genomic-files").upload(
        path, pdf_bytes, {"content-type": "application/pdf"}
    )
    return path

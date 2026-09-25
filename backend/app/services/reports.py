"""
PDF report generation using xhtml2pdf.
Professional clinical-style layout with metadata, provenance, per-variant
ACMG evidence, and legal disclaimers.
"""
import base64
import uuid
from datetime import datetime
from io import BytesIO
from pathlib import Path
from app.config import settings
from app.supabase_client import supabase


def _logo_data_uri() -> str:
    logo_path = Path(__file__).parent.parent / "static" / "logo-pdf.png"
    if not logo_path.exists():
        logo_path = Path(__file__).parent.parent / "static" / "logo.png"
    if not logo_path.exists():
        return ""
    try:
        with open(logo_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        return f"data:image/png;base64,{b64}"
    except Exception as e:
        print(f"Failed to load logo: {e}")
        return ""


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


def _badge(text: str, cls: str) -> str:
    return f'<span class="badge {cls}">{text}</span>'


def _report_shell(
    title: str,
    subtitle: str,
    metadata: dict,
    body: str,
    footer_note: str = "",
) -> str:
    logo_uri = _logo_data_uri()
    logo_html = f'<img src="{logo_uri}" width="160" />' if logo_uri else \
        '<span style="font-size:20px;font-weight:bold;color:#10b981;">GenomicsOps</span>'

    meta_rows = "".join(
        f'<tr><td class="mk">{k}</td><td class="mv">{v}</td></tr>'
        for k, v in metadata.items() if v
    )

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
    <meta charset="utf-8">
    <style>
      @page {{
        size: A4;
        margin: 1.5cm 2cm 2cm 2cm;
        @frame footer {{
          -pdf-frame-content: footerContent;
          bottom: 1cm;
          margin-left: 2cm;
          margin-right: 2cm;
          height: 1cm;
        }}
      }}
      body {{
        font-family: Helvetica, Arial, sans-serif;
        color: #1e293b;
        font-size: 10px;
        line-height: 1.4;
        margin: 0;
        padding: 0;
      }}
      .header {{
        border-bottom: 2px solid #0f172a;
        padding-bottom: 12px;
        margin-bottom: 16px;
      }}
      .header table {{ width: 100%; }}
      .header td {{ border: none; padding: 0; vertical-align: middle; }}
      .header-right {{ text-align: right; color: #64748b; font-size: 9px; }}
      .title-block {{ margin-bottom: 18px; }}
      h1 {{
        font-size: 20px;
        color: #0f172a;
        margin: 0 0 3px 0;
        font-weight: bold;
      }}
      .subtitle {{
        font-size: 11px;
        color: #64748b;
        margin: 0;
      }}
      h2 {{
        font-size: 12px;
        color: #0f172a;
        margin: 20px 0 8px 0;
        padding-bottom: 4px;
        border-bottom: 1px solid #e2e8f0;
        font-weight: bold;
      }}
      h3 {{
        font-size: 11px;
        color: #0f172a;
        margin: 14px 0 6px 0;
        font-weight: bold;
      }}
      .meta {{ width: 100%; margin-bottom: 12px; }}
      .meta td {{ padding: 3px 0; border: none; vertical-align: top; }}
      .meta .mk {{ width: 40%; color: #64748b; font-size: 9px; }}
      .meta .mv {{ color: #0f172a; font-size: 9px; font-family: monospace; }}
      .cards {{ width: 100%; margin: 8px 0 16px 0; }}
      .cards td {{
        padding: 10px 8px;
        border: 1px solid #e2e8f0;
        text-align: center;
        width: 25%;
      }}
      .cards .label {{ color: #64748b; font-size: 8px; text-transform: uppercase; letter-spacing: 0.5px; }}
      .cards .value {{ font-size: 20px; font-weight: bold; color: #0f172a; margin-top: 2px; }}
      .cards .value.warn {{ color: #991b1b; }}
      .cards .value.ok {{ color: #065f46; }}
      table.data {{ width: 100%; border-collapse: collapse; margin-top: 6px; }}
      table.data th {{
        background-color: #f1f5f9;
        text-align: left;
        padding: 5px 6px;
        font-size: 8px;
        color: #475569;
        text-transform: uppercase;
        letter-spacing: 0.3px;
        border-bottom: 1px solid #cbd5e1;
      }}
      table.data td {{
        padding: 5px 6px;
        border-bottom: 1px solid #e2e8f0;
        font-size: 9px;
        vertical-align: top;
      }}
      table.data tr.alt td {{ background-color: #f8fafc; }}
      .badge {{
        display: inline-block;
        padding: 1px 5px;
        font-size: 8px;
        font-weight: bold;
      }}
      .pathogenic {{ background-color: #fee2e2; color: #991b1b; }}
      .likely-pathogenic {{ background-color: #fed7aa; color: #9a3412; }}
      .vus {{ background-color: #fef3c7; color: #92400e; }}
      .likely-benign {{ background-color: #d1fae5; color: #065f46; }}
      .benign {{ background-color: #bbf7d0; color: #14532d; }}
      .other {{ background-color: #e2e8f0; color: #475569; }}
      .high {{ background-color: #fee2e2; color: #991b1b; }}
      .moderate {{ background-color: #fef3c7; color: #92400e; }}
      .low {{ background-color: #e2e8f0; color: #475569; }}
      .variant-detail {{
        border: 1px solid #e2e8f0;
        padding: 8px 10px;
        margin: 8px 0;
        background-color: #f8fafc;
      }}
      .variant-detail .vhead {{
        font-family: monospace;
        font-size: 10px;
        font-weight: bold;
        color: #0f172a;
        margin-bottom: 4px;
      }}
      .criteria-list {{ margin: 4px 0 0 0; padding: 0; }}
      .criteria-list li {{
        list-style: none;
        padding: 2px 0;
        font-size: 9px;
      }}
      .criteria-list .code {{
        font-weight: bold;
        font-family: monospace;
        color: #059669;
        margin-right: 6px;
      }}
      .criteria-list .ev {{ color: #64748b; }}
      .disclaimer {{
        background-color: #fef3c7;
        border-left: 3px solid #f59e0b;
        padding: 8px 12px;
        margin-top: 20px;
        font-size: 8px;
        color: #78350f;
      }}
      .signature-block {{
        border-top: 1px solid #cbd5e1;
        margin-top: 24px;
        padding-top: 12px;
        font-size: 9px;
      }}
      .signature-block table {{ width: 100%; }}
      .signature-block td {{ padding: 4px 0; border: none; }}
      .footer-text {{
        text-align: center;
        color: #94a3b8;
        font-size: 8px;
        border-top: 1px solid #e2e8f0;
        padding-top: 6px;
      }}
      .note-block {{
        background-color: #f1f5f9;
        padding: 8px 10px;
        border-left: 3px solid #64748b;
        margin: 8px 0;
        font-size: 9px;
        color: #334155;
        font-style: italic;
      }}
    </style>
    </head>
    <body>
      <div class="header">
        <table>
          <tr>
            <td style="width: 60%;">{logo_html}</td>
            <td class="header-right" style="width: 40%;">
              <b style="color:#0f172a;">GENOMIC VARIANT REPORT</b><br/>
              Research Use Only<br/>
              {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}
            </td>
          </tr>
        </table>
      </div>

      <div class="title-block">
        <h1>{title}</h1>
        <p class="subtitle">{subtitle}</p>
      </div>

      <h2>Report Metadata</h2>
      <table class="meta">
        {meta_rows}
      </table>

      {body}

      <div class="disclaimer">
        <b>Research Use Only.</b> This report is generated by GenomicsOps,
        a research-use-only variant interpretation workbench. It is not
        intended for clinical diagnosis, treatment, or patient management.
        Classifications follow ACMG/AMP 2015 guidelines applied automatically
        and must be verified by a qualified clinical scientist before any
        clinical use. This report does not replace expert review.
      </div>

      <div class="signature-block">
        <table>
          <tr>
            <td style="width: 50%;"><b>Reviewed by:</b> _____________________</td>
            <td style="width: 50%;"><b>Date:</b> _____________________</td>
          </tr>
        </table>
      </div>

      <div id="footerContent">
        <div class="footer-text">
          {footer_note or 'GenomicsOps'} · Page <pdf:pagenumber /> of <pdf:pagecount />
        </div>
      </div>
    </body>
    </html>
    """


def generate_sample_report_html(sample: dict, qc: dict | None, variants: list[dict]) -> str:
    total = len(variants)
    counts = {"pathogenic": 0, "likely_pathogenic": 0, "vus": 0, "likely_benign": 0, "benign": 0, "other": 0}

    for v in variants:
        acmg = (v.get("acmg_classification") or "").lower().replace(" ", "_")
        if "likely_pathogenic" in acmg or "likely pathogenic" in acmg:
            counts["likely_pathogenic"] += 1
        elif acmg == "pathogenic" or "pathogenic" in acmg:
            counts["pathogenic"] += 1
        elif "likely_benign" in acmg or "likely benign" in acmg:
            counts["likely_benign"] += 1
        elif acmg == "benign":
            counts["benign"] += 1
        elif acmg == "vus" or not acmg:
            counts["vus"] += 1
        else:
            counts["other"] += 1

    actionable = [
        v for v in variants
        if (v.get("acmg_classification") or "").lower() in ("pathogenic", "likely pathogenic")
        or (v.get("impact") or "").upper() == "HIGH"
    ]

    # --- Metadata ---
    metadata = {
        "Sample name": sample.get("name"),
        "Sample ID": sample.get("id", "")[:8] + "..." if sample.get("id") else "",
        "File type": sample.get("file_type"),
        "File size": f"{sample.get('file_size_bytes', 0):,} bytes" if sample.get("file_size_bytes") else "",
        "Reference genome": sample.get("reference_build") or sample.get("reference_genome") or "GRCh38",
        "Species": sample.get("species", "Homo sapiens"),
        "Uploaded": str(sample.get("created_at", ""))[:19],
        "Pipeline version": sample.get("pipeline_version", "0.1.0"),
    }

    # --- QC Cards ---
    qc_html = ""
    if qc:
        qc_html = f"""
        <h2>Quality Control Metrics</h2>
        <table class="cards">
          <tr>
            <td>
              <div class="label">Total Variants</div>
              <div class="value">{qc.get('variant_count', '—')}</div>
            </td>
            <td>
              <div class="label">SNPs</div>
              <div class="value">{qc.get('snp_count', '—')}</div>
            </td>
            <td>
              <div class="label">Indels</div>
              <div class="value">{qc.get('indel_count', '—')}</div>
            </td>
            <td>
              <div class="label">Mean Quality</div>
              <div class="value">{round(qc.get('mean_coverage') or 0, 1)}</div>
            </td>
          </tr>
        </table>
        """

    # --- Classification summary cards ---
    summary_html = f"""
    <h2>ACMG Classification Summary</h2>
    <table class="cards">
      <tr>
        <td>
          <div class="label">Pathogenic</div>
          <div class="value warn">{counts['pathogenic']}</div>
        </td>
        <td>
          <div class="label">Likely Pathogenic</div>
          <div class="value warn">{counts['likely_pathogenic']}</div>
        </td>
        <td>
          <div class="label">VUS</div>
          <div class="value">{counts['vus']}</div>
        </td>
        <td>
          <div class="label">Benign / LB</div>
          <div class="value ok">{counts['benign'] + counts['likely_benign']}</div>
        </td>
      </tr>
    </table>
    <p style="font-size:9px;color:#64748b;">
      Total variants analyzed: <b>{total}</b> ·
      Actionable (pathogenic or high-impact): <b>{len(actionable)}</b>
    </p>
    """

    # --- Prioritized variant detail cards with full ACMG evidence ---
    variant_html = ""
    for i, v in enumerate(actionable[:25]):
        cls_raw = v.get("acmg_classification") or "VUS"
        cls = cls_raw.lower().replace(" ", "-")
        impact = (v.get("impact") or "").upper()
        impact_cls = impact.lower() if impact in ("HIGH", "MODERATE", "LOW") else "other"

        # Criteria fired
        criteria = v.get("acmg_criteria_fired") or []
        if isinstance(criteria, str):
            import json
            try:
                criteria = json.loads(criteria)
            except Exception:
                criteria = []

        criteria_html = ""
        if criteria:
            criteria_html = '<ul class="criteria-list">'
            for c in criteria:
                code = c.get("code", "")
                ev = c.get("evidence", "")
                criteria_html += f'<li><span class="code">{code}</span><span class="ev">{ev}</span></li>'
            criteria_html += "</ul>"

        # Sample-level QC per-variant
        qual = v.get("qual")
        depth = v.get("depth")

        variant_html += f"""
        <div class="variant-detail">
          <div class="vhead">
            {v.get('chrom')}:{v.get('pos')} {v.get('ref')}→{v.get('alt')}
            &nbsp;&nbsp;{_badge(cls_raw, cls)}
            &nbsp;&nbsp;{_badge(impact or 'N/A', impact_cls)}
          </div>
          <table class="meta">
            <tr>
              <td class="mk">Gene</td>
              <td class="mv">{v.get('gene') or '—'}</td>
              <td class="mk">Consequence</td>
              <td class="mv">{v.get('consequence') or '—'}</td>
            </tr>
            <tr>
              <td class="mk">MANE Select</td>
              <td class="mv">{v.get('mane_select') or '—'}</td>
              <td class="mk">ClinVar</td>
              <td class="mv">{v.get('clinvar_significance') or '—'}</td>
            </tr>
            <tr>
              <td class="mk">gnomAD AF</td>
              <td class="mv">{f"{v.get('gnomad_af'):.2e}" if v.get('gnomad_af') is not None else '—'}</td>
              <td class="mk">Quality</td>
              <td class="mv">{qual if qual is not None else '—'}</td>
            </tr>
          </table>
          {f'<div style="margin-top:6px;font-size:8px;color:#64748b;text-transform:uppercase;letter-spacing:0.5px;">ACMG Criteria Fired</div>{criteria_html}' if criteria_html else ''}
          {f'<div class="note-block"><b>Reviewer note:</b> {v.get("acmg_notes")}</div>' if v.get("acmg_notes") else ''}
        </div>
        """

    if not variant_html:
        variant_html = '<p style="color:#94a3b8;font-style:italic;">No actionable variants identified.</p>'

    body = f"""
    {qc_html}
    {summary_html}

    <h2>Actionable Variant Details</h2>
    <p style="font-size:9px;color:#64748b;margin-bottom:8px;">
      The following variants are classified as Pathogenic, Likely Pathogenic, or have high predicted impact.
      Each entry includes the ACMG criteria that fired and the evidence behind each criterion.
    </p>
    {variant_html}
    """

    metadata_str = {k: v for k, v in metadata.items() if v}

    return _report_shell(
        title=f"Genomic Variant Report — {sample.get('name', 'Sample')}",
        subtitle=f"Analysis of {total} variants · {len(actionable)} flagged for review",
        metadata=metadata_str,
        body=body,
        footer_note="GenomicsOps · Sample Report",
    )


def generate_cohort_report_html(cohort: dict, samples: list[dict], variants: list[dict], stats: dict) -> str:
    sample_count = len(samples)

    metadata = {
        "Cohort name": cohort.get("name"),
        "Cohort ID": cohort.get("id", "")[:8] + "..." if cohort.get("id") else "",
        "Samples": str(sample_count),
        "Total variants": f"{stats.get('n_variants', 0):,}",
        "Created": str(cohort.get("created_at", ""))[:19],
    }

    counts = stats.get("classification", {})

    summary_html = f"""
    <h2>ACMG Classification Breakdown</h2>
    <table class="cards">
      <tr>
        <td><div class="label">Pathogenic</div><div class="value warn">{counts.get('pathogenic', 0)}</div></td>
        <td><div class="label">VUS</div><div class="value">{counts.get('vus', 0)}</div></td>
        <td><div class="label">Benign</div><div class="value ok">{counts.get('benign', 0)}</div></td>
        <td><div class="label">Other</div><div class="value">{counts.get('other', 0)}</div></td>
      </tr>
    </table>
    """

    gene_rows = ""
    for i, g in enumerate(stats.get("top_genes", [])[:20]):
        alt = "alt" if i % 2 == 1 else ""
        gene_rows += f"""
        <tr class="{alt}">
          <td><b>{g['gene']}</b></td>
          <td>{g['count']}</td>
          <td>{g['sample_count']}/{sample_count}</td>
          <td>{g['sample_pct']}%</td>
        </tr>
        """

    gene_html = f"""
    <h2>Top Mutated Genes</h2>
    <table class="data">
      <thead>
        <tr>
          <th>Gene</th>
          <th>Variant count</th>
          <th>Samples affected</th>
          <th>Frequency</th>
        </tr>
      </thead>
      <tbody>
        {gene_rows or '<tr><td colspan="4" style="text-align:center;color:#94a3b8;">No gene data</td></tr>'}
      </tbody>
    </table>
    """

    sample_rows = ""
    for i, s in enumerate(samples):
        alt = "alt" if i % 2 == 1 else ""
        status = s.get("status", "—")
        sample_rows += f"""
        <tr class="{alt}">
          <td>{s.get('name')}</td>
          <td>{s.get('file_type', '—')}</td>
          <td>{_badge(status, 'benign' if status == 'ready' else 'other')}</td>
        </tr>
        """

    samples_html = f"""
    <h2>Samples in Cohort</h2>
    <table class="data">
      <thead>
        <tr><th>Name</th><th>Type</th><th>Status</th></tr>
      </thead>
      <tbody>{sample_rows}</tbody>
    </table>
    """

    shared = stats.get("shared_variants", [])
    shared_html = ""
    if shared:
        rows = ""
        for i, v in enumerate(shared[:20]):
            alt = "alt" if i % 2 == 1 else ""
            rows += f"""
            <tr class="{alt}">
              <td style="font-family:monospace;">{v['variant']}</td>
              <td>{v.get('gene') or '—'}</td>
              <td>{v['sample_count']}/{sample_count}</td>
              <td>{v['sample_pct']}%</td>
            </tr>
            """
        shared_html = f"""
        <h2>Variants Shared Across Cohort</h2>
        <table class="data">
          <thead>
            <tr><th>Variant</th><th>Gene</th><th>Samples</th><th>Frequency</th></tr>
          </thead>
          <tbody>{rows}</tbody>
        </table>
        """

    body = f"""
    {summary_html}
    {gene_html}
    {samples_html}
    {shared_html}
    """

    return _report_shell(
        title=f"Cohort Report — {cohort.get('name', 'Cohort')}",
        subtitle=f"{sample_count} samples · {stats.get('n_variants', 0)} variants analyzed",
        metadata=metadata,
        body=body,
        footer_note="GenomicsOps · Cohort Report",
    )


def render_pdf(html: str) -> bytes:
    from xhtml2pdf import pisa
    buf = BytesIO()
    result = pisa.CreatePDF(html, dest=buf, encoding="utf-8")
    if result.err:
        raise RuntimeError(f"xhtml2pdf failed with {result.err} error(s)")
    return buf.getvalue()


def upload_report(user_id: str, title: str, pdf_bytes: bytes) -> str:
    report_id = str(uuid.uuid4())
    path = f"{user_id}/reports/{report_id}.pdf"

    if settings.is_local:
        full = Path(settings.LOCAL_DATA_DIR) / path
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_bytes(pdf_bytes)
        return path

    supabase.storage.from_("genomic-files").upload(
        path, pdf_bytes, {"content-type": "application/pdf"}
    )
    return path

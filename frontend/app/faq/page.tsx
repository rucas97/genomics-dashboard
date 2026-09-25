"use client";
import { useState } from "react";
import Link from "next/link";

const FAQ = [
  {
    q: "What is GenomicsOps?",
    a: "A variant interpretation workbench for research labs and bioinformatics teams. It ingests VCF files, annotates variants with gene and ClinVar data, classifies them using a transparent ACMG/AMP engine, and exports clinically significant findings as FHIR R4, custom JSON, or HL7 v2.",
  },
  {
    q: "Is it a clinical tool?",
    a: "No. GenomicsOps is Research Use Only (RUO). It is not intended for clinical diagnosis, treatment, or patient management. Classifications follow ACMG/AMP 2015 guidelines applied automatically and must be verified by a qualified clinical scientist before any clinical use.",
  },
  {
    q: "How is this different from VarSome, Geneyx, or Fabric?",
    a: "Three ways: (1) Transparency — every ACMG classification shows exactly which criteria fired, the evidence behind each criterion, and what would change the call. (2) Offline-capable — runs on your machine with no cloud dependency. (3) Structured export — pushes FHIR R4 DiagnosticReport + Observations directly to your EHR/LIMS.",
  },
  {
    q: "Does it work on real VCF files?",
    a: "Yes. Tested on the GIAB NA12878 benchmark VCF (GRCh38) and multi-sample cohorts. Handles VCFs up to ~2 GB uncompressed via DuckDB streaming.",
  },
  {
    q: "What annotation sources does it use?",
    a: "MyVariant.info (aggregates ClinVar, dbSNP, SnpEff) and Ensembl VEP. Annotation is optional — in offline mode you can disable it entirely.",
  },
  {
    q: "Is my data safe?",
    a: "Yes. In offline mode no data leaves your machine and every outbound call is blocked and logged. In cloud mode each customer is isolated at the database level via Postgres Row-Level Security. Every action is logged with user attribution and timestamp.",
  },
  {
    q: "What formats can I export?",
    a: "FHIR R4 (DiagnosticReport + Observations), Custom JSON for any LIMS with a REST API, HL7 v2 ORU^R01 for legacy hospital systems, and PDF reports with per-variant ACMG evidence.",
  },
  {
    q: "Does it support cohort analysis?",
    a: "Yes. Group samples into a cohort and run PCA clustering, gene enrichment, and shared variant analysis.",
  },
  {
    q: "Can I use it offline?",
    a: "Yes. In local mode, activate an offline license and the app runs entirely on your machine with SQLite. Only variant annotation requires internet.",
  },
  {
    q: "How does licensing work?",
    a: "Three tiers: Trial (7 days), Standard, and Enterprise. Licenses are signed tokens bound to a machine fingerprint. Activation is offline — send us your fingerprint, we send back a token.",
  },
  {
    q: "Can I run it on-premise?",
    a: "Yes. The desktop build runs entirely on a lab workstation with no cloud dependency.",
  },
  {
    q: "What's the pipeline runner?",
    a: "It executes lightweight Python scripts (variant statistics, deep QC, annotation refresh). Not a Nextflow/Snakemake replacement.",
  },
  {
    q: "Who is this for?",
    a: "Research labs, bioinformatics core facilities, academic genomics groups, biotech R&D teams.",
  },
  {
    q: "Who is this NOT for?",
    a: "Clinical diagnostics, full genome alignment/calling, large-scale population genomics, or anyone needing FDA-cleared software.",
  },
];

export default function FAQPage() {
  const [open, setOpen] = useState<number | null>(0);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <div className="max-w-3xl mx-auto px-6 py-16">
        {/* Logo + back link header */}
        <div className="flex items-center justify-between mb-10">
          <Link href="/dashboard" className="flex items-center">
            <img
              src="/logo-sidebar.png"
              alt="GenomicsOps"
              className="h-10 w-auto"
            />
          </Link>
          <Link
            href="/dashboard"
            className="text-emerald-400 text-sm hover:underline"
          >
            ← Back to Dashboard
          </Link>
        </div>

        <div className="mb-10">
          <h1 className="text-4xl font-bold mb-2">Frequently Asked Questions</h1>
          <p className="text-slate-400">
            Everything you need to know about GenomicsOps.
          </p>
        </div>

        <div className="space-y-2">
          {FAQ.map((item, i) => (
            <div
              key={i}
              className="bg-slate-900 border border-slate-800 rounded-lg overflow-hidden"
            >
              <button
                onClick={() => setOpen(open === i ? null : i)}
                className="w-full text-left px-5 py-4 flex items-center justify-between hover:bg-slate-800/50"
              >
                <span className="font-medium pr-4">{item.q}</span>
                <span className="text-slate-500 text-lg shrink-0">
                  {open === i ? "−" : "+"}
                </span>
              </button>
              {open === i && (
                <div className="px-5 pb-5 text-sm text-slate-400 leading-relaxed border-t border-slate-800 pt-4">
                  {item.a}
                </div>
              )}
            </div>
          ))}
        </div>

        <div className="mt-12 pt-8 border-t border-slate-800 text-center">
          <p className="text-slate-400 text-sm mb-4">Still have questions?</p>
          <a
            href="mailto:support@genomicsops.io"
            className="inline-block bg-emerald-600 hover:bg-emerald-500 px-5 py-2 rounded text-sm font-medium"
          >
            Contact Support
          </a>
        </div>
      </div>
    </div>
  );
}

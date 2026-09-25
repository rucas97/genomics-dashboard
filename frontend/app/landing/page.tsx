"use client";
import Link from "next/link";
import { useState } from "react";

const FEATURES = [
  {
    title: "Transparent ACMG classification",
    body: "Every classification shows exactly which criteria fired, the evidence behind each one, and what would change the call. Add or remove criteria and watch the classification recompute in real time.",
  },
  {
    title: "What-if simulator",
    body: "Ask 'what would make this VUS pathogenic?' and see the answer immediately. Single-criterion upgrades are one click away.",
  },
  {
    title: "Fully auditable",
    body: "Every action logged with user attribution and timestamp. Full provenance for every classification: engine version, rule set, evidence snapshot hash.",
  },
  {
    title: "Offline-capable",
    body: "Runs on your machine with no cloud dependency. In offline mode, every outbound network call is blocked at the application layer and audited.",
  },
  {
    title: "Structured export",
    body: "FHIR R4 DiagnosticReport + Observations, custom JSON, or HL7 v2 ORU^R01. Pushes directly to your EHR/LIMS — not a PDF you copy-paste.",
  },
  {
    title: "Cohort analysis",
    body: "Multi-sample PCA clustering, gene enrichment, and shared variant analysis. Find the mutations that matter across a cohort.",
  },
];

const PLANS = [
  {
    id: "trial",
    name: "Trial",
    tagline: "7 days, full access",
    features: [
      "Variant annotation",
      "ACMG classification",
      "FHIR / JSON / HL7 export",
      "Up to 5 samples",
    ],
    color: "border-amber-700",
  },
  {
    id: "standard",
    name: "Standard",
    tagline: "For individual researchers and small labs",
    features: [
      "Everything in Trial",
      "Unlimited samples",
      "Multi-user access",
      "PDF reports",
      "Priority support",
    ],
    color: "border-emerald-700",
    featured: true,
  },
  {
    id: "enterprise",
    name: "Enterprise",
    tagline: "For labs with integration and compliance needs",
    features: [
      "Everything in Standard",
      "Full network access",
      "Custom integrations (LIMS, EHR)",
      "On-prem deployment",
      "Dedicated support",
    ],
    color: "border-purple-700",
  },
];

const FAQ_PREVIEW = [
  {
    q: "Is it a clinical tool?",
    a: "No. GenomicsOps is Research Use Only (RUO). Classifications must be verified by a qualified clinical scientist before any clinical use.",
  },
  {
    q: "Does it work on real VCF files?",
    a: "Yes. Tested on the GIAB NA12878 benchmark VCF and multi-sample cohorts. Handles VCFs up to ~2 GB uncompressed via DuckDB streaming.",
  },
  {
    q: "Can I use it offline?",
    a: "Yes. In local mode the app runs entirely on your machine with SQLite. Only optional variant annotation requires internet.",
  },
  {
    q: "What formats can I export?",
    a: "FHIR R4, custom JSON, HL7 v2 ORU^R01, and clinical-style PDF reports with per-variant ACMG evidence.",
  },
];

export default function LandingPage() {
  const [openFaq, setOpenFaq] = useState<number | null>(0);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      {/* Nav */}
      <nav className="border-b border-slate-800 px-6 py-4">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <Link href="/landing" className="flex items-center">
            <img
              src="/logo-sidebar.png"
              alt="GenomicsOps"
              className="h-10 w-auto"
            />
          </Link>
          <div className="flex items-center gap-6 text-sm">
            <a href="#features" className="text-slate-400 hover:text-slate-200">
              Features
            </a>
            <a href="#plans" className="text-slate-400 hover:text-slate-200">
              Plans
            </a>
            <Link href="/faq" className="text-slate-400 hover:text-slate-200">
              FAQ
            </Link>
            <a
              href="mailto:support@genomicsops.io?subject=GenomicsOps%20Beta%20Request"
              className="bg-emerald-600 hover:bg-emerald-500 px-4 py-2 rounded font-medium"
            >
              Request Beta
            </a>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="px-6 py-24">
        <div className="max-w-4xl mx-auto text-center">
          <div className="inline-block text-[10px] uppercase tracking-wider text-amber-500 border border-amber-900 bg-amber-950/50 px-3 py-1 rounded-full mb-6">
            Research Use Only
          </div>
          <h1 className="text-5xl md:text-6xl font-bold mb-6 leading-tight">
            Variant interpretation
            <br />
            <span className="text-emerald-400">that shows its work.</span>
          </h1>
          <p className="text-lg text-slate-400 max-w-2xl mx-auto mb-10 leading-relaxed">
            A variant interpretation workbench for research labs and bioinformatics
            teams. ACMG classifications you can audit, reproduce, and challenge —
            with a full evidence trail for every call.
          </p>
          <div className="flex gap-3 justify-center flex-wrap">
            <a
              href="mailto:support@genomicsops.io?subject=GenomicsOps%20Beta%20Request"
              className="bg-emerald-600 hover:bg-emerald-500 px-6 py-3 rounded-lg font-medium"
            >
              Request Beta Access
            </a>
            <Link
              href="/faq"
              className="bg-slate-900 hover:bg-slate-800 border border-slate-800 px-6 py-3 rounded-lg font-medium"
            >
              Read the FAQ
            </Link>
          </div>
        </div>
      </section>

      {/* Problem statement */}
      <section className="px-6 py-16 border-t border-slate-800">
        <div className="max-w-4xl mx-auto text-center">
          <p className="text-slate-400 text-lg leading-relaxed">
            Variant interpretation tools treat classification as a black box.
            You get an answer — <span className="text-slate-200">Pathogenic</span> — but
            you can&apos;t see the reasoning, can&apos;t reproduce it six months later, and
            can&apos;t defend it to a reviewer.
          </p>
          <p className="text-slate-200 text-lg leading-relaxed mt-6 font-medium">
            GenomicsOps shows every step.
          </p>
        </div>
      </section>

      {/* Features */}
      <section id="features" className="px-6 py-24 border-t border-slate-800">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold mb-4">
              Everything you need. Nothing you don&apos;t.
            </h2>
            <p className="text-slate-400 max-w-2xl mx-auto">
              Built for research labs that need to trust their tools.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {FEATURES.map((f) => (
              <div
                key={f.title}
                className="bg-slate-900 border border-slate-800 rounded-lg p-6 hover:border-slate-700 transition"
              >
                <h3 className="text-lg font-semibold mb-3 text-emerald-400">
                  {f.title}
                </h3>
                <p className="text-sm text-slate-400 leading-relaxed">
                  {f.body}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Screenshots placeholder */}
      <section className="px-6 py-24 border-t border-slate-800">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-3xl md:text-4xl font-bold mb-4">
              See it in action
            </h2>
            <p className="text-slate-400">
              Screenshots coming soon — request beta access to see a live demo.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="bg-slate-900 border border-slate-800 rounded-lg aspect-video flex items-center justify-center">
              <div className="text-center">
                <div className="text-slate-600 text-sm mb-2">
                  ACMG Workbench
                </div>
                <div className="text-slate-700 text-xs">
                  Evidence panel with criteria and what-if simulator
                </div>
              </div>
            </div>
            <div className="bg-slate-900 border border-slate-800 rounded-lg aspect-video flex items-center justify-center">
              <div className="text-center">
                <div className="text-slate-600 text-sm mb-2">
                  Cohort PCA
                </div>
                <div className="text-slate-700 text-xs">
                  Multi-sample clustering and gene enrichment
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Plans */}
      <section id="plans" className="px-6 py-24 border-t border-slate-800">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold mb-4">
              Plans for every lab
            </h2>
            <p className="text-slate-400">
              Start with a 7-day trial. Upgrade when you&apos;re ready.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {PLANS.map((p) => (
              <div
                key={p.id}
                className={`bg-slate-900 border-2 rounded-lg p-6 ${p.color} ${
                  p.featured ? "md:scale-105 shadow-xl" : ""
                }`}
              >
                {p.featured && (
                  <div className="text-[10px] uppercase tracking-wider text-emerald-400 mb-3 font-semibold">
                    Most popular
                  </div>
                )}
                <div className="text-2xl font-bold mb-2">{p.name}</div>
                <div className="text-sm text-emerald-400 mb-6">
                  {p.tagline}
                </div>
                <ul className="text-sm text-slate-400 space-y-2.5 mb-6">
                  {p.features.map((f) => (
                    <li key={f} className="flex items-start gap-2">
                      <span className="text-emerald-400 shrink-0">✓</span>
                      <span>{f}</span>
                    </li>
                  ))}
                </ul>
                <a
                  href={`mailto:sales@genomicsops.io?subject=GenomicsOps%20${p.name}%20Plan`}
                  className={`block text-center py-2.5 rounded font-medium ${
                    p.featured
                      ? "bg-emerald-600 hover:bg-emerald-500"
                      : "bg-slate-800 hover:bg-slate-700"
                  }`}
                >
                  Contact for pricing
                </a>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* FAQ preview */}
      <section className="px-6 py-24 border-t border-slate-800">
        <div className="max-w-3xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-3xl md:text-4xl font-bold mb-4">
              Common questions
            </h2>
            <Link
              href="/faq"
              className="text-emerald-400 text-sm hover:underline"
            >
              See all FAQs →
            </Link>
          </div>

          <div className="space-y-2">
            {FAQ_PREVIEW.map((item, i) => (
              <div
                key={i}
                className="bg-slate-900 border border-slate-800 rounded-lg overflow-hidden"
              >
                <button
                  onClick={() => setOpenFaq(openFaq === i ? null : i)}
                  className="w-full text-left px-5 py-4 flex items-center justify-between hover:bg-slate-800/50"
                >
                  <span className="font-medium pr-4">{item.q}</span>
                  <span className="text-slate-500 text-lg shrink-0">
                    {openFaq === i ? "−" : "+"}
                  </span>
                </button>
                {openFaq === i && (
                  <div className="px-5 pb-5 text-sm text-slate-400 leading-relaxed border-t border-slate-800 pt-4">
                    {item.a}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Final CTA */}
      <section className="px-6 py-24 border-t border-slate-800">
        <div className="max-w-3xl mx-auto text-center">
          <h2 className="text-3xl md:text-4xl font-bold mb-4">
            Ready to see it?
          </h2>
          <p className="text-slate-400 mb-8">
            Request beta access and we&apos;ll send you a 7-day trial license.
          </p>
          <a
            href="mailto:support@genomicsops.io?subject=GenomicsOps%20Beta%20Request"
            className="inline-block bg-emerald-600 hover:bg-emerald-500 px-8 py-3 rounded-lg font-medium"
          >
            Request Beta Access
          </a>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-slate-800 px-6 py-12">
        <div className="max-w-6xl mx-auto">
          <div className="flex justify-between items-start flex-wrap gap-8 mb-8">
            <div>
              <img
                src="/logo-sidebar.png"
                alt="GenomicsOps"
                className="h-10 w-auto mb-3"
              />
              <p className="text-xs text-slate-500 max-w-xs">
                A variant interpretation workbench for research labs and
                bioinformatics teams.
              </p>
            </div>
            <div className="flex gap-12 text-sm">
              <div>
                <div className="text-slate-300 font-medium mb-3">Product</div>
                <div className="space-y-2">
                  <a
                    href="#features"
                    className="block text-slate-500 hover:text-slate-300"
                  >
                    Features
                  </a>
                  <a
                    href="#plans"
                    className="block text-slate-500 hover:text-slate-300"
                  >
                    Plans
                  </a>
                  <Link
                    href="/faq"
                    className="block text-slate-500 hover:text-slate-300"
                  >
                    FAQ
                  </Link>
                </div>
              </div>
              <div>
                <div className="text-slate-300 font-medium mb-3">Contact</div>
                <div className="space-y-2">
                  <a
                    href="mailto:support@genomicsops.io"
                    className="block text-slate-500 hover:text-slate-300"
                  >
                    Support
                  </a>
                  <a
                    href="mailto:sales@genomicsops.io"
                    className="block text-slate-500 hover:text-slate-300"
                  >
                    Sales
                  </a>
                  <a
                    href="mailto:security@genomicsops.io"
                    className="block text-slate-500 hover:text-slate-300"
                  >
                    Security
                  </a>
                </div>
              </div>
            </div>
          </div>
          <div className="pt-8 border-t border-slate-800 text-xs text-slate-600">
            <p className="mb-2">
              <strong className="text-amber-500">Research Use Only.</strong>{" "}
              GenomicsOps is not intended for clinical diagnosis, treatment, or
              patient management.
            </p>
            <p>© {new Date().getFullYear()} GenomicsOps. All rights reserved.</p>
          </div>
        </div>
      </footer>
    </div>
  );
}

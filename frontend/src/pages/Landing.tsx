import { Link } from "react-router-dom";
import { ShieldCheck, Upload, BookOpen, ArrowRight } from "lucide-react";

export default function Landing() {
  return (
    <div className="min-h-screen bg-soc-bg">
      <header className="border-b border-soc-border px-8 py-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded bg-gradient-to-br from-soc-accent to-soc-accentDim flex items-center justify-center text-white font-bold text-xs">
            U
          </div>
          <span className="font-bold tracking-wide">ULPF</span>
          <span className="text-2xs text-soc-textDim ml-2">SIH 2026 · PS 26156</span>
        </div>
        <Link to="/login" className="btn btn-primary">
          Sign in <ArrowRight className="w-3.5 h-3.5" />
        </Link>
      </header>
      <section className="max-w-5xl mx-auto px-8 pt-20 pb-16">
        <h1 className="text-4xl md:text-5xl font-bold tracking-tight leading-tight">
          From heterogeneous security logs to
          <span className="text-soc-accent"> one common security language.</span>
        </h1>
        <p className="mt-6 text-soc-textMuted max-w-3xl text-base leading-relaxed">
          ULPF is a vendor-agnostic log pre-processing and normalization layer. It sits
          between your security telemetry and downstream consumers (SIEM, SOC, ML, data
          lakes) and produces a single Canonical Security Event for every log.
        </p>
        <div className="mt-8 flex flex-wrap gap-3">
          <Link to="/login" className="btn btn-primary">
            <ShieldCheck className="w-4 h-4" /> Open Dashboard
          </Link>
          <Link to="/ingest" className="btn">
            <Upload className="w-4 h-4" /> Upload Logs
          </Link>
          <a href="/docs" className="btn" target="_blank" rel="noreferrer">
            <BookOpen className="w-4 h-4" /> API Documentation
          </a>
        </div>
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4 mt-16">
          {[
            ["Vendor agnostic", "JSON, JSONL, XML, CSV, RFC 5424, CEF, LEEF — detected automatically."],
            ["Lossless preservation", "Raw bytes stored before any processing, with SHA-256 integrity."],
            ["Automatic detection", "Multi-signal format detection with transparent confidence + reasons."],
            ["Canonical normalization", "Practical, OCSF-aligned CSE. Provenance for every field."],
            ["Optional enrichment", "VirusTotal, GeoIP, AbuseIPDB, OTX, RDAP, DNS, STIX/TAXII — never blocking."],
            ["Unknown-log onboarding", "Structural analysis + analyst-approved reusable mappings."],
            ["Schema drift", "Detects new vendor fields and proposes mappings for approval."],
            ["Quarantine + replay", "No event is silently dropped. Deterministic replay after correction."],
            ["Auditable by design", "Every action, evidence access, replay, and config change is logged."],
          ].map(([title, desc]) => (
            <div key={title} className="panel p-4">
              <div className="text-sm font-semibold text-soc-text">{title}</div>
              <div className="mt-1 text-xs text-soc-textMuted leading-relaxed">{desc}</div>
            </div>
          ))}
        </div>
      </section>
      <footer className="border-t border-soc-border px-8 py-4 text-2xs text-soc-textDim flex justify-between">
        <span>Team - BEETLES · Universal Log Pre-Processing Framework</span>
        <span>Defensive cybersecurity platform — no offensive tooling</span>
      </footer>
    </div>
  );
}
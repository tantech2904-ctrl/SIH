import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import {
  Compass,
  ArrowRight,
  ArrowLeft,
  X,
  LayoutDashboard,
  Radio,
  Server,
  Crosshair,
  Puzzle,
  FileSearch,
  Map,
  ScrollText,
  FlaskConical,
  CheckCircle2,
  ExternalLink,
  Target,
  Sun,
  Moon,
  PlayCircle,
  Brain,
} from "lucide-react";
import { useTheme } from "@/context/ThemeContext";

export interface TourStep {
  id: string;
  category: string;
  title: string;
  spotlightFeature: string;
  description: string;
  route: string;
  icon: React.ComponentType<{ className?: string }>;
  keyCapabilities: string[];
}

export const TOUR_STEPS: TourStep[] = [
  {
    id: "dashboard",
    category: "OPERATIONS OVERVIEW",
    title: "SOC Command Center & Triage",
    spotlightFeature: "High-Risk Event Queue & Clickable KPI Cards",
    description:
      "This is your central operational dashboard. When suspicious events occur, the Priority Triage table at the top highlights logs with risk scores of 50 and above so you can spot attacks immediately instead of sifting through noise. You can also click any stat card to jump straight into its corresponding workspace.",
    route: "/dashboard",
    icon: LayoutDashboard,
    keyCapabilities: [
      "Priority triage queue sorted by risk score",
      "Clickable metric cards that open related workspaces",
      "Live events-per-second velocity and status counters",
    ],
  },
  {
    id: "demo",
    category: "LIVE ATTACK DEMO",
    title: "One-Click Platform Simulation",
    spotlightFeature: "Simulated Attack Scenarios & Live Alert Cascade",
    description:
      "Click the 'Run Demo' button at the top of the dashboard to test the platform. It fires 11 real-world attack scenarios through the pipeline in seconds, including SSH brute force, SQL injection, port scans, and malware hashes. The dashboard counters update live, popups guide you to triggered alerts, and high-risk events appear instantly in your queue. Everything runs inside Docker without needing external tools or network access.",
    route: "/dashboard",
    icon: PlayCircle,
    keyCapabilities: [
      "11 realistic attack scenarios including brute force, SQLi, port scans, and malware",
      "Real-time toast notifications that link directly to generated alerts",
      "Self-contained in Docker, ready for evaluation without external dependencies",
    ],
  },
  {
    id: "live",
    category: "STREAMING LOGS",
    title: "Live Stream Telemetry",
    spotlightFeature: "Real-Time Event Stream with Raw vs Normalized Comparison",
    description:
      "Watch logs arrive in real time over Server-Sent Events (SSE). Each event shows its original raw payload right alongside its normalized Canonical Security Event (CSE) fields. If you want to collect logs from your local Windows machine, the host connector can stream your Security and System logs directly into this feed. During presentations, clicking 'Run Demo' also streams events here automatically.",
    route: "/telemetry?tab=live",
    icon: Radio,
    keyCapabilities: [
      "Live stream with pause, resume, and keyword search",
      "Side-by-side view comparing raw text against parsed JSON",
      "Auto-reconnect if your connection drops",
    ],
  },
  {
    id: "connectors",
    category: "LOG SOURCES & AGENTS",
    title: "Host Connectors & Network Syslog",
    spotlightFeature: "Windows Event Log, Linux Journald, and UDP Syslog",
    description:
      "This section manages how endpoints send telemetry into the SIEM. We provide a lightweight Python connector that tails Windows Event Logs (Security, System, Application) and Linux systemd journals. It remembers where it left off using local bookmarking and buffers events on disk if the network is interrupted. The backend also listens on UDP port 5140 for standard Syslog traffic from firewalls and routers.",
    route: "/telemetry?tab=connectors",
    icon: Server,
    keyCapabilities: [
      "Windows Event Log collector with bookmarking and forward-only timestamps",
      "Built-in UDP Syslog listener on port 5140 for network appliances",
      "Local disk spooling so no logs get lost during network drops",
      "Runs directly on your host machine to access native OS APIs",
    ],
  },
  {
    id: "explorer",
    category: "LOG DISCOVERY & DATASETS",
    title: "Event Explorer & ML Dataset Export",
    spotlightFeature: "Multi-Field Querying and Supervised ML Dataset Exports",
    description:
      "Explore normalized logs across IP addresses, event types, severity levels, and risk scores. If you are building or fine-tuning machine learning models, click 'Export ML Dataset' to download up to 10,000 events in JSONL, CSV, or JSON format. Every exported row includes pre-labeled features like binary threat tags, risk scores, and standardized schema tokens ready for Scikit-Learn, PyTorch, or Pandas.",
    route: "/discovery?tab=explorer",
    icon: Brain,
    keyCapabilities: [
      "Filter by source and destination IP, event type, severity, and risk level",
      "Export clean ML training datasets in JSONL, CSV, or JSON up to 10,000 rows",
      "Includes target threat labels, risk ratings, and normalized feature fields",
      "Quick reset button to clear all search filters and reload fresh logs",
    ],
  },
  {
    id: "format",
    category: "LOG DISCOVERY & PARSING",
    title: "Format Auto-Detection",
    spotlightFeature: "Automatic Recognition of Unfamiliar Log Formats",
    description:
      "When onboarding logs from new or proprietary systems, paste a sample line here. The engine inspects structural markers, delimiters, and headers to identify whether the payload is JSON, XML, Syslog (RFC 3164/5424), Apache, CEF, or CSV, giving you a confidence score for each match.",
    route: "/discovery?tab=format",
    icon: Crosshair,
    keyCapabilities: [
      "Detects JSON, XML, Syslog, Apache, CEF, and CSV automatically",
      "Provides confidence scores based on structural patterns and delimiters",
      "Helps you choose or create the right parser before setting up a pipeline",
    ],
  },
  {
    id: "parsers",
    category: "PARSER MANAGEMENT",
    title: "Parsers & Plug-and-Play Field Mappings",
    spotlightFeature: "Custom Field Mapping into Canonical Security Schema",
    description:
      "Manage the rules that turn messy vendor logs into clean, structured Canonical Security Events. You can browse both built-in and user-defined parsers, see their exact field mappings, add custom mapping transforms, or delete parsers you no longer need. Execution counters keep track of parse successes and errors in real time.",
    route: "/pipeline?tab=parsers",
    icon: Puzzle,
    keyCapabilities: [
      "Inspect and edit field mappings for both built-in and custom parsers",
      "Plug-and-play form to add new parsers with instant field assignments",
      "Apply transformations like lowercase, uppercase, and IP normalization",
      "Delete custom parsers directly from the management interface",
    ],
  },
  {
    id: "quarantine",
    category: "ERROR HANDLING & DRIFT",
    title: "Quarantine Center & Log Replay",
    spotlightFeature: "Safe Staging for Unparsed Logs with 1-Click Replay",
    description:
      "Security platforms often drop logs when vendors quietly change their format. Our system never discards an unparsed log. Instead, failed or modified events go straight to Quarantine with detailed error explanations. Once you update your parser or mappings, you can replay those quarantined logs with one click to reprocess them into the main pipeline.",
    route: "/pipeline?tab=quarantine",
    icon: FileSearch,
    keyCapabilities: [
      "Captures failed, malformed, or drifting logs without dropping data",
      "Side-by-side inspection showing exact error details and candidate parsers",
      "One-click replay to reprocess quarantined logs through updated rules",
    ],
  },
  {
    id: "attck",
    category: "THREAT DETECTION",
    title: "MITRE ATT&CK Matrix & Threat Intel",
    spotlightFeature: "Live Heatmap of Adversary Tactics and Techniques",
    description:
      "See which adversary techniques are active in your environment. As correlation rules trigger on incoming events, this heatmap highlights matching tactics across Initial Access, Execution, Persistence, Privilege Escalation, and Exfiltration. You can click any active tactic to inspect the underlying alerts and IP reputations.",
    route: "/detection?tab=attck",
    icon: Map,
    keyCapabilities: [
      "Visual matrix showing triggered techniques mapped to MITRE ATT&CK",
      "Click-through inspection of linked alerts and incident details",
      "External threat intelligence indicators for malicious IPs and domains",
    ],
  },
  {
    id: "evidence",
    category: "FORENSICS & AUDITING",
    title: "Cryptographic Chain of Custody",
    spotlightFeature: "Tamper-Evident Storage and SHA-256 Hash Ledger",
    description:
      "For incident response and legal audits, log integrity is critical. The moment raw events arrive, the system computes an initial SHA-256 hash before any normalization takes place. Logs are stored in an append-only ledger where each entry references the previous hash, creating a cryptographic proof that records have not been altered or deleted.",
    route: "/evidence?tab=evidence",
    icon: ScrollText,
    keyCapabilities: [
      "Computes SHA-256 hash at ingestion before normalization",
      "Cryptographic hash chain proves no records were edited or removed",
      "One-click integrity verification to confirm the audit chain is valid",
    ],
  },
  {
    id: "testlab",
    category: "TESTING & VALIDATION",
    title: "Attack Simulator & Test Lab",
    spotlightFeature: "Interactive Breach Emulation Scenarios",
    description:
      "Validate your detection rules and pipeline without needing a separate penetration testing rig. From here, you can trigger individual scenarios like SSH brute force, port scans, ransomware encryption patterns, and SQL injections, then watch how the pipeline normalizes the logs and raises alerts in real time.",
    route: "/platform?tab=testlab",
    icon: FlaskConical,
    keyCapabilities: [
      "Run realistic attack simulations on demand",
      "Verify that correlation rules trigger alerts accurately",
      "Safe and repeatable testing environment built right into the platform",
    ],
  },
];

export function SiteTour({
  isOpen,
  onClose,
}: {
  isOpen: boolean;
  onClose: () => void;
}) {
  const [currentStep, setCurrentStep] = useState(0);
  const { effectiveTheme, toggleTheme } = useTheme();
  const navigate = useNavigate();

  useEffect(() => {
    if (isOpen) {
      setCurrentStep(0);
      navigate(TOUR_STEPS[0].route);
    }
  }, [isOpen]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!isOpen) return;
      if (e.key === "Escape") onClose();
      if (e.key === "ArrowRight") handleNext();
      if (e.key === "ArrowLeft") handlePrev();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, currentStep]);

  if (!isOpen) return null;

  const step = TOUR_STEPS[currentStep];
  const IconComponent = step.icon;
  const isLast = currentStep === TOUR_STEPS.length - 1;

  const handleNext = () => {
    if (isLast) {
      localStorage.setItem("ulpf.tour_completed", "true");
      onClose();
    } else {
      const nextIdx = currentStep + 1;
      setCurrentStep(nextIdx);
      navigate(TOUR_STEPS[nextIdx].route);
    }
  };

  const handlePrev = () => {
    if (currentStep > 0) {
      const prevIdx = currentStep - 1;
      setCurrentStep(prevIdx);
      navigate(TOUR_STEPS[prevIdx].route);
    }
  };

  const handleJump = () => {
    navigate(step.route);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-150">
      <div className="relative w-full max-w-2xl overflow-hidden rounded-3xl border border-soc-border bg-soc-panel shadow-2xl transition-all duration-300">
        {/* Top iOS/One UI Accent Ribbon */}
        <div className="absolute top-0 left-0 right-0 h-1.5 bg-gradient-to-r from-soc-accent via-sky-500 to-indigo-600" />

        {/* Header Bar */}
        <div className="flex items-center justify-between border-b border-soc-border px-6 py-4 bg-soc-panelAlt/50">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-soc-accent/15 border border-soc-accent/30 text-soc-accent shadow-sm">
              <Compass className="h-5 w-5 animate-pulse" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold uppercase tracking-[0.2em] text-soc-accent">
                  Interactive Platform Guide
                </span>
                <span className="text-[10px] font-mono text-soc-textDim font-bold">
                  {currentStep + 1} of {TOUR_STEPS.length}
                </span>
              </div>
              <div className="text-xs text-soc-textDim font-medium">
                {step.category}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={toggleTheme}
              type="button"
              className="inline-flex h-8 w-8 items-center justify-center rounded-xl border border-soc-border bg-soc-panel hover:border-soc-accent text-soc-text transition"
              title="Toggle Light / Dark Mode"
            >
              {effectiveTheme === "dark" ? (
                <Sun className="h-4 w-4 text-amber-400" />
              ) : (
                <Moon className="h-4 w-4 text-sky-500" />
              )}
            </button>

            <button
              onClick={onClose}
              type="button"
              className="rounded-xl p-1.5 text-soc-textDim hover:bg-soc-panel hover:text-soc-text transition"
              title="Exit Guide (Esc)"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
        </div>

        {/* Body Content */}
        <div key={step.id} className="p-6 sm:p-7 space-y-4 animate-in fade-in slide-in-from-right-4 duration-200">
          <div className="flex items-start gap-4">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-gradient-to-br from-soc-accent/20 to-soc-panelAlt border border-soc-accent/30 text-soc-accent shadow-md">
              <IconComponent className="h-6 w-6" />
            </div>
            <div className="min-w-0">
              <h3 className="text-xl font-extrabold text-soc-text tracking-tight">
                {step.title}
              </h3>
              <div className="flex items-center gap-1.5 mt-1">
                <Target className="h-3.5 w-3.5 text-soc-accent shrink-0" />
                <span className="text-xs font-bold text-soc-accent">
                  Spotlight: {step.spotlightFeature}
                </span>
              </div>
            </div>
          </div>

          <p className="text-xs sm:text-sm leading-relaxed text-soc-textMuted font-normal">
            {step.description}
          </p>

          {/* Key Capabilities */}
          <div className="space-y-2 rounded-2xl border border-soc-border bg-soc-panelAlt/60 p-3.5">
            <div className="text-[10px] font-bold uppercase tracking-[0.2em] text-soc-textDim">
              Key Capabilities on this Page
            </div>
            <div className="grid grid-cols-1 gap-1.5">
              {step.keyCapabilities.map((c, i) => (
                <div key={i} className="flex items-center gap-2 text-xs text-soc-text">
                  <CheckCircle2 className="h-3.5 w-3.5 shrink-0 text-emerald-500" />
                  <span className="truncate">{c}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Dots Indicator */}
          <div className="flex items-center justify-between pt-1">
            <div className="flex items-center gap-1.5 overflow-x-auto no-scrollbar py-1">
              {TOUR_STEPS.map((s, idx) => (
                <button
                  key={s.id}
                  type="button"
                  onClick={() => {
                    setCurrentStep(idx);
                    navigate(TOUR_STEPS[idx].route);
                  }}
                  className={`h-2 rounded-full transition-all duration-300 ${
                    idx === currentStep
                      ? "w-7 bg-soc-accent shadow-sm"
                      : "w-2 bg-soc-borderStrong/60 hover:bg-soc-accent/50"
                  }`}
                  aria-label={`Jump to step ${idx + 1}`}
                />
              ))}
            </div>

            <button
              onClick={handleJump}
              type="button"
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-soc-accent/40 bg-soc-accent/10 hover:bg-soc-accent/20 text-xs text-soc-accent font-bold transition shadow-sm whitespace-nowrap"
            >
              <span>Explore this Tab</span>
              <ExternalLink className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>

        {/* Footer Navigation */}
        <div className="flex items-center justify-between border-t border-soc-border bg-soc-panelAlt/50 px-6 py-4">
          <button
            onClick={onClose}
            type="button"
            className="text-xs font-semibold text-soc-textDim hover:text-soc-text transition"
          >
            Skip Tour
          </button>

          <div className="flex items-center gap-2.5">
            {currentStep > 0 && (
              <button
                onClick={handlePrev}
                type="button"
                className="btn rounded-xl !px-3.5 !py-2 text-xs font-medium"
              >
                <ArrowLeft className="h-3.5 w-3.5" /> Back
              </button>
            )}
            <button
              onClick={handleNext}
              type="button"
              className="btn btn-primary rounded-xl !px-5 !py-2 text-xs font-bold shadow-md"
            >
              {isLast ? (
                <>Finish Guide</>
              ) : (
                <>
                  Next Step <ArrowRight className="h-3.5 w-3.5" />
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

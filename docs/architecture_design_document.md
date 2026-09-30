# ULPF SecOps: Architecture Design Document (ADD)
**Project Title**: Unified Log Processing Framework & SIEM  
**Team**: Team BEETLES | **Event**: Smart India Hackathon (SIH)  
**Target Specifications**: 2-Page High-Density Technical Reference Document  

---

## 1. Executive Summary & Design Principles

Modern Security Operations Centers (SOCs) face four critical bottlenecks: log format heterogeneity, schema drift, fragmented threat correlation, and the risk of post-incident forensic evidence tampering. 

**ULPF SecOps** is an enterprise-grade, high-throughput log ingestion and correlation framework designed to solve these challenges. Built on a microservices architecture, ULPF ingests telemetry from diverse operating systems, devices, and clouds, normalizes disparate formats into an extensible **Canonical Security Event (CSE)** schema, detects multi-stage threats using the **MITRE ATT&CK matrix**, and guarantees forensic immutability via **SHA-256 hash-chained WORM (Write Once, Read Many) storage** with **zero-leakage multi-tenant sandboxing**.

### Core Architectural Tenets
1. **Format Agnosticism**: Real-time parsing of structured and unstructured logs (Syslog RFC 3164/5424, Windows EVTX, CEF, LEEF, JSON, CSV).
2. **Deterministic Normalization**: Conversion to CSE without dropping raw source fidelity.
3. **Sub-Second Correlation**: Stream processing mapped to MITRE ATT&CK tactics and techniques.
4. **Court-Admissible Forensics**: Mathematical integrity verification through chained cryptographic hashing.
5. **Multi-Tenant Isolation**: Strict compartmentalization of telemetry, alerts, and audit chains across teams.

---

## 2. System Architecture & Component Model

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                          DATA PRODUCERS                                                │
│  [Windows EventLog]        [Linux Journald / Syslog]        [macOS Unified Log]      [Network / Clouds] │
└─────────────────┬──────────────────────┬────────────────────────────┬────────────────────────┬─────────┘
                  │                      │                            │                        │
                  ▼                      ▼                            ▼                        ▼
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                   LAYER 1: INGESTION & ADAPTER LAYER                                   │
│  • REST API Ingestion Endpoints (`/api/v1/events/ingest`)      • UDP/Syslog Listener (Port 5140)       │
│  • Native Cross-Platform OS Connectors (Bookmark tailing, local queue buffer, exponential backoff)    │
└───────────────────────────────────────────────────┬────────────────────────────────────────────────────┘
                                                    │
                                                    ▼
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              LAYER 2: NORMALIZATION & PARSER ENGINE (CSE)                              │
│  • Auto-Format Detection (Regex, Magic Byte, Delimiter Analysis)                                       │
│  • CSE Mapping: timestamp, event_type, severity, src/dst ip:port, user, process, hashes, mitre_tags   │
│  • Schema Drift Detection & Quarantine Queue for Malformed Telemetry                                  │
└─────────────────────────┬──────────────────────────────────────────────────────────┬───────────────────┘
                          │                                                          │
                          ▼                                                          ▼
┌───────────────────────────────────────────────────────┐  ┌─────────────────────────────────────────────┐
│       LAYER 3: MITRE ATT&CK CORRELATION ENGINE        │  │      LAYER 4: FORENSIC EVIDENCE & WORM       │
│  • Sliding-Window Rule Engine (Threshold & Sequence)  │  │  • Raw Payload Preservation in S3/MinIO WORM│
│  • Threat Intel Enrichment (VirusTotal, AbuseIPDB)    │  │  • SHA-256 Hash Chained Audit Ledger        │
│  • Automated Incident Escalation & MITRE Heatmaps     │  │  • Per-Tenant Genesis Anchors & Verification│
└─────────────────────────┬─────────────────────────────┘  └──────────────────────────────┬──────────────┘
                          │                                                               │
                          ▼                                                               ▼
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                           LAYER 5: DATA PERSISTENCE & MULTI-TENANT BUS                                 │
│  • PostgreSQL 16 (Tenant-Scoped Relational Store)       • Redis 7 (Pub/Sub & SSE Live Broadcast)       │
│  • Celery Workers (Async Normalization & Bulk Flush)    • MinIO / S3 (Immutable Evidence Buckets)       │
└───────────────────────────────────────────────────┬────────────────────────────────────────────────────┘
                                                    │
                                                    ▼
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                   LAYER 6: CONSUMPTION & PRESENTATION                                  │
│  • React 18 SPA (Tailwind CSS, Vite, Lucide HUD)        • Role-Based Access Control (Admin/Analyst/Aud)│
│  • Real-Time SSE Log Stream HUD                        • Interactive MITRE Matrix & Attack Simulator   │
└────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Data Processing Lifecycle & Pipeline

```
[Raw Log] ──► [Connector / API] ──► [Format Detection] ──► [CSE Normalizer] ──► [Hash & WORM Commit]
                                                                   │
                                                                   ├──► [MITRE Correlation Engine] ──► [Incident Alert]
                                                                   │
                                                                   └──► [Redis Pub/Sub] ──► [SSE Dashboard Stream]
```

1. **Collection**: Connectors tail system channels using stateful bookmarks (`.ulpf-connector/bookmarks.json`), batching records into local disk-backed buffers before TLS transmission to the backend.
2. **Identification & Parsing**: Payload enters the parser pipeline. Header heuristics classify syntax (e.g., `<PRI>` prefix for Syslog, `CEF:0` headers, or JSON object keys). 
3. **Canonical Normalization**: Standardized fields are extracted into the **Canonical Security Event (CSE)** model. Unmapped fields are preserved inside `metadata: jsonb` to prevent forensic data loss.
4. **Forensic Hashing & WORM Storage**: The raw payload is signed with SHA-256 and committed to MinIO object storage with immutability retention rules.
5. **Correlation & Threat Detection**: The event evaluates against active detection rules (e.g., T1110 Brute Force: $\ge 5$ failed authentications within 60s for the same user).
6. **Live Distribution**: Broadcasted via Redis Pub/Sub to Server-Sent Events (SSE) subscribers for instant SOC visibility.

---

## 4. Cryptographic Chain of Custody & Tamper-Evident Architecture

To prevent internal threat actors or compromised administrators from altering log history, ULPF employs an **Independent Tenant-Chained Cryptographic Audit Ledger**:

$$\text{IntegrityHash}_n = \text{SHA-256}\Big(\text{seq}_n \parallel \text{timestamp}_n \parallel \text{tenant\_id} \parallel \text{action} \parallel \text{payload\_digest} \parallel \text{IntegrityHash}_{n-1}\Big)$$

```
┌──────────────────────┐       ┌──────────────────────┐       ┌──────────────────────┐
│  Genesis Block (n=0) │       │  Audit Entry (n=1)   │       │  Audit Entry (n=2)   │
│  prev_hash = ""      │◄──────┤  prev_hash = Hash(0) │◄──────┤  prev_hash = Hash(1) │
│  hash = SHA256(...)  │       │  hash = SHA256(...)  │       │  hash = SHA256(...)  │
└──────────────────────┘       └──────────────────────┘       └──────────────────────┘
```

- **Per-Tenant Genesis Anchoring**: Each team workspace initializes with an independent cryptographic anchor (`prev_hash=""`). Transactions across different tenants are strictly isolated, preventing inter-tenant chain breaks.
- **Verification Engine**: The auditor can execute mathematical verification across the entire database or single tenant partition. If any record, sequence ID, or timestamp is modified or deleted, the computed hash mismatches `prev_hash`, pinpointing the exact corrupted block.

---

## 5. Multi-Tenancy & Role-Based Access Control (RBAC)

ULPF implements a **Shared-Database, Tenant-Partitioned Isolation Model**:
- **Data Isolation**: All primary database models (`Event`, `Alert`, `Incident`, `AuditLog`, `Connector`) inherit a mandatory `tenant_id` foreign key. Query interceptors enforce tenant boundaries at the ORM layer, preventing unauthorized cross-tenant data access.
- **Dynamic Collaboration**: When a user registers with an existing workspace identifier, the system automatically binds them to that workspace sandbox.
- **RBAC Matrix**:

| Capability | Platform Admin | Workspace Admin | SOC Analyst | Compliance Auditor |
|---|:---:|:---:|:---:|:---:|
| Ingest & Stream Logs | ✅ | ✅ | ✅ | ❌ |
| Triage Alerts & Incidents | ✅ | ✅ | ✅ | 👁️ (Read Only) |
| Configure Correlation Rules | ✅ | ✅ | 👁️ (Read Only) | ❌ |
| Run Threat Simulations | ✅ | ✅ | ❌ | ❌ |
| Inspect Audit Ledger | ✅ | ✅ | ❌ | ✅ |
| Verify Cryptographic Chain | ✅ | ✅ | ❌ | ✅ |

---

## 6. Technical Stack & Deployment Matrix

| Tier | Component | Technology Selection | Rationale |
|---|---|---|---|
| **Frontend** | Dashboard & HUD | React 18, TypeScript, Tailwind CSS, Vite | Fast client rendering, sub-100ms dashboard refreshes, responsive dark SOC theme. |
| **API Backend** | REST & SSE Layer | FastAPI (Python 3.11), Pydantic v2 | High concurrency async I/O, native OpenAPI 3.1 generation, low memory overhead. |
| **Relational DB** | Metadata & Query | PostgreSQL 16 (SQLAlchemy 2.0 Async) | ACID compliance, JSONB indexing for unconstrained metadata, robust partitioning. |
| **Message Broker**| Ingestion & Pub/Sub | Redis 7 + Celery Workers | Microsecond event buffering, reliable Celery task execution, low-latency SSE fanout. |
| **Evidence Store**| Immutable Archive | MinIO / S3 API Compatible | S3-compliant WORM object storage for long-term retention and legal compliance. |
| **Host Agents**   | System Log Tailer | Python 3 native / Win32 API / Journald | Cross-platform, zero third-party agent dependencies, auto-bookmarking recovery. |

### Deployment Models
1. **One-Click Local Stack**: Automated orchestration via `start_ulpf.bat` (Windows) and `start_ulpf.sh` (Linux/macOS) with self-healing dependency verification.
2. **Containerized Production**: Multi-stage Docker Compose microservices stack with isolated network bridges.
3. **Native Standalone (No Docker)**: Direct Python virtualenv + Node.js with embedded SQLite/PostgreSQL fallback for air-gapped environments.
4. **Cloud Sovereign Hosting**: Validated on **Oracle Cloud Infrastructure (OCI) Always Free Tier** (4 OCPU ARM Ampere A1, 24GB RAM), delivering an enterprise-ready SIEM at **₹0 cloud licensing cost**.

---
*Team BEETLES — Smart India Hackathon (SIH)*

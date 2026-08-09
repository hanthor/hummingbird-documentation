---
title: "ADR-0001: Unified Observability Stack"
weight: 10
aliases: [/l/adr-0001]
---

- **Status:** Proposed
- **Date:** 2026-07-19 (updated 2026-08-09)
- **Author:** Robert Sturla
- **Jira:** [HUM-4790][hum-4790] (Epic), [HUM-4791][hum-4791] (Design task)

## Context

Hummingbird has no single place to view the health of builds, infrastructure,
and services. Multiple disconnected monitoring and alerting implementations
exist — CloudWatch dashboards, custom forwarder Lambdas
(cloudwatch-log-forwarder), ad-hoc SNS topics (hummingbird-events-topic),
and per-service custom dashboards. Workloads span multiple clusters (MPP,
ITUP.stable) with no cross-cluster visibility. This creates blind spots,
duplicated effort, and inconsistent alerting behaviour.

One standardised observability stack is needed. No duplication. One toolchain,
used everywhere, federated across clusters from day one.

### Cluster Constraints

Hummingbird has no cluster-admin access on any cluster. All resources must
be deployed within tenant-provisioned namespaces. Operator CRDs and RBAC
grants are controlled by the cluster platform team — what is available
differs between clusters (see [Operator Availability](#operator-availability)).

This constraint drives a **hub-spoke split architecture**: the hub (MPP)
runs the full observability stack, while spoke clusters (ITUP.stable) run
lightweight collectors that forward all telemetry to the hub.

## Decision

### Stack

**Hub (MPP):**

| Signal        | Backend                                | Storage                                            |
|---------------|----------------------------------------|----------------------------------------------------|
| Metrics       | Prometheus via COO MonitoringStack CR  | gp3-csi PVC (hot) + S3 bucket (warm/cold)          |
| Logs          | Loki (standalone)                      | S3 bucket (native S3 client, manually provisioned) |
| Traces        | Tempo (standalone)                     | S3 bucket (native S3 client, manually provisioned) |
| Collection    | OpenTelemetry collectors (Deployment)  | N/A                                                |
| Visualisation | Grafana                                | N/A                                                |

**Spoke (ITUP.stable):**

| Signal        | Backend                                              | Storage |
|---------------|------------------------------------------------------|---------|
| Metrics       | OTel collector remote-writes to hub Prometheus       | N/A     |
| Logs          | ClusterLogForwarder → hub Loki                       | N/A     |
| Traces        | OTel collector forwards to hub Tempo via OTLP        | N/A     |
| Collection    | OpenTelemetry collectors (Deployment)                | N/A     |
| Visualisation | None (use hub Grafana)                               | N/A     |

Spoke clusters have no local backends. All storage, alerting, and
visualisation is centralised on the hub.

### Alerting Architecture

Grafana evaluates alert rules against all three backends. Alertmanager handles
all delivery. This gives one evaluation engine that understands metrics, logs,
and traces, and one delivery engine purpose-built for routing, dedup, grouping,
and silencing.

```text
PrometheusRules         → Alertmanager → Slack / email
Grafana alert rules     → Alertmanager → Slack / email
Application direct POST → Alertmanager → Slack / email
```

- Grafana forwards all managed alerts to MonitoringStack Alertmanager via
  `handleGrafanaManagedAlerts: true` on the Alertmanager data source.
- PrometheusRules fire natively through Alertmanager (no Grafana dependency).
- Any application can POST alerts directly to the Alertmanager API
  (`/api/v2/alerts`) — no special client library required.
- Notification appearance controlled via Alertmanager Go templates.

All alerting runs on the hub. Spoke clusters do not run Alertmanager.
This means spoke alerting depends on network connectivity to the hub —
if a spoke loses connectivity, alerts for that cluster are delayed until
the connection is restored. This is an accepted tradeoff given the
operator constraints on spoke clusters (see
[Cluster Constraints](#cluster-constraints)).

### Alert Routing

| Severity                  | Channel        |
|---------------------------|----------------|
| Critical / infrastructure | Slack + email  |
| Build / pipeline failures | Slack          |
| Informational / low       | Email digest   |

### Deployment Model

The hub runs the full observability stack. Spoke clusters run lightweight
collectors that forward all telemetry to the hub.

**Hub (MPP):**

- **Namespace:** dedicated `hummingbird--monitoring` namespace
  (tenant-provisioned)
- **Tenant-scoped:** all resources deployed in namespaces owned by
  Hummingbird, no cluster-admin dependency
- **MonitoringStack:** Prometheus + Alertmanager + Thanos Sidecar for
  alerting and metrics storage. Receives metrics from local services
  (via ServiceMonitors) and from spoke clusters (via OTel collector
  remote-write). The MonitoringStack CR is configured with
  `objectStorageConfig` to enable the Thanos Sidecar, which uploads
  TSDB blocks to S3 for long-term retention (up to 3y via tiered
  lifecycle policy). Local PVC holds 15d of hot data.
- **Thanos Store Gateway:** reads historical metric blocks from S3.
  Deployed alongside the MonitoringStack.
- **Thanos Querier:** fans out queries across live Prometheus replicas
  (hot, ≤15d) and the Store Gateway (S3, up to 3y). Grafana data
  source points to Thanos Querier, not Prometheus directly — queries
  transparently span the full retention window.
- **Cross-namespace scraping:** Prometheus scrapes services in other
  Hummingbird namespaces (e.g., `hummingbird--internal`) via
  `namespaceSelector` on MonitoringStack CR and ServiceMonitors in target
  namespaces. Network policies required.
- **Standalone Loki (Simple Scalable mode):** deployed in
  `hummingbird--monitoring`. The LokiStack operator CRD is not available
  to tenant namespaces. Loki runs three component types — write (2
  replicas for ingestion HA), read (1 replica for queries), and backend
  (1 replica for compaction and ruler). This isolates query load from
  ingestion. Loki receives logs from hub CLF and spoke CLFs. Index
  retention is set to 30d (searchable via LogQL); raw log chunks remain
  in S3 beyond 30d (recoverable but not indexed).
- **Standalone Tempo:** deployed in `hummingbird--monitoring`. The
  TempoStack operator CRD is not available to tenant namespaces. Tempo
  receives traces from hub and spoke OTel collectors.
- **Grafana:** exposed via internal Route. Dashboards are
  Git-provisioned using [Grafana Git Sync][grafana-git-sync] —
  dashboards are pulled from a Git repository on startup and UI edits
  are pushed back to Git. This makes Grafana stateless (no PVC, no
  external database), which is why a single replica is sufficient.
  Data sources are provisioned via configmaps — not editable through
  the UI. No GrafanaAdmin role is assigned — data sources and server
  configuration are managed via provisioning and Git, not the UI.
- **Authentication (phased):**
  - **Phase 1:** OpenShift OAuth. All authenticated users receive
    Viewer role. Single access tier. No external dependencies —
    available immediately.
  - **Phase 2:** Corporate OIDC (Keycloak-based). LDAP group
    membership mapped to Grafana organisations via `org_mapping`,
    enabling per-org data source isolation (e.g., metrics-only org
    for general users, full-access org for ops). Requires an OIDC
    client registration with the corporate IAM team. Migration is a
    Grafana config change — no architectural impact.

**Spoke (ITUP.stable):**

- **Namespace:** Hummingbird tenant namespace (e.g.,
  `hummingbird--factory-sandbox`)
- **OTel collector (Deployment):** scrapes local metrics via the
  [Prometheus receiver][otel-prom-receiver] and forwards to hub
  Prometheus via [Prometheus remote-write exporter][otel-prom-rw].
  Also receives OTLP traces from local applications and forwards to
  hub Tempo. Replaces ServiceMonitors (not available on spoke).
- **ClusterLogForwarder:** forwards container logs to hub Loki.
  CLF is available on spoke clusters.
- **No local Prometheus, Alertmanager, Grafana, Loki, or Tempo.**
  COO CRDs are not available to tenant namespaces on spoke clusters.
- **No local alerting.** All alerting is evaluated on the hub against
  federated data.

### AWS Lambda Services

Some Hummingbird services (e.g., container-catalog) currently run as AWS
Lambda functions. Whether Lambda remains the long-term home for these
services is under evaluation. While they remain on Lambda, observability
is provided via the [OTel Collector Lambda extension layer][otel-lambda],
which runs a lightweight OTel collector inside each Lambda and exports
metrics, logs, and traces to the OCP-based OTel collector via OTLP.

This requires a network path from Lambda to the OTel collector endpoint
on MPP. If/when these services migrate to OCP, they fall under the
standard collection paths (ServiceMonitors on hub, OTel scraping on
spoke, ClusterLogForwarder on both) with no additional plumbing.

Low-traffic utility Lambdas (SNS archivers, event forwarders) are not
worth instrumenting with OTel — monitor via CloudWatch until
decommissioned.

### Log Collection

Container stdout/stderr is forwarded to Loki via a namespaced
`ClusterLogForwarder` CR (`observability.openshift.io/v1`). This requires
no application code changes, no sidecars, and no DaemonSet — the cluster
logging operator handles collection and delivery. Logs are indexed by
namespace using `tenantKey: kubernetes.namespaceName`.

CLF is available on both hub and spoke clusters. On spoke clusters, the
CLF output target is the hub Loki endpoint (cross-cluster network path
required). On the hub, the CLF output target is the local standalone
Loki instance.

Services that need logs correlated with distributed traces can
additionally push structured logs via the OTel SDK to the OTel collector
endpoint. Both paths coexist — ClusterLogForwarder is the default, OTel
SDK is opt-in for trace correlation.

### OTel Collector

**Hub:**

- Deployed as a **Deployment** (not sidecar) in `hummingbird--monitoring`
- Applications send telemetry to
  `otel-collector.hummingbird--monitoring.svc` via OTLP
- Two default pipelines: metrics → Prometheus, traces → Tempo
- Optional third pipeline: structured logs → Loki (for services using
  OTel SDK for trace-correlated logging)
- Receives remote-write metrics and OTLP traces from spoke OTel
  collectors

**Spoke:**

- Deployed as a **Deployment** in the Hummingbird tenant namespace
- Scrapes local service metrics via the Prometheus receiver (replaces
  ServiceMonitors, which are not available on spoke)
- Forwards metrics to hub Prometheus via Prometheus remote-write
  exporter
- Receives OTLP traces from local applications and forwards to hub
  Tempo
- Optional structured logs pipeline → hub Loki

### High Availability

**Hub:**

| Component                      | Replicas | Rationale                                             |
|--------------------------------|----------|-------------------------------------------------------|
| Prometheus (MonitoringStack)   | 2        | Alerting cannot go down                               |
| Thanos Sidecar                 | 2        | One per Prometheus replica (automatic)                |
| Alertmanager (MonitoringStack) | 2        | Automatic with HA MonitoringStack                     |
| Thanos Store Gateway           | 1        | Reads S3; stateless query path, brief downtime OK     |
| Thanos Querier                 | 1        | Fans out across Prometheus replicas + Store Gateway   |
| Grafana                        | 1        | View-only; brief downtime acceptable                  |
| Loki write                     | 2        | Ingestion HA; no log loss during rolling updates      |
| Loki read                      | 1        | Query path; brief downtime acceptable                 |
| Loki backend                   | 1        | Compactor + ruler; brief downtime acceptable          |
| Tempo                          | 1        | Traces are best-effort initially                      |
| OTel collector                 | 1        | Scale up if throughput requires it                    |

**Spoke:**

| Component      | Replicas | Rationale                                              |
|----------------|----------|--------------------------------------------------------|
| OTel collector | 1        | Stateless forwarder; brief gap acceptable              |

Spoke clusters have no stateful observability components. HA concerns
are concentrated on the hub.

### Retention

| Signal  | Searchable | Archived | Rationale                                                      |
|---------|------------|----------|----------------------------------------------------------------|
| Metrics | 15d PVC    | 3y S3    | Tiered S3 lifecycle; full PromQL across all tiers              |
| Logs    | 30d S3     | 3y S3    | 30d indexed (LogQL); chunks retained unindexed beyond 30d      |
| Traces  | 7d S3      | 3y S3    | 7d searchable in Tempo; chunks retained unindexed beyond 7d    |

All three signals use tiered S3 lifecycle policies on their respective
buckets. For metrics, Thanos Store Gateway reads from all S3 storage
classes transparently — the same PromQL interface regardless of tier.
For logs and traces, data beyond the searchable window remains in S3
as raw chunks (recoverable by reindexing or direct S3 access, but not
queryable via LogQL/TraceQL).

**S3 lifecycle tiers (all buckets):**

| Tier | Age     | S3 Storage Class | Rationale                                      |
|------|---------|------------------|------------------------------------------------|
| Hot  | 0–90d   | S3 Standard      | Active queries, no retrieval fees              |
| Cool | 90d–1y  | S3 Standard-IA   | Rare ad-hoc queries, multi-AZ durability       |
| Cold | 1y–3y   | S3 One Zone-IA   | Near-never accessed, cheapest storage          |
| —    | >3y     | Deleted          | No retention requirement beyond 3 years        |

Metrics additionally use PVC (gp3-csi) for the first 15d (Prometheus
local storage), after which Thanos Sidecar uploads blocks to S3.

### Long-Term Data

Tempo is hot storage for operational debugging (7d retention). For
customer-facing dashboards and long-term analytics (e.g., CVE lifecycle
metrics), data is written to a purpose-built store (e.g., DynamoDB or
PostgreSQL) as each stage completes — not only at trace completion. This
means dashboards can show in-progress state (e.g., "RPM fixed, awaiting
image rebuild") without waiting for the full lifecycle to finish. Customer
dashboards query the long-term store, not Tempo.

### Operator Availability

CRD availability and RBAC were audited on 2026-08-09 across all three
clusters. Hummingbird has no cluster-admin access — only operator CRDs
explicitly granted to tenant namespaces are usable.

| CRD / Operator                     | Hub Prod (MPP) | Hub Pre-prod (MPP) | Spoke (ITUP.stable) |
|------------------------------------|----------------|--------------------|---------------------|
| COO (`monitoring.rhobs`)           | Full CRUD      | Full CRUD          | No access           |
| ClusterLogForwarder                | Full CRUD      | Full CRUD          | Full CRUD           |
| OTel (`opentelemetry.io`)          | Full CRUD      | Full CRUD          | Full CRUD           |
| ObservabilityAddon (ACM)           | CRUD           | CRUD               | No access           |
| UIPlugin                           | Full CRUD      | Full CRUD          | No access           |
| TempoStack (`tempo.grafana.com`)   | No access      | No access          | No access           |
| LokiStack (`loki.grafana.com`)     | No access      | No access          | No access           |

**Key constraints:**

- **COO** (MonitoringStack, ServiceMonitor, PrometheusRule, etc.) is
  available on both hub clusters but not on spoke. Spoke metrics
  collection uses the OTel collector Prometheus receiver instead.
- **Loki and Tempo operators** are not available to tenant namespaces
  on any cluster. Both are deployed as standalone instances (Helm or
  manifests) on the hub.
- **ACM ObservabilityAddon** is available on hub clusters but not on
  spoke. Federation from spoke uses OTel collector remote-write
  instead of the ACM addon.
- **ClusterLogForwarder and OTel** are available everywhere — these
  form the universal collection layer.

## Relationship to Existing Dashboard

The existing `hummingbird-dashboard` app serves two distinct roles:

1. **Data visualisation** — CVE status charts, failed release counts,
   build metrics
2. **Operational workflows** — click to rerun a failed release,
   interactive triage, actionable controls

This observability stack takes over **data collection, storage, and
visualisation** (role 1). Grafana becomes the primary place for charts,
time-series dashboards, and alert-driven visualisations. The dashboard
app retains **operational workflow features** (role 2) — interactive
actions that Grafana cannot provide.

The two systems complement each other:

- The dashboard app can embed Grafana panels (via iframe or
  [Grafana panel sharing][grafana-share]) for richer visualisation
  without reimplementing charting
- The dashboard app can query the same backends (Prometheus, Loki)
  directly for data it needs to drive workflows
- The dashboard app can consume trace data from Tempo (via API) to
  display CVE lifecycle state — e.g., tracking a CVE from detection
  through RPM fix to image rebuild — without building its own event
  tracking pipeline
- Over time, the dashboard app's own data collection pipelines
  (custom forwarders, SNS topics) are replaced by this stack — the
  dashboard app consumes data from the unified backends instead of
  maintaining parallel collection

Alerting (e.g., failed release Slack notifications) moves to
Alertmanager. The dashboard app no longer needs its own alerting path.

## What This Replaces

| Current                          | Replaced by                              |
|----------------------------------|------------------------------------------|
| CloudWatch dashboards            | Grafana dashboards                       |
| cloudwatch-log-forwarder Lambda  | OTel collector → Loki                    |
| hummingbird-events-topic (SNS)   | Alertmanager                             |
| Per-service custom dashboards    | Grafana dashboards                       |
| Dashboard app data collection    | Unified backends (Prometheus, Loki)      |
| Dashboard app alerting (Slack)   | Alertmanager                             |
| Dashboard app visualisations     | Grafana (embeddable in dashboard app)    |

The dashboard app itself is **not decommissioned** — its operational
workflow features (release reruns, interactive triage) remain. Only its
data collection and visualisation responsibilities shift to the unified
stack.

Decommissioning of replaced components is tracked as a separate story
under [HUM-4790][hum-4790]. Each component is audited before removal;
exceptions are documented.

## Future Work

- **CVE lifecycle tracing:** instrument CVE analysis, RPM build, and container
  image pipelines with OTel spans. Trace a CVE from detection → RPM fix →
  image rebuild → publish. Requires trace schema design (separate story).
- **Spoke COO access:** if COO CRDs are granted to tenant namespaces on
  spoke clusters in the future, spoke deployment can be upgraded to run a
  local MonitoringStack with local alerting — eliminating the hub dependency
  for spoke alerts.

## Alternatives Considered

### Alerting: Grafana-only vs Alertmanager-only vs hybrid

- **Alertmanager-only:** cannot alert on logs or traces.
- **Grafana-only:** less mature routing, dedup, and silencing.
- **Hybrid (chosen):** Grafana evaluates rules across all backends;
  Alertmanager handles delivery. Best of both, and applications can POST
  directly to Alertmanager without Grafana dependency.

### Storage: PVCs vs S3 for Loki/Tempo

PVCs require sizing upfront and can run out. S3 is effectively unlimited,
cheaper for log/trace workloads, and is the native storage backend for both
Loki and Tempo. S3 buckets are provisioned manually (Terraform or AWS console)
and configured in Loki/Tempo via their native S3 client settings — not via
Kubernetes StorageClass or PVC mounts. The cluster does offer an
ObjectBucketClaim provisioner (`aws-s3` StorageClass), but manual provisioning
provides more control over bucket policies, lifecycle rules, and IAM.
Prometheus uses PVCs managed by MonitoringStack (gp3-csi, COO default)
for hot data (15d). The Thanos Sidecar uploads TSDB blocks to a
separate S3 bucket with a tiered lifecycle policy (Standard → Standard-IA
→ One Zone-IA → delete at 3y), enabling SLO measurement across 30–90
day windows and long-term historical queries without increasing PVC
size.

### Logs: Sumo Logic vs Loki

Red Hat has a company-wide Sumo Logic license. However, the [Sumo Logic
Grafana plugin][sumo-plugin] requires Grafana Enterprise or Grafana Cloud —
it is not available in open-source Grafana. Since the stack deploys
open-source Grafana, Sumo Logic cannot serve as the primary log backend.
Additionally, Sumo Logic only supports Grafana alerting on aggregated log
queries — raw log alerting is not supported, which limits its usefulness
for operational alerting.

Loki integrates natively with open-source Grafana, supports full LogQL
alerting (including raw log queries), and keeps logs on-cluster with no
external dependencies.

### Spoke architecture: full stack vs collector-only

- **Full stack per cluster (original design):** each cluster runs its own
  Prometheus, Alertmanager, Loki, Tempo, and Grafana. Local alerting
  survives network partitions. Requires COO, Loki operator, and Tempo
  operator CRDs on all clusters.
- **Collector-only on spoke (chosen):** spoke runs only OTel collector and
  ClusterLogForwarder, forwarding all telemetry to the hub. Simpler spoke
  footprint, fewer operator dependencies. Tradeoff: spoke alerting depends
  on hub connectivity.
- **Why:** COO CRDs are not available to tenant namespaces on spoke
  clusters, and Loki/Tempo operator CRDs are not available on any cluster.
  The full-stack model is not achievable without cluster-admin intervention
  that is outside Hummingbird's control.

### Federation: ACM ObservabilityAddon vs OTel remote-write

- **ACM ObservabilityAddon:** automatic remote-write to hub Thanos. Zero
  plumbing on the hub side. Requires the addon CRD on spoke clusters.
- **OTel remote-write (chosen for spoke):** OTel collector on spoke uses
  the Prometheus remote-write exporter to push metrics to hub Prometheus.
  Requires configuring the remote-write endpoint and authentication.
  Used because the ObservabilityAddon CRD is not available on spoke.
- ACM ObservabilityAddon remains available on hub clusters and may be
  used for hub-to-hub federation if additional hub clusters are added.

### HA: all components vs selective

Full HA for all components doubles resource cost with marginal benefit for
view-only tools. Selective HA (Prometheus + Alertmanager only) protects the
alerting path — the only component where downtime has operational impact.

## Consequences

- Team must learn Grafana dashboarding and PromQL/LogQL basics
- Applications that want direct alerting need to know the Alertmanager API
  endpoint (hub only)
- New services on the hub must create a ServiceMonitor and optionally a
  Grafana dashboard (runbook to be provided)
- New services on spoke clusters must be scraped by the OTel collector
  Prometheus receiver (no ServiceMonitor available)
- Spoke alerting depends on hub connectivity — no local alerting on spoke
- Existing CloudWatch/SNS monitoring will be decommissioned after migration —
  teams relying on those need advance notice
- Deploying to a new hub cluster requires provisioning a MonitoringStack
  (with Thanos S3 bucket for long-term metrics), standalone Loki/Tempo,
  and Thanos Store Gateway + Querier
- Deploying to a new spoke cluster requires provisioning an OTel collector
  and ClusterLogForwarder pointing to the hub

[hum-4790]: https://redhat.atlassian.net/browse/HUM-4790
[hum-4791]: https://redhat.atlassian.net/browse/HUM-4791
[sumo-plugin]: https://grafana.com/grafana/plugins/grafana-sumologic-datasource/
[otel-lambda]: https://github.com/open-telemetry/opentelemetry-lambda
[otel-prom-receiver]: https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/main/receiver/prometheusreceiver
[otel-prom-rw]: https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/main/exporter/prometheusremotewriteexporter
[grafana-git-sync]: https://grafana.com/docs/grafana/latest/setup-grafana/configure-grafana/settings/git-sync/
[grafana-share]: https://grafana.com/docs/grafana/latest/dashboards/share-dashboards-panels/

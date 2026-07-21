---
title: "ADR-0001: Unified Observability Stack"
weight: 10
aliases: [/l/adr-0001]
---

- **Status:** Proposed
- **Date:** 2026-07-19
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

## Decision

### Stack

| Signal        | Backend                                | Storage                                            |
|---------------|----------------------------------------|----------------------------------------------------|
| Metrics       | Prometheus via COO MonitoringStack CR  | gp3-csi PVC (managed by COO)                       |
| Logs          | Loki                                   | S3 bucket (native S3 client, manually provisioned) |
| Traces        | Tempo                                  | S3 bucket (native S3 client, manually provisioned) |
| Collection    | OpenTelemetry collectors (Deployment)  | N/A                                                |
| Visualisation | Grafana                                | N/A                                                |
| Federation    | ACM ObservabilityAddon                 | Hub Thanos (managed by ACM)                        |

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

### Alert Routing

| Severity                  | Channel        |
|---------------------------|----------------|
| Critical / infrastructure | Slack + email  |
| Build / pipeline failures | Slack          |
| Informational / low       | Email digest   |

### Deployment Model

Each cluster runs its own observability stack. ACM federates metrics
across clusters to a central hub.

**Per-cluster (MPP, ITUP.stable):**

- **Namespace:** dedicated `hummingbird--monitoring` namespace
  (tenant-provisioned)
- **Tenant-scoped:** all resources deployed in namespaces owned by
  Hummingbird, no cluster-admin dependency
- **MonitoringStack:** local Prometheus + Alertmanager for per-cluster
  alerting. Alerting survives network partitions — no cross-cluster
  dependency.
- **Cross-namespace scraping:** Prometheus scrapes services in other
  Hummingbird namespaces (e.g., `hummingbird--internal`) via
  `namespaceSelector` on MonitoringStack CR and ServiceMonitors in target
  namespaces. Network policies required.
- **ACM ObservabilityAddon:** deployed in `hummingbird--internal`,
  remote-writes metrics from local Prometheus to hub Thanos. The addon
  CRD (`observability.open-cluster-management.io/v1beta1`) and CRUD
  permissions are confirmed on MPP.
- **Access:** Grafana exposed via internal Route, authenticated via OAuth
  (cluster OAuth or gitlab.com). Open-source Grafana has limited RBAC —
  in particular, data source access cannot be restricted per-dashboard
  without auth. Roles mapped from GitLab group membership using
  `role_attribute_path` (see [CKI reference implementation][cki-grafana]).
  Default mapping: project group → Viewer, editors subgroup → Editor,
  admin → GrafanaAdmin.

**Hub (ACM-managed):**

- ACM's `MultiClusterObservability` CR manages a central Thanos
  (Receive + Query) and Grafana on the hub cluster.
- Hub Grafana provides unified cross-cluster dashboards.
- Per-cluster Grafana remains for team-specific dashboards and local
  debugging.

### AWS Lambda Services

Some Hummingbird services (e.g., container-catalog) currently run as AWS
Lambda functions. Whether Lambda remains the long-term home for these
services is under evaluation. While they remain on Lambda, observability
is provided via the [OTel Collector Lambda extension layer][otel-lambda],
which runs a lightweight OTel collector inside each Lambda and exports
metrics, logs, and traces to the OCP-based OTel collector via OTLP.

This requires a network path from Lambda to the OTel collector endpoint
on MPP. If/when these services migrate to OCP, they fall under the
standard collection paths (ServiceMonitors, ClusterLogForwarder) with no
additional plumbing.

Low-traffic utility Lambdas (SNS archivers, event forwarders) are not
worth instrumenting with OTel — monitor via CloudWatch until
decommissioned.

### Log Collection

Container stdout/stderr is forwarded to Loki via a namespaced
`ClusterLogForwarder` CR (`observability.openshift.io/v1`). This requires
no application code changes, no sidecars, and no DaemonSet — the cluster
logging operator handles collection and delivery. Logs are indexed by
namespace using `tenantKey: kubernetes.namespaceName`.

Services that need logs correlated with distributed traces can
additionally push structured logs via the OTel SDK to the OTel collector
endpoint. Both paths coexist — ClusterLogForwarder is the default, OTel
SDK is opt-in for trace correlation.

### OTel Collector

- Deployed as a **Deployment** (not sidecar) in `hummingbird--monitoring`
- Applications send telemetry to
  `otel-collector.hummingbird--monitoring.svc` via OTLP
- Two default pipelines: metrics → Prometheus, traces → Tempo
- Optional third pipeline: structured logs → Loki (for services using
  OTel SDK for trace-correlated logging)

### High Availability

| Component                      | Replicas | Rationale                                             |
|--------------------------------|----------|-------------------------------------------------------|
| Prometheus (MonitoringStack)   | 2        | Alerting cannot go down                               |
| Alertmanager (MonitoringStack) | 2        | Automatic with HA MonitoringStack                     |
| Thanos Querier                 | 1        | Deduplicates across Prometheus replicas (per-cluster) |
| Grafana                        | 1        | View-only; brief downtime acceptable                  |
| Loki                           | 1        | Logs can buffer; brief gap acceptable                 |
| Tempo                          | 1        | Traces are best-effort initially                      |
| OTel collector                 | 1        | Scale up if throughput requires it                    |

### Retention

| Signal  | Retention | Rationale                                                                    |
|---------|-----------|------------------------------------------------------------------------------|
| Metrics | 15d       | MonitoringStack default; sufficient for dashboards and alerting              |
| Logs    | 14d       | Build logs are the primary use case; 2 weeks covers sprint cycles            |
| Traces  | 7d        | Operational debugging only; long-term data extracted to purpose-built store  |

### Long-Term Data

Tempo is hot storage for operational debugging (7d retention). For
customer-facing dashboards and long-term analytics (e.g., CVE lifecycle
metrics), data is written to a purpose-built store (e.g., DynamoDB or
PostgreSQL) as each stage completes — not only at trace completion. This
means dashboards can show in-progress state (e.g., "RPM fixed, awaiting
image rebuild") without waiting for the full lifecycle to finish. Customer
dashboards query the long-term store, not Tempo.

### Operator Availability

Confirmed on MPP cluster:

- **COO:** `MonitoringStack` CRD exists (`monitoring.rhobs/v1alpha1`,
  namespaced). Full CRD list: MonitoringStack, Alertmanager,
  AlertmanagerConfig, Prometheus, PrometheusAgent, PrometheusRule,
  ServiceMonitor, PodMonitor, Probe, ScrapeConfig, ThanosQuerier,
  ThanosRuler
- **ACM:** `ObservabilityAddon` CRD exists
  (`observability.open-cluster-management.io/v1beta1`, namespaced).
  Full CRUD permissions confirmed in `hummingbird--internal`.
- `oc auth can-i create monitoringstacks.monitoring.rhobs` → `yes`
- `oc auth can-i create observabilityaddons` → `yes`

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
- **Cross-cluster log/trace federation:** Loki and Tempo are per-cluster
  initially. Evaluate centralising to a shared S3-backed instance or using
  Grafana multi-datasource queries across clusters.

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
Prometheus uses PVCs managed by MonitoringStack (gp3-csi, COO default).

### Logs: Sumo Logic vs Loki

Red Hat has a company-wide Sumo Logic license. However, the [Sumo Logic
Grafana plugin][sumo-plugin] requires Grafana Enterprise or Grafana Cloud —
it is not available in open-source Grafana. Since the stack deploys
open-source Grafana in the team namespace, Sumo Logic cannot serve as the
primary log backend. Additionally, Sumo Logic only supports Grafana alerting
on aggregated log queries — raw log alerting is not supported, which limits
its usefulness for operational alerting.

Loki integrates natively with open-source Grafana, supports full LogQL
alerting (including raw log queries), and keeps logs on-cluster with no
external dependencies.

### Federation: ACM ObservabilityAddon vs COO-only Thanos

- **COO-only:** deploy MonitoringStack + ThanosQuerier on each cluster,
  manually wire Thanos Query to fan out across clusters. Full control but
  significant plumbing — network paths, TLS, service discovery all manual.
- **ACM ObservabilityAddon (chosen):** the addon already exists on managed
  clusters and remote-writes to hub Thanos automatically. Zero federation
  plumbing. Per-cluster MonitoringStack still handles local alerting. ACM
  hub Grafana provides unified cross-cluster view.

### HA: all components vs selective

Full HA for all components doubles resource cost with marginal benefit for
view-only tools. Selective HA (Prometheus + Alertmanager only) protects the
alerting path — the only component where downtime has operational impact.

## Consequences

- Team must learn Grafana dashboarding and PromQL/LogQL basics
- Applications that want direct alerting need to know the Alertmanager API
  endpoint
- New services must create a ServiceMonitor and optionally a Grafana dashboard
  (runbook to be provided)
- Existing CloudWatch/SNS monitoring will be decommissioned after migration —
  teams relying on those need advance notice
- Deploying to a new cluster requires provisioning a MonitoringStack and
  ObservabilityAddon — federation is automatic once the addon is active

[hum-4790]: https://redhat.atlassian.net/browse/HUM-4790
[hum-4791]: https://redhat.atlassian.net/browse/HUM-4791
[sumo-plugin]: https://grafana.com/grafana/plugins/grafana-sumologic-datasource/
[otel-lambda]: https://github.com/open-telemetry/opentelemetry-lambda
[cki-grafana]: https://gitlab.cee.redhat.com/cki-project/deployment-all/-/blob/main/openshift/applecrumble-grafana/10-configmap.yml.j2.d/grafana.ini?ref_type=heads#L20
[grafana-share]: https://grafana.com/docs/grafana/latest/dashboards/share-dashboards-panels/

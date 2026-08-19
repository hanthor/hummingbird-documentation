---
title: "ADR-0001: Unified Observability Stack"
weight: 10
aliases: [/l/adr-0001]
---

- **Status:** Implemented
- **Date:** 2026-07-19 (updated 2026-08-19)
- **Author:** Robert Sturla
- **Jira:** [HUM-4790][hum-4790] (Epic), [HUM-4791][hum-4791] (Design task)

## Context

Hummingbird had no single place to view the health of builds, infrastructure,
and services. Multiple disconnected monitoring and alerting implementations
existed — CloudWatch dashboards, a custom `cloudwatch-log-forwarder` Lambda,
an SNS `AlertsTopic` for consumer CloudWatch alarms, and per-service custom
dashboards. Workloads span multiple clusters with no cross-cluster visibility.
This created blind spots, duplicated effort, and inconsistent alerting
behaviour.

One standardised observability stack is needed. No duplication. One toolchain,
used everywhere, federated across clusters from day one.

Operational runbooks live in `documentation/monitoring.md` in the
[infrastructure repository][infrastructure]. This ADR records the
architecture decision.

### Cluster Constraints

Hummingbird has no cluster-admin access on any cluster. All resources must
be deployed within tenant-provisioned namespaces. Operator CRDs and RBAC
grants are controlled by the cluster platform team — what is available
differs between clusters.

This constraint drives a **hub-spoke split architecture**: the hub (MPP)
runs the backends and Grafana, while spoke clusters run lightweight
collectors that forward all telemetry to the hub.

## Decision

### Stack

**Hub (MPP, `hummingbird--monitoring-hub`):**

| Signal        | Backend                         | Storage                          |
|---------------|---------------------------------|----------------------------------|
| Metrics       | Mimir (monolithic)              | S3 via ObjectBucketClaim         |
| Logs          | Loki (monolithic)               | S3 via ObjectBucketClaim         |
| Collection    | Alloy Hub (YACE + textfile)     | N/A                              |
| Visualisation | Grafana                         | N/A                              |
| Alerting      | Mimir ruler + Alertmanager      | N/A                              |

**Spoke (every cluster with `hummingbird--monitoring`):**

| Signal        | Backend                                            | Storage |
|---------------|----------------------------------------------------|---------|
| Metrics       | Alloy `prometheus.scrape` → hub Mimir remote-write | N/A     |
| Logs          | Alloy `loki.source.kubernetes` → hub Loki          | N/A     |
| Collection    | Alloy + kube-state-metrics                         | N/A     |
| Visualisation | None (use hub Grafana)                             | N/A     |

Spoke clusters have no local backends. All storage, alerting, and
visualisation is centralised on the hub. Each spoke forwards to both the
staging and production hubs.

Distributed tracing (Tempo) is not deployed. See
[Future Work](#future-work).

### Alerting Architecture

Mimir evaluates PromQL alerting rules (ruler) and delivers notifications
through its built-in Alertmanager. Grafana is not in the evaluation path.

```text
Mimir ruler (PromQL) → Mimir Alertmanager → Slack / email
```

- Rules are Git-provisioned in the infrastructure repository and mounted
  into Mimir as a ConfigMap.
- All alerting runs on the hub. Spoke clusters do not run Alertmanager.
  Spoke alerting depends on network connectivity to the hub — if a spoke
  loses connectivity, alerts for that cluster are delayed until the
  connection is restored. This is an accepted tradeoff given the
  operator constraints on spoke clusters (see
  [Cluster Constraints](#cluster-constraints)).
- Staging Alertmanager receivers are empty (a blackhole) so staging does
  not page Slack or email.

### Alert Routing

| Severity        | Channel                                   |
|-----------------|-------------------------------------------|
| `critical`      | Slack `#hummingbird-infra-alerts` + email |
| `info`          | Slack `#hummingbird-infra-alerts`         |
| everything else | Slack `#hummingbird-infra-alerts` + email |

Email goes to `hummingbird-alerts@redhat.com`. Production only; staging
is a blackhole.

### Deployment Model

The hub runs the backends, Grafana, and Alloy Hub. Spoke clusters run
Alloy and kube-state-metrics.

**Hub (MPP):**

- **Namespace:** dedicated `hummingbird--monitoring-hub` namespace
  (tenant-provisioned)
- **Tenant-scoped:** all resources deployed in namespaces owned by
  Hummingbird, no cluster-admin dependency
- **Mimir (monolithic):** accepts Prometheus remote-write from spoke
  Alloy and Alloy Hub, stores TSDB blocks in S3, serves PromQL, and
  runs the ruler and Alertmanager. Grafana queries Mimir in-cluster
  (no nginx basic auth on the Service port).
- **Loki (monolithic):** receives logs from spoke Alloy via
  authenticated Routes. Grafana queries Loki in-cluster.
- **Alloy Hub:** a dedicated Alloy instance in the hub namespace.
  CloudWatch metrics are ingested with `prometheus.exporter.cloudwatch`
  (YACE), filtered to Hummingbird resources (`app-code=RPRM-001`).
  Credential-expiry metrics are ingested with the textfile collector
  from a CI-generated ConfigMap. Alloy Hub remote-writes to in-cluster
  Mimir (Service DNS; no Route or CA bundle).
- **Grafana:** exposed via an internal Route. Authentication is Generic
  OAuth against gitlab.com (`redhat/hummingbird` group). GitLab Owner
  and Maintainer map to Grafana Admin, Developer to Editor, everyone
  else in the allowed group to Viewer. Datasources and dashboards live
  in `grafana_data/` and are synced with `grafana_data/deploy.sh`.
  Grafana also has a CloudWatch datasource for ad-hoc browsing of AWS
  logs and metrics; that path is query-only and is not used for
  alerting or pod-log forwarding.
- **External access:** Loki and Mimir Routes sit behind an nginx sidecar
  with HTTP basic auth. In-cluster Service access (Grafana, Alloy Hub)
  does not require auth.

**Spoke (every cluster):**

- **Namespace:** `hummingbird--monitoring`
- **Alloy:** collects container logs via `loki.source.kubernetes` and
  scrapes `prometheus.io/scrape` Services, including kube-state-metrics.
  Forwards logs to hub Loki and metrics to hub Mimir. Dual-writes to
  staging and production hubs.
- **kube-state-metrics:** Kubernetes object metrics (deployments, pods,
  jobs, PVCs, resource quotas) with a curated allowlist.
- **No local Mimir, Loki, Grafana, or Alertmanager.**

### AWS Lambda Services

Some Hummingbird services (e.g. container-catalog) run as AWS Lambda
functions. Observability for those services uses the existing AWS
signals rather than an OpenTelemetry Lambda extension:

- **Metrics:** Alloy Hub YACE scrapes curated `AWS/Lambda` metrics
  (Invocations, Errors, Duration, Throttles) into Mimir. Mimir alerting
  rules cover error rate and throttling.
- **Logs:** Grafana queries CloudWatch Logs directly via the CloudWatch
  datasource. Pod logs are not involved; Lambda logs stay in
  CloudWatch.
- Low-traffic utility Lambdas are covered by the same YACE allowlist
  when tagged `app-code=RPRM-001`.

If/when these services migrate to OpenShift, they fall under the
standard spoke collection paths (Alloy scrape + `loki.source`) with no
additional plumbing.

### Log Collection

Container stdout/stderr is tailed by spoke Alloy using
`loki.source.kubernetes` (Kubernetes API; no DaemonSet, no sidecar, no
ClusterLogForwarder). Logs are labeled with cluster, namespace, pod,
container, and app, then dual-written to hub Loki.

This requires no application code changes. ClusterLogForwarder is
available on some clusters but is not used.

### High Availability

**Hub:**

| Component     | Replicas | Rationale                                          |
|---------------|----------|----------------------------------------------------|
| Mimir         | 1        | Monolithic; brief downtime acceptable              |
| Loki          | 1        | Monolithic; brief downtime acceptable              |
| Grafana       | 1        | View-only; brief downtime acceptable               |
| Alloy Hub     | 1        | Stateless scrape; gap until next scrape is OK      |

**Spoke:**

| Component           | Replicas | Rationale                               |
|---------------------|----------|-----------------------------------------|
| Alloy               | 1        | Stateless forwarder; brief gap OK       |
| kube-state-metrics  | 1        | Stateless; brief gap OK                 |

Spoke clusters have no stateful observability components. HA concerns
are concentrated on the hub. Single-replica monolithic Mimir and Loki
are an accepted tradeoff against the proposed Prometheus + Thanos HA
pair: there is no existing Prometheus fleet to retrofit, and Alloy
already remote-writes.

### Retention

| Environment | Mimir | Loki |
|-------------|-------|------|
| Production  | 90d   | 90d  |
| Staging     | 14d   | 14d  |

S3 is provisioned with ObjectBucketClaim. There is no separate warm/cold
tier or multi-year archive.

### Operator Availability

CRD availability was audited on 2026-08-09. Hummingbird has no
cluster-admin access — only operator CRDs explicitly granted to tenant
namespaces are usable. That audit is why this stack does **not** use
Cluster Observability Operator (MonitoringStack / Thanos), LokiStack,
TempoStack, ClusterLogForwarder, or an OpenTelemetry Collector as the
live path:

- **LokiStack and TempoStack** are not available to tenant namespaces
  on any cluster. Loki is a standalone Deployment. Tempo is deferred.
- **COO MonitoringStack** is available on MPP but not on spoke, and
  would have required Prometheus + Thanos for a fleet we do not have.
  Mimir accepts remote-write directly from Alloy.
- **ClusterLogForwarder** is available, but Alloy
  `loki.source.kubernetes` collects the same pod logs without a second
  operator.
- **OpenTelemetry Collector** was deployed earlier and removed once
  Alloy wrote directly to Loki and Mimir.

## Relationship to Existing Dashboard

The existing `hummingbird-dashboard` app serves two distinct roles:

1. **Data visualisation** — CVE status charts, failed release counts,
   build metrics
2. **Operational workflows** — click to rerun a failed release,
   interactive triage, actionable controls

This observability stack takes over **data collection, storage, and
visualisation** (role 1). Grafana is the primary place for charts,
time-series dashboards, and alert-driven visualisations. The dashboard
app retains **operational workflow features** (role 2) — interactive
actions that Grafana cannot provide.

The two systems complement each other:

- The dashboard app can embed Grafana panels for richer visualisation
  without reimplementing charting
- The dashboard app can query the same backends (Mimir, Loki) directly
  for data it needs to drive workflows
- Over time, the dashboard app consumes data from the unified backends
  instead of maintaining parallel collection

Alerting (e.g. failed release Slack notifications) moves to
Alertmanager. The dashboard app no longer needs its own alerting path.

## What This Replaces

| Previous                                       | Replaced by                               |
|------------------------------------------------|-------------------------------------------|
| `cloudwatch-log-forwarder` Lambda              | Spoke Alloy → hub Loki                    |
| SNS `AlertsTopic` + consumer CloudWatch alarms | Mimir ruler + Alertmanager                |
| Per-service custom dashboards                  | Grafana dashboards                        |
| Dashboard app data collection                  | Unified backends (Mimir, Loki)            |
| Dashboard app alerting (Slack)                 | Alertmanager                              |
| Dashboard app visualisations                   | Grafana (embeddable in the dashboard app) |

The dashboard app itself is **not decommissioned** — its operational
workflow features (release reruns, interactive triage) remain. Only its
data collection and visualisation responsibilities shift to the unified
stack.

`hummingbird-events-topic` is the live event bus. It was not an
alerting channel and is **not** replaced by this stack.

Consumer CloudWatch alarms and the log-forwarder were removed after the
Mimir/Loki path was in place. Remaining CloudWatch use is intentional:

- Grafana CloudWatch datasource for ad-hoc AWS log and metric browsing
- CVE error-budget SLO dashboards and `hummingbird-slo-alerts` (no
  Grafana port yet)

## Operations

Day-to-day endpoints, datasources, query examples, and onboarding a new
cluster are documented in `documentation/monitoring.md` in the
[infrastructure repository][infrastructure].

## Future Work

- **Distributed tracing:** Tempo (or equivalent) for request and
  pipeline traces. Not deployed; traces are not a current signal.
- **CVE lifecycle tracing:** instrument CVE analysis, RPM build, and
  container image pipelines with spans. Trace a CVE from detection →
  RPM fix → image rebuild → publish. Requires a trace backend and a
  schema (separate story).
- **Spoke local alerting:** if operator access on spoke clusters
  changes, a local evaluation path could remove the hub dependency for
  spoke alerts. Not required today.

## Alternatives Considered

### Alerting: Grafana-only vs Alertmanager-only vs hybrid

- **Grafana-only:** less mature routing, dedup, and silencing.
- **Hybrid Grafana + Alertmanager (original proposal):** Grafana would
  evaluate rules across metrics, logs, and traces, then forward to
  Alertmanager. That is not what shipped: there is no Tempo, and log
  alerting is not required yet.
- **Mimir ruler + Alertmanager (chosen):** PromQL rules and delivery in
  one component. Matches the metrics-first rollout. Applications can
  still POST to the Alertmanager API later if needed.

### Metrics backend: Prometheus + Thanos vs Mimir

Prometheus + Thanos (MonitoringStack) was the original hub design. It
fits retrofitting an existing Prometheus fleet. Hummingbird had no such
fleet — Alloy already remote-writes. Mimir is one component for
receive, storage, PromQL, ruler, and Alertmanager, instead of
Prometheus + Thanos Sidecar + Store Gateway + Querier + a separate
Alertmanager.

### Logs: Sumo Logic vs Loki

Red Hat has a company-wide Sumo Logic license. However, the [Sumo Logic
Grafana plugin][sumo-plugin] requires Grafana Enterprise or Grafana Cloud —
it is not available in open-source Grafana. Loki integrates natively
with open-source Grafana and keeps logs on-cluster.

### Log collection: ClusterLogForwarder vs Alloy

ClusterLogForwarder is available on hub and spoke. Alloy
`loki.source.kubernetes` collects the same pod logs and already runs on
every spoke for metrics, so a second operator was not justified.

### Spoke architecture: full stack vs collector-only

- **Full stack per cluster:** each cluster runs its own backends and
  Grafana. Local alerting survives network partitions. Requires
  operator CRDs Hummingbird does not have on spoke.
- **Collector-only on spoke (chosen):** Alloy + kube-state-metrics
  forwarding to the hub. Simpler spoke footprint. Tradeoff: spoke
  alerting depends on hub connectivity.

### Lambda: OTel extension vs CloudWatch ingest

An OpenTelemetry Collector Lambda extension would export OTLP to the
hub. That needs a network path from Lambda to MPP and a collector that
no longer exists. YACE metrics into Mimir plus Grafana's CloudWatch
datasource for logs reuse AWS signals already produced by the
functions.

### HA: all components vs selective vs single replica

Full HA doubles cost with little benefit for view-only tools. The
original proposal kept HA only on Prometheus and Alertmanager. The
as-built stack uses single-replica monolithic Mimir and Loki;
Alertmanager is in-process with Mimir. Brief downtime is accepted.

## Consequences

- Team must learn Grafana dashboarding and PromQL/LogQL basics
- New hub services should expose Prometheus metrics (scrape annotation)
  and may add a Grafana dashboard under `grafana_data/`
- New spoke services must be scraped by Alloy (scrape annotation) and
  emit logs to stdout/stderr
- Spoke alerting depends on hub connectivity — no local alerting on
  spoke
- Deploying a new hub cluster requires Mimir, Loki, Grafana, and Alloy
  Hub, plus ObjectBucketClaims
- Deploying a new spoke cluster requires a `hummingbird--monitoring`
  namespace, Alloy, and kube-state-metrics pointing at both hubs
- CloudWatch remains for Lambda logs (Grafana datasource) and CVE SLO
  error-budget dashboards; it is not used for pod-log forwarding or
  consumer alarms

[hum-4790]: https://redhat.atlassian.net/browse/HUM-4790
[hum-4791]: https://redhat.atlassian.net/browse/HUM-4791
[sumo-plugin]: https://grafana.com/grafana/plugins/grafana-sumologic-datasource/
[infrastructure]: https://gitlab.com/redhat/hummingbird/infrastructure

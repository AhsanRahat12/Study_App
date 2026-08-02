# 📚 Study App

A study-session tracker (FastAPI + Flask) used as the vehicle for a complete, containerized, GitOps-driven deployment pipeline — from local dev through CI to Kubernetes. The app is intentionally simple; the engineering depth is in how it's built, tested, secured, released, and deployed.

> **Where deployments actually live:** this repo holds application source and CI/CD pipeline definitions only — **no deployment manifests**. All Kubernetes manifests, per-environment config, and released image tags live in a separate repo, [`study-app-gitops`](https://github.com/AhsanRahat12/study-app-gitops), which the pipelines below keep automatically in sync.

---

## Philosophy

Backend and frontend are treated as fully independent services end-to-end — separate versioning, separate images, separate release cadence, separate promotion to production. A frontend-only change never triggers a backend rebuild, redeploy, or version bump, and vice versa.

The pipeline is deliberately **not** one monolithic workflow. It's a set of small, independently-triggered GitHub Actions workflows chained together with path filtering and reusable `workflow_call`s — each stage stays readable and debuggable rather than folded into one opaque file. That calculus would flip at much larger scale (many more services/teams), but at this project's size, explicit beats DRY.

Dev auto-deploys, prod requires a pull request — a concrete, opinionated trust boundary: speed where the cost of being wrong is low, a human checkpoint where it isn't. And the cluster never receives `kubectl apply` from CI directly — every change flows through Git first via GitOps, giving a full audit trail and a deployed state that's reproducible from source control alone.

---

## Architecture

![Study App CI/CD and GitOps architecture](./architecture.svg)

---

## 🧰 Stack

| Tool | Purpose |
|---|---|
| FastAPI | Backend API (`src/backend`) |
| Flask | Frontend web app (`src/frontend`) |
| `uv` + Ruff | Dependency management, linting, formatting |
| Pytest + `pytest-cov` | Unit/integration tests, coverage-gated CI |
| Docker | Multi-stage, non-root, Alpine-based images |
| Trivy | Container vulnerability scanning (CI gate) |
| GitHub Actions | Path-filtered, reusable-workflow CI/CD |
| release-please | Conventional-Commits-driven semantic versioning, per component |
| Kustomize | Base + environment-overlay Kubernetes manifests |
| Flux | GitOps controller — reconciles the cluster from `study-app-gitops` |
| k3d | Disposable local Kubernetes for dev + e2e testing |
| `mise` | Toolchain version pinning + task runner |
| Dev Containers | Reproducible, zero-drift dev environment |

---

## 📁 Repository Structure

```
.
├── src/
│   ├── backend/          # FastAPI service
│   └── frontend/         # Flask service
├── Kubernetes/           # Local dev cluster config, Kustomize manifests (local), e2e test suite
├── scripts/              # Reusable automation: deploy key setup, GitOps tag updates
└── .github/workflows/    # CI/CD pipeline definitions
```

---

## 🔄 CI/CD Pipeline

| Stage | Workflow | What It Does |
|---|---|---|
| **Path-aware triggering** | `check_paths` job (per component) | `dorny/paths-filter` so a PR only triggers the backend or frontend pipeline for the component that actually changed |
| **Lint & format** | Ruff, identical locally and in CI | Correctness-oriented lint rules (e.g. blind exception handling, naive datetimes) plus formatting |
| **Test & coverage** | Pytest + `pytest-cov` | Per-component unit/integration tests with an enforced minimum coverage threshold as a merge gate |
| **End-to-end testing** | `e2e_test.py` | Provisions a real k3d cluster, builds and loads the actual Docker images, deploys via Kustomize, exercises the live HTTP API and frontend — not mocked |
| **Release automation** | [release-please](https://github.com/googleapis/release-please) | Parses Conventional Commit history per component, proposes semantic version bumps, changelogs, and GitHub releases — independently for backend and frontend |
| **Image build & publish** | `docker/build-push-action`, on release tag | Multi-stage, non-root, Alpine-based builds, pushed to GHCR tagged with both the release version and `latest` |
| **Vulnerability scanning** | Trivy | Scans every built image for OS + library CVEs, filtered to actionable (fixable) findings |
| **GitOps promotion** | `update-gitops.yaml` | Updates image tags in `study-app-gitops` — dev committed automatically, prod opened as a PR requiring human review |
| **Deployment** | Flux | Continuously reconciles the cluster against `study-app-gitops` |

**Merge discipline:** direct pushes to `main` are blocked; every change goes through a PR with required status checks (lint, test, coverage, image build/scan). Commit messages follow **Conventional Commits**, enforced via a `commitizen` pre-commit hook — release-please depends on this history to determine which component changed and what version bump is warranted.

---

## 📦 Containerization

Each optimization pass was verified with concrete before/after measurements:

| Stage | Base | Size | CVEs |
|---|---|---|---|
| Baseline | `python:latest` | ~450MB | 400+ |
| Slim | `python:3.13-slim` | ~80MB | ~19 |
| Alpine | `python:3.13-alpine` | ~53MB | — |
| Multi-stage + BuildKit cache mounts | (final image) | ~20MB | 0 actionable |

Dependencies install in a disposable builder stage; only the resulting virtual environment is copied into the final image — no build tooling, no source clutter, no package manager. The container runs as a dedicated, explicitly UID/GID-pinned non-root user, and dev/test tooling (`ruff`, `pytest`, etc.) is scoped to a dependency group excluded entirely from production builds.

---

## 🚀 GitOps & Deployment Strategy

Kubernetes manifests are managed with Kustomize, base + environment-overlay:

```
apps/
├── base/    # environment-agnostic Deployment/Service definitions
├── dev/     # namespace, dev- name prefix, dev image tags
└── prod/    # prod- name prefix, prod image tags, prod-specific config
```

Overlays patch only what differs per environment — the base manifests are never duplicated. Flux watches `study-app-gitops` and reconciles the cluster to match it on a short interval, so cluster state is always a direct reflection of what's committed to Git, not a manually-applied snapshot. Deploy authentication uses a repository-scoped SSH deploy key, not a personal credential, limiting blast radius to exactly the one repo that needs access.

---

## 🎯 Notable Engineering Decisions

- **Independent per-component versioning over lockstep releases** — avoids unnecessary redeploys of unchanged services, at the cost of slightly more complex release tooling.
- **Reusable GitHub Actions workflows over duplicated YAML** — weighed deliberately against a "template everything" instinct; at this project's scale, explicit per-component pipelines were judged more valuable than DRY abstraction.
- **Dev auto-deploys, prod requires a PR** — a concrete, opinionated trust boundary between low-cost and high-cost mistakes.
- **GitOps over direct cluster access** — every change flows through Git first, giving a full audit trail and a deployed state reproducible from source control alone.

---

## 🛠️ Local Development

**Prerequisites:** Docker (with enough resources to run a k3d cluster inside Docker-in-Docker) and a devcontainer-capable editor (e.g. VS Code with the [Dev Containers](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers) extension).

```bash
git clone git@github.com:AhsanRahat12/Study_App.git
cd Study_App
# Open in a devcontainer — it handles the rest of the toolchain automatically
mise run k8s-setup-local     # spin up a cluster, build images, deploy the app
mise run k8s-setup-minimal   # bare cluster only, nothing deployed
mise run k8s-setup-gitops    # cluster + Flux, syncing from study-app-gitops
mise run e2e-test            # full end-to-end test suite against a real cluster
```

Pull requests only — commit messages must follow [Conventional Commits](https://www.conventionalcommits.org/).

---

## 🌐 Connect

[LinkedIn](https://www.linkedin.com/in/rahatahsan/) &nbsp;•&nbsp; [Twitter/X](https://x.com/RahatAhsan20) &nbsp;•&nbsp; [GitHub (Main Profile)](https://github.com/AhsanRahat12) &nbsp;•&nbsp; [Medium](https://medium.com/@s.rahatahsan)

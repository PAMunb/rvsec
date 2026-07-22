# Docker Image Security Guide

## Tool Selection

Three open-source tools cover the full security lifecycle of our Docker images:

| Tool | Category | Phase | License | Purpose |
|------|----------|-------|---------|---------|
| **Hadolint** | Dockerfile Linter | Pre-build | GPL-3.0 | Lint Dockerfile source (syntax, best practices, ShellCheck on RUN) |
| **Dockle** | Image Linter | Post-build | Apache-2.0 | Lint built image (CIS benchmarks, non-root check, exposed secrets) |
| **Trivy** | Vulnerability Scanner | Post-build | Apache-2.0 | CVEs, misconfigs, secrets, license scanning |

Hadolint and Dockle are complementary, not redundant: Hadolint analyzes the Dockerfile source, Dockle analyzes the built image. Trivy covers vulnerability scanning with the broadest database coverage.

**Excluded tools**: Grype (same category as Trivy, redundant), Docker Scout (free tier limited to 1 repo, requires API connectivity), Docker Bench (runtime/production focus, not applicable to our ephemeral experiment containers).

---

## 1. Hadolint: Dockerfile Linter

### What is it?

Hadolint parses a Dockerfile and flags violations of best practices, common mistakes, and security anti-patterns. It integrates ShellCheck for shell commands inside RUN instructions.

### Installation

```bash
wget -O hadolint https://github.com/hadolint/hadolint/releases/download/v2.12.0/hadolint-Linux-x86_64
chmod +x hadolint
sudo mv hadolint /usr/local/bin/
```

### Usage

```bash
# Lint a single Dockerfile
hadolint docker/base/Dockerfile

# Lint all Dockerfiles
for f in docker/*/Dockerfile; do echo "=== $f ===" && hadolint "$f"; done
```

**Key rules**:
- **DL3006**: Always pin base image version (`FROM ubuntu:22.04`, not `FROM ubuntu`)
- **DL3008**: Pin package versions in `apt-get install`
- **DL3018**: Use `apt-get clean` after installing packages
- **DL4006**: Use `COPY --chown` instead of separate `chown`
- **SC2086**: ShellCheck warnings for scripts inside Dockerfile

---

## 2. Dockle: Image Linter

### What is it?

Dockle checks built Docker images against CIS Docker Benchmark recommendations and additional best practices. It detects issues that Hadolint cannot catch because they only manifest in the built image (e.g., running as root, exposed credentials, unnecessary setuid binaries).

### Installation

```bash
VERSION=$(curl --silent "https://api.github.com/repos/goodwithtech/dockle/releases/latest" | grep '"tag_name":' | sed -E 's/.*"v([^"]+)".*/\1/')
curl -L -o dockle.deb "https://github.com/goodwithtech/dockle/releases/download/v${VERSION}/dockle_${VERSION}_Linux-64bit.deb"
sudo dpkg -i dockle.deb && rm dockle.deb
```

### Usage

```bash
# Check a built image
dockle phtcosta/rvandroid:0.8.0

# Ignore specific checks (e.g., CIS-DI-0001 for non-root user)
dockle --ignore CIS-DI-0001 phtcosta/rvandroid:0.8.0
```

**Key checks**:
- **CIS-DI-0001**: Create a user for the container (non-root)
- **CIS-DI-0005**: Enable Content trust for Docker
- **CIS-DI-0006**: Add HEALTHCHECK instruction
- **DKL-DI-0001**: Avoid `latest` tag
- **DKL-DI-0005**: Clear `apt-get` caches
- **DKL-LI-0001**: Avoid credential files (`.env`, `.npmrc`, etc.)

---

## 3. Trivy: Vulnerability Scanner

### What is it?

Trivy is a comprehensive vulnerability scanner that inspects Docker images for known CVEs in OS packages, application dependencies, misconfigurations, and embedded secrets.

### Installation

```bash
sudo apt-get install wget apt-transport-https gnupg lsb-release -y
wget -qO - https://aquasecurity.github.io/trivy-repo/deb/public.key | sudo apt-key add -
echo "deb https://aquasecurity.github.io/trivy-repo/deb $(lsb_release -sc) main" | sudo tee -a /etc/apt/sources.list.d/trivy.list
sudo apt-get update && sudo apt-get install trivy -y
```

### Usage

```bash
# Full scan
trivy image phtcosta/rvandroid:0.8.0

# Only HIGH and CRITICAL vulnerabilities
trivy image --severity HIGH,CRITICAL phtcosta/rvandroid:0.8.0

# Scan Dockerfile for misconfigurations
trivy config docker/base/Dockerfile
```

**What to look for**:
- **CRITICAL and HIGH vulnerabilities**: Fix with priority
- **"fixed in ..." status**: Update the package in the Dockerfile and rebuild
- **"Status: affected" (no fix)**: Assess risk for our use case

---

## Recommended Workflow

### During Development (pre-build)

```bash
# 1. Lint the Dockerfile
hadolint docker/base/Dockerfile
```

### After Building (post-build)

```bash
# 2. Check image against CIS benchmarks
dockle phtcosta/rvandroid:0.8.0

# 3. Scan for vulnerabilities
trivy image --severity HIGH,CRITICAL phtcosta/rvandroid:0.8.0
```

### Remediation

1. Fix Hadolint warnings in the Dockerfile source
2. Address Dockle findings (non-root user, healthcheck, credential cleanup)
3. For Trivy CVEs with available fixes: update the package and rebuild
4. For Trivy CVEs without fixes: assess exploitability in our context (ephemeral experiment containers with no network exposure)
5. Rebuild and re-scan until CRITICAL vulnerabilities are resolved

FROM phtcosta/rvandroid_tools:0.9.2

ENV RVSEC_HOME=/opt/rvsec

# --- Layer 0: Remove upstream droidbot from base image ---
# The tools image installs upstream droidbot (honeynet/droidbot) via pip at
# /opt/droidbot/ and sets PYTHONPATH=/opt/droidbot. This conflicts with the
# local modified droidbot (which has POLICY_RVANDROID and other RV-Android
# customizations) installed by uv in Layer 4. PYTHONPATH takes precedence
# over the uv venv's site-packages, so `import droidbot.input_policy`
# resolves to the upstream version (missing POLICY_RVANDROID) instead of the
# local copy. Fix: remove the upstream install and clear PYTHONPATH.
RUN pip uninstall -y droidbot 2>/dev/null || true
ENV PYTHONPATH=

# --- Layer 1: Root project files (changes rarely) ---
WORKDIR /opt/rvsec/rv-android
COPY pyproject.toml uv.lock ./

# --- Layer 1b: DroidBot source ---
# DroidBot is a local path dependency (setup.py, not pyproject.toml).
# The full source is needed because `uv run droidbot` uses the uv
# virtualenv, which does not inherit the pip-installed droidbot from the
# base tools image. uv installs droidbot from this local path into
# the venv, including the console_scripts entry point.
COPY droidbot/ ./droidbot/

# --- Layer 2: Module pyproject.toml files only (changes rarely) ---
COPY modules/rv-android-core/pyproject.toml ./modules/rv-android-core/
COPY modules/rv-platform/pyproject.toml ./modules/rv-platform/
COPY modules/rv-tools/pyproject.toml ./modules/rv-tools/
COPY modules/rv-experiment/pyproject.toml ./modules/rv-experiment/
COPY modules/rv-agent/pyproject.toml ./modules/rv-agent/
COPY modules/rv-coverage/pyproject.toml ./modules/rv-coverage/
COPY modules/rv-static-analysis/pyproject.toml ./modules/rv-static-analysis/
COPY modules/rv-instrumentation/pyproject.toml ./modules/rv-instrumentation/
COPY modules/rv-monitor-generator/pyproject.toml ./modules/rv-monitor-generator/
COPY modules/rv-screen-parser/pyproject.toml ./modules/rv-screen-parser/
COPY modules/rv-uiautomator/pyproject.toml ./modules/rv-uiautomator/
COPY modules/rvagent-tool/pyproject.toml ./modules/rvagent-tool/
COPY modules/rv-agent-validation/pyproject.toml ./modules/rv-agent-validation/

# --- Layer 3: Stub packages for editable installs ---
# uv workspace requires package directories and README.md to exist.
# All modules have `readme = "README.md"` in pyproject.toml — the build fails
# with FileNotFoundError during PEP 517 build if README.md is missing.
# Create minimal stubs; real source code overwrites these in Layer 5.
RUN for mod in \
    rv-android-core/src/rv_android_core \
    rv-platform/src/rv_platform \
    rv-tools/src/rv_tools \
    rv-experiment/src/rv_experiment \
    rv-agent/src/rv_agent \
    rv-coverage/src/rv_coverage \
    rv-static-analysis/src/rv_static_analysis \
    rv-instrumentation/src/rv_instrumentation \
    rv-monitor-generator/src/rv_monitor_generator \
    rv-screen-parser/src/rv_screen_parser \
    rv-uiautomator/src/rv_uiautomator \
    rvagent-tool/src/rvagent_tool \
    rv-agent-validation/src/rv_agent_validation; \
  do \
    mod_dir="modules/$(dirname $(dirname $mod))"; \
    pkg_dir="modules/$mod"; \
    mkdir -p "$pkg_dir" && touch "$pkg_dir/__init__.py"; \
    touch "$mod_dir/README.md"; \
  done

# --- Layer 4: Install dependencies (cached unless pyproject.toml changes) ---
RUN uv sync --no-dev

# --- Layer 5: Source code (changes frequently, only this layer rebuilds) ---
COPY modules/ ./modules/

# Copy entry point script
COPY docker/rvandroid/docker-entrypoint.sh /opt/docker-entrypoint.sh
RUN chmod +x /opt/docker-entrypoint.sh

# Default environment variables
ENV RV_TOOLS=monkey
ENV RV_TIMEOUTS=300
ENV RV_REPETITIONS=1
ENV RV_NO_WINDOW=true
ENV RV_SPEC_SET=jca

# Volumes for APKs, artifacts, and results
VOLUME /opt/rvsec/rv-android/apks
VOLUME /opt/rvsec/rv-android/out
VOLUME /opt/rvsec/rv-android/results

ENTRYPOINT ["/opt/docker-entrypoint.sh"]
CMD ["run"]

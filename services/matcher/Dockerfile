# Build from the repository root:
#   docker build -f services/matcher/Dockerfile -t doors-matcher .
# The test stage runs the unit suite (including the research matcher's 14 worked examples);
# the runtime image is only produced if it passes.
# Behind a TLS-intercepting proxy, pass its CA for pip only (never stored in a layer):
#   docker build --secret id=pipca,src=/path/to/ca-bundle.crt -f services/matcher/Dockerfile .
ARG PYTHON=python:3.13.18-slim@sha256:ae14d4ce8771606477a81446e7ef429edd6762305fc50c84507c1041fa8285d1

FROM ${PYTHON} AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /src/services/matcher
COPY services/matcher/requirements.txt services/matcher/requirements-dev.txt ./
RUN --mount=type=secret,id=pipca,required=false \
    if [ -f /run/secrets/pipca ]; then export PIP_CERT=/run/secrets/pipca; fi; pip install -r requirements.txt

FROM base AS test
RUN --mount=type=secret,id=pipca,required=false \
    if [ -f /run/secrets/pipca ]; then export PIP_CERT=/run/secrets/pipca; fi; pip install -r requirements-dev.txt
COPY research/doors_into_one_room/scripts/narrative /src/research/doors_into_one_room/scripts/narrative
COPY services/matcher /src/services/matcher
RUN python -m pytest -q tests -W ignore::DeprecationWarning && touch /tests-passed

FROM base AS runtime
COPY --from=test /tests-passed /tests-passed
COPY services/matcher/matcher_service ./matcher_service
COPY services/matcher/idl ./idl
RUN useradd --uid 10001 --create-home matcher && mkdir -p /data && chown matcher /data
USER matcher
ENV MATCHER_ENV=production MATCHER_SIGNER=gcp-kms MATCHER_DB=/data/decisions.sqlite3
VOLUME ["/data"]
EXPOSE 8080
HEALTHCHECK --interval=10s --timeout=5s --start-period=20s CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8080/health').status==200 else 1)"
CMD ["uvicorn", "--factory", "matcher_service.app:factory", "--host", "0.0.0.0", "--port", "8080", "--workers", "1"]

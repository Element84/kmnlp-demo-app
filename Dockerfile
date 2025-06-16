# Adapted from https://github.com/Chainlit/cookbook/blob/main/aws-ecs-deployment/README.md

ARG PYTHON_VERSION=3.12
ARG BUILD_ENV_IS_CI=1

###############
# Base image #
###############

FROM python:${PYTHON_VERSION}-slim AS base
COPY --from=ghcr.io/astral-sh/uv:0.5.28 /uv /uvx /bin/
ARG BUILD_ENV_IS_CI

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Install git and ssh
RUN apt-get update && \
    apt-get install -y --no-install-recommends git  openssh-client

# Add GitLab's SSH key only if running locally.
# CI will use HTTPS to fetch from GitLab.
RUN \
    if [ "${BUILD_ENV_IS_CI:-0}" != "1" ]; then \
      mkdir -p -m 0700 ~/.ssh && ssh-keyscan repo.element84.com > ~/.ssh/known_hosts; \
    fi

# Update git config to fetch llm-agent private repo over HTTPS using basic auth.
# the HTTPS basic auth password will be the CI_JOB_TOKEN provided in secrets.
# Run ONLY if build is not local (i.e. is CI)
RUN --mount=type=secret,id=CI_JOB_TOKEN \
    if [ "${BUILD_ENV_IS_CI:-0}" -eq 1 ]; then \
      git config --global \
        url."https://gitlab-ci-token:$(cat /run/secrets/CI_JOB_TOKEN)@repo.element84.com/noaa_km_nlp/llm-agent.git".insteadOf ssh://git@repo.element84.com/noaa_km_nlp/llm-agent.git; \
    fi

# Set working directory
WORKDIR /app

# Create venv and use it
RUN uv venv
ENV PATH="/app/.venv/bin:$PATH"

# Add requirements file so we can install our dependencies
COPY pyproject.toml .
COPY uv.lock .

# Ensure lock file is up to date
RUN uv lock --check

# Setup venv and call `natural-language-geocoding init`.
# Do not mount SSH if CI, do if local
RUN \
    if [ "${BUILD_ENV_IS_CI:-0}" -eq 1 ]; then \
      uv sync --all-extras; \
      natural-language-geocoding init; \
    fi

RUN --mount=type=ssh \
    if [ "${BUILD_ENV_IS_CI:-0}" != "1" ]; then \
      uv sync --all-extras; \
      natural-language-geocoding init; \
    fi

###############
# Build image #
###############

FROM base AS build

COPY . /app

WORKDIR /app

# Build app
RUN python -m build

##################
# Chainlit image #
##################

FROM build AS chainlit

COPY . /app/

WORKDIR /app

ENV PATH="/app/.venv/bin:$PATH"

# Expose the port the app runs on
EXPOSE 8000

# Command to run the app
CMD ["chainlit", "run", "src/app.py", "-h", "--host", "0.0.0.0", "--port", "8000"]

##############
# Dask image #
##############

FROM base AS dask

WORKDIR /app

CMD ["bash"]

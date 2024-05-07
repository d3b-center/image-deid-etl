# ========= config AWS CLI ======================
FROM --platform=linux/amd64 debian:bullseye-slim AS awscli2-builder

RUN set -ex \
    && apt-get update && apt-get install -y ca-certificates curl unzip --no-install-recommends \
    && curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" \
    && unzip awscliv2.zip \
    # The --bin-dir is specified so that we can copy the entire bin directory
    # from the installer stage into into /usr/local/bin of the final stage
    # without accidentally copying over any other executables that may be
    # present in /usr/local/bin of the installer stage.
    && ./aws/install --bin-dir /aws-cli-bin/

#  ========= config dcm2niix =====================
FROM --platform=linux/amd64 debian:bullseye-slim AS dcm2niix-builder

# Specify version of dcm2niix release
ENV DCM2NIIX_VERSION="bb3a6c35d2bbac6ed95acb2cd0df65f35e79b5fb"

RUN mkdir -p /usr/local/src
WORKDIR /usr/local/src

RUN set -ex \
    && apt-get update && apt-get install -y ca-certificates build-essential cmake git --no-install-recommends \
    # The external CMake projects are referenced with the deprecated git:// protocol.
    && git config --global url."https://".insteadOf git:// \
    && git clone https://github.com/rordenlab/dcm2niix.git && cd dcm2niix \
    && git checkout "$DCM2NIIX_VERSION" \
    && mkdir build && cd build  \
    && cmake -DBATCH_VERSION=OFF -DUSE_OPENJPEG=ON -DUSE_JPEGLS=true -DZLIB_IMPLEMENTATION=Cloudflare ..  && make

#  ========= config libdcm-tools (GDCM utility package) =====================
FROM --platform=linux/amd64 ubuntu:focal AS gdcm-builder

RUN mkdir -p /usr/local/src
WORKDIR /usr/local/src

RUN apt-get update && apt-get install -y libgdcm-tools \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# ========= config Flywheel CLI =====================

FROM --platform=linux/amd64 debian:bullseye-slim AS flywheel-cli-builder

#ENV FLYWHEEL_VERSION=16.4.0
ENV FLYWHEEL_VERSION=18.1.2

RUN mkdir -p /usr/local/src
WORKDIR /usr/local/src

RUN set -ex \
    && apt-get update && apt-get install -y ca-certificates curl unzip --no-install-recommends \
    && curl "https://storage.googleapis.com/flywheel-dist/cli/$FLYWHEEL_VERSION/fw-linux_amd64-$FLYWHEEL_VERSION.zip" -o "flywheel-cli.zip" \
    && unzip flywheel-cli.zip

# ========= config Python packages =====================

FROM --platform=linux/amd64 python:3.9-slim-bullseye

RUN mkdir -p /usr/local/src
WORKDIR /usr/local/src

ENV PYTHONPATH=/usr/local/src

COPY requirements.txt /usr/local/src/
RUN set -ex \
    && buildDeps=" \
      build-essential \
      libpq-dev \
    " \
    && deps=" \
      ca-certificates \
      curl \
      pigz \
      postgresql-client \
    " \
    && apt-get update && apt-get install -y $buildDeps $deps --no-install-recommends \
    # Install Python dependencies.
    && pip install -r requirements.txt \
    # Purge build dependencies and clean up package state.
    && apt-get purge -y --auto-remove $buildDeps \
    && rm -rf /var/lib/apt/lists/*

# ========= finalize =====================

COPY . /usr/local/src/

RUN set -ex \
  # Install the project in editable mode so that we can edit sources via a
  # docker-compose volume mount without needing to reinstall the project.
  # https://pip.pypa.io/en/stable/cli/pip_install/#editable-installs
  && pip install --editable .

# Install the AWS CLI version 2.
COPY --from=awscli2-builder /usr/local/aws-cli/ /usr/local/aws-cli/
COPY --from=awscli2-builder /aws-cli-bin/ /usr/local/bin/
# Install dcm2niix.
COPY --from=dcm2niix-builder /usr/local/src/dcm2niix/build/bin/dcm2niix /usr/local/bin/dcm2niix
# Install the Flywheel CLI.
COPY --from=flywheel-cli-builder /usr/local/src/linux_amd64/fw /usr/local/bin/fw
# Install GDCM package libdcm-tools.
COPY --from=gdcm-builder /usr/bin/ /usr/local/bin/
COPY --from=gdcm-builder /lib/x86_64-linux-gnu/ /lib/x86_64-linux-gnu/

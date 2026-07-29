# CI image for psstools/pssparser on Forgejo Actions.
#
# Base is the manylinux image the wheels must be compatible with. Two things
# are added that the base lacks and that CI needs on every run:
#
#   node   -- act-based runners execute JS actions (checkout, upload-artifact)
#             *inside* the job container. manylinux ships no node, so without
#             this the very first workflow step fails.
#   java   -- the ANTLR tool is a jar; the parser generator runs at cmake time.
#
# Build deps are pre-installed into every interpreter so a run does not spend
# minutes doing it. Rebuild manually when the toolchain moves; nothing here
# tracks :latest.
FROM quay.io/pypa/manylinux_2_28_x86_64

ARG NODE_VERSION=20.18.1

RUN dnf install -y libuuid-devel java-11-openjdk-devel zip unzip which \
 && dnf clean all

# node, from the official tarball (nodesource has no EL8 build for node 20)
RUN curl -fsSL "https://nodejs.org/dist/v${NODE_VERSION}/node-v${NODE_VERSION}-linux-x64.tar.xz" \
      -o /tmp/node.tar.xz \
 && mkdir -p /opt/node \
 && tar -xJf /tmp/node.tar.xz -C /opt/node --strip-components=1 \
 && rm /tmp/node.tar.xz \
 && ln -s /opt/node/bin/node /usr/local/bin/node \
 && ln -s /opt/node/bin/npm  /usr/local/bin/npm
ENV PATH=/opt/node/bin:$PATH

# Build tooling in every interpreter that produces a wheel.
RUN for py in cp39-cp39 cp310-cp310 cp311-cp311 cp312-cp312 cp313-cp313 cp314-cp314; do \
      /opt/python/${py}/bin/python -m pip install --no-cache-dir -q \
        ninja wheel cython setuptools build ivpm ivpm-build || exit 1; \
    done

# Release/QA tooling lives in one interpreter only.
RUN /opt/python/cp312-cp312/bin/python -m pip install --no-cache-dir -q \
      auditwheel twine pytest

ENV IVPM_PYTHON=/opt/python/cp312-cp312/bin/python

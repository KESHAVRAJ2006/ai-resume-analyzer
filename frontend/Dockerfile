# syntax=docker/dockerfile:1

# ---------------------------------------------------------------------------
# Stage 1: build the static site.
# ---------------------------------------------------------------------------
FROM node:22-alpine AS builder

WORKDIR /build

# Copy the manifests alone first. Docker caches each layer by the files that
# went into it, so dependencies are only re-installed when package.json or the
# lockfile changes - not on every source edit.
COPY package.json package-lock.json ./
# `npm ci` installs exactly the lockfile, and fails if the two disagree. `npm
# install` would silently resolve newer versions inside a build nobody watches.
RUN npm ci

COPY . .

# Vite inlines import.meta.env at BUILD time, not at runtime. The API URL is
# therefore a build argument, and changing it means rebuilding the image - a
# container env var would have no effect at all.
ARG VITE_API_URL=http://127.0.0.1:8001
ENV VITE_API_URL=${VITE_API_URL}

RUN npm run build


# ---------------------------------------------------------------------------
# Stage 2: serve it.
#
# The result is ~50MB of nginx plus a few hundred KB of assets; node and
# node_modules never ship.
# ---------------------------------------------------------------------------
FROM nginx:1.27-alpine AS runtime

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /build/dist /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -q --spider http://127.0.0.1/ || exit 1

CMD ["nginx", "-g", "daemon off;"]

# syntax=docker/dockerfile:1.7
FROM node:22-alpine AS base
# Optional extra CA (corporate TLS proxy): docker build --secret id=extra_ca,src=ca.crt
RUN --mount=type=secret,id=extra_ca,required=false \
    if [ -s /run/secrets/extra_ca ]; then export NODE_EXTRA_CA_CERTS=/run/secrets/extra_ca npm_config_cafile=/run/secrets/extra_ca; fi; npm install -g pnpm@10.11.0
WORKDIR /repo

FROM base AS deps
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml .npmrc ./
COPY apps/web/package.json apps/web/package.json
COPY packages/court/package.json packages/court/package.json
COPY packages/api-client/package.json packages/api-client/package.json
COPY packages/tactics/package.json packages/tactics/package.json
COPY packages/ui/package.json packages/ui/package.json
RUN --mount=type=secret,id=extra_ca,required=false --mount=type=cache,id=pnpm,target=/root/.local/share/pnpm/store \
    if [ -s /run/secrets/extra_ca ]; then export NODE_EXTRA_CA_CERTS=/run/secrets/extra_ca npm_config_cafile=/run/secrets/extra_ca; fi; pnpm install --frozen-lockfile --filter @handball/web...

FROM deps AS build
COPY tsconfig.base.json ./
COPY packages packages
COPY apps/web apps/web
ENV NEXT_TELEMETRY_DISABLED=1
RUN pnpm --filter @handball/web build

FROM node:22-alpine AS runtime
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 PORT=3000 HOSTNAME=0.0.0.0
WORKDIR /app
# The runtime needs only node: drop npm, npx, corepack and yarn (smaller image, fewer CVEs).
RUN rm -rf /usr/local/lib/node_modules/npm /usr/local/lib/node_modules/corepack /opt/yarn-* \
      /usr/local/bin/npm /usr/local/bin/npx /usr/local/bin/corepack /usr/local/bin/yarn /usr/local/bin/yarnpkg \
 && addgroup -S app && adduser -S -G app -u 10001 app
COPY --from=build --chown=app:app /repo/apps/web/.next/standalone ./
COPY --from=build --chown=app:app /repo/apps/web/.next/static ./apps/web/.next/static
COPY --from=build --chown=app:app /repo/apps/web/public ./apps/web/public
USER app
EXPOSE 3000
HEALTHCHECK --interval=10s --timeout=3s --retries=5 CMD wget -qO- http://127.0.0.1:3000/api/healthz || exit 1
CMD ["node", "apps/web/server.js"]

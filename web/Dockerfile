FROM node:22-alpine AS build
WORKDIR /web
COPY package.json package-lock.json* ./
RUN if [ -f package-lock.json ]; then npm ci; else npm install; fi
COPY . .
ARG PUBLIC_TILES_URL=""
ARG PUBLIC_GLYPHS_URL=""
ENV PUBLIC_TILES_URL=$PUBLIC_TILES_URL PUBLIC_GLYPHS_URL=$PUBLIC_GLYPHS_URL
RUN npm run build

FROM caddy:2-alpine
COPY Caddyfile /etc/caddy/Caddyfile
COPY --from=build /web/build /srv/web

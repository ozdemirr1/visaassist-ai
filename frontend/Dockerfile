# Web image for `docker compose --profile app up` (see the README): the built client served by
# nginx, which forwards /api to the API container. Build context: the repository root.
FROM node:22-alpine AS build
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build && chmod -R a+rX dist

FROM nginx:1.27-alpine
COPY --chmod=644 frontend/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /web/dist /usr/share/nginx/html

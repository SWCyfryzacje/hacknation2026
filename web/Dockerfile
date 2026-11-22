ARG NODE_VERSION=24.14.0-alpine
# Oficjalny obraz nginx bez uprawnień roota (użytkownik nginx), wersja przypięta jawnie.
ARG NGINX_VERSION=1.30.5-alpine3.24

FROM node:${NODE_VERSION} AS build
WORKDIR /app

COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

FROM nginxinc/nginx-unprivileged:${NGINX_VERSION} AS run
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
# Proces bez roota nie może słuchać na porcie <1024 — 8080 w kontenerze, mapowany na 80 w docker-compose.
EXPOSE 8080
CMD ["nginx", "-g", "daemon off;"]

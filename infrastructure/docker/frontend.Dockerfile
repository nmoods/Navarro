FROM node:24-alpine AS build
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
ARG VITE_API_URL=http://127.0.0.1:8000
ARG VITE_AUTH_MODE=local
ENV VITE_API_URL=$VITE_API_URL VITE_AUTH_MODE=$VITE_AUTH_MODE
RUN npm run build

FROM nginx:1.29-alpine
COPY infrastructure/docker/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /web/dist /usr/share/nginx/html

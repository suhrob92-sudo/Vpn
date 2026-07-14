# Shared Dockerfile for the two Next.js apps; APP_DIR selects which one.
ARG APP_DIR=apps/miniapp

FROM node:20-alpine AS builder
ARG APP_DIR
ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
WORKDIR /build
COPY ${APP_DIR}/package.json ${APP_DIR}/package-lock.json* ./
RUN npm install --no-audit --no-fund
COPY ${APP_DIR}/ ./
RUN npm run build

FROM node:20-alpine
WORKDIR /srv/app
ENV NODE_ENV=production
COPY --from=builder /build/.next/standalone ./
COPY --from=builder /build/.next/static ./.next/static
EXPOSE 3000
CMD ["node", "server.js"]

FROM node:24-alpine
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1
COPY package.json package-lock.json ./
RUN npm ci --no-audit --fetch-retries=1 --fetch-timeout=30000 --loglevel=info
COPY . .
RUN npm run build
EXPOSE 3000
CMD ["node", "node_modules/next/dist/bin/next", "start", "--hostname", "0.0.0.0"]

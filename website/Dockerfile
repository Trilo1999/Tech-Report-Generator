# Multi-stage production build for website (Docusaurus + AI Research Agent UI)
FROM node:20-alpine AS builder

WORKDIR /app

# Install dependencies using cached layer
COPY website/package*.json ./website/
RUN cd website && npm ci

# Copy website and documentation source trees
COPY website ./website
COPY docs ./docs

# Build static bundle for production
WORKDIR /app/website
RUN npm run build

# Nginx Alpine runtime to serve static assets and proxy /api requests to backend
FROM nginx:alpine

COPY --from=builder /app/website/build /usr/share/nginx/html
COPY website/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]

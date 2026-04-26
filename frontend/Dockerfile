FROM node:22-bookworm-slim

# wget for compose healthcheck (node:slim does not ship it)
RUN apt-get update \
 && apt-get install -y --no-install-recommends wget \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy lockfiles first for better layer caching
COPY package.json package-lock.json ./
RUN npm ci

# Copy the rest of the source
COPY . /app

EXPOSE 3000

CMD ["npm", "run", "dev"]

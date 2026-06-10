FROM node:20-slim
WORKDIR /app
RUN apt-get update && apt-get install -y chromium ffmpeg && rm -rf /var/lib/apt/lists/*
COPY package*.json ./
RUN npm ci
COPY . .

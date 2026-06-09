# --- Stage 1: build the React dashboard ---
FROM node:20-slim AS dashboard
WORKDIR /app/dashboard
COPY dashboard/package*.json ./
RUN npm install
COPY dashboard/ ./
# generate.py writes responses.csv at the project root; the build copies it
# into dist. Provide a seed CSV so the very first build has data.
COPY responses.csv /app/responses.csv
RUN npm run build

# --- Stage 2: Python backend that serves the built dashboard ---
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
# App code + survey + initial data
COPY surveygen/ ./surveygen/
COPY generate.py server.py survey.json responses.csv responses.json ./
# Built dashboard from stage 1
COPY --from=dashboard /app/dashboard/dist ./dashboard/dist

ENV PORT=8080
EXPOSE 8080
CMD ["sh", "-c", "gunicorn server:app --bind 0.0.0.0:${PORT}"]

FROM python:3.12-slim

WORKDIR /app

# Copy only requirements first. Docker caches this layer, so deps are not
# reinstalled on every code change, only when requirements.txt itself changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
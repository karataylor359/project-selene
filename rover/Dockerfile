FROM python:3.12-slim AS base
RUN pip install --no-cache-dir fastapi uvicorn
RUN mkdir -p /rover/output
COPY base/server.py /rover/server.py
WORKDIR /rover
EXPOSE 8080

FROM base

# --- Install your dependencies below ---
# Example: RUN pip install anthropic httpx networkx
# Example: RUN npm install -g tsx && npm install openai
RUN apt-get update && apt-get install -y \
    curl \
    dnsutils \
    nmap

RUN pip install \
    openai \
    httpx \
    networkx \
    pandas \
    numpy


# --- Copy your code ---
COPY . /rover/

# Make scripts executable
RUN chmod +x /rover/run_mapping.sh /rover/run_reporting.sh

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8080"]

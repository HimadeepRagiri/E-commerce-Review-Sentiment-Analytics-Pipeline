# Base image with Java for Spark
FROM openjdk:11-slim

# Set a working directory
WORKDIR /app

# Install Python, pip, and other essentials
# This command first updates the package lists, then installs python3 and python3-pip,
# and finally cleans up the apt cache to keep the image small.
RUN apt-get update && \
    apt-get install -y python3 python3-pip && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files into container


ENTRYPOINT ["/bin/bash"]

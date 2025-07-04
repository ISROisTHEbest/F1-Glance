# Use the official lightweight Python image.
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

# Set work directory
WORKDIR /app

# Copy files into the image
COPY . /app

# Install dependencies
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

# Expose the port Flask runs on
EXPOSE $PORT

# Run the Flask app
CMD ["python", "main.py"]

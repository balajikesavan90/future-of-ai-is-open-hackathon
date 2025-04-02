# Use the official Python image from the Docker Hub
FROM python:3.12.7

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY pyproject.toml poetry.lock ./

# Install system dependencies (example: build-essential)
RUN apt-get update && apt-get install -y build-essential

# Create a virtual environment
RUN python -m venv /opt/venv

# Activate the virtual environment and install Poetry
RUN /opt/venv/bin/pip install poetry

# Ensure the virtual environment is used for the rest of the commands
ENV PATH="/opt/venv/bin:$PATH"

# Install the dependencies
RUN poetry install --no-root --verbose

# Copy the rest of the application code into the container
COPY . .

# Make the entrypoint script executable
RUN chmod +x entrypoint.sh

# Expose the port that Streamlit will run on
EXPOSE 8501

# Use the entrypoint script to start the application
ENTRYPOINT ["./entrypoint.sh"]
# Use an official Python runtime as a base image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any dependencies from requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Install Gunicorn to serve the app
RUN pip install gunicorn

# Expose the port your app will run on (default Flask port is 5000)
EXPOSE 5000

# Command to run the app using Gunicorn
CMD ["gunicorn", "-b", "0.0.0.0:8000", "app:app"]

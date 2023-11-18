# Use an official Python runtime as a parent image
FROM python:3.11.0

# Set the working directory in the container
WORKDIR /rogue

# Copy the requirements file into the container at /app
COPY requirements.txt /rogue/

# Install any needed packages specified in requirements.txt
RUN pip install -r requirements.txt

# Copy the rest of the application code into the container at /app
COPY . /rogue/

# Specify the command to run your application
CMD [ "python", "app.py" ]
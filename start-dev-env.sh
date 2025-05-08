#!/bin/bash

# Check if NVIDIA Container Toolkit is installed and configured
if ! command -v nvidia-smi &> /dev/null; then
    echo "NVIDIA GPU not detected. Please make sure your NVIDIA drivers are installed."
    exit 1
fi

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Test if Docker can access GPU
echo "Testing GPU access in Docker..."
if ! docker run --rm --gpus all nvidia/cuda:11.0.3-base-ubuntu20.04 nvidia-smi &> /dev/null; then
    echo "Docker cannot access GPU. Installing NVIDIA Container Toolkit..."
    
    # Install NVIDIA Container Toolkit
    curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
    curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
        sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
        sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
    sudo apt-get update
    sudo apt-get install -y nvidia-container-toolkit
    sudo nvidia-ctk runtime configure --runtime=docker
    sudo systemctl restart docker
    
    echo "NVIDIA Container Toolkit installed and configured."
else
    echo "GPU access in Docker is working correctly."
fi

# Build and start the container
echo "Building and starting the development container..."
docker-compose up -d

echo "Development environment is ready!"
echo "To enter the container, run: docker exec -it style-bert-vits2-dev bash"
echo "To start Jupyter Lab, run inside the container: jupyter lab --ip=0.0.0.0 --allow-root --no-browser"
echo "To stop the container, run: docker-compose down"

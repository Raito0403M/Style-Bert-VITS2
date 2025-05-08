# Style-Bert-VITS2 Docker Development Environment

This guide explains how to set up a development environment for Style-Bert-VITS2 using Docker with GPU support. There are multiple ways to use this environment, including a simple script, Docker Compose, or VSCode's Remote Containers extension.

## Prerequisites

- NVIDIA GPU with installed drivers
- Docker and Docker Compose
- NVIDIA Container Toolkit (will be installed automatically by the script if needed)

## Quick Start

The easiest way to start the development environment is to use the provided script:

```bash
./start-dev-env.sh
```

This script will:
1. Check if your NVIDIA GPU is properly detected
2. Verify Docker and Docker Compose are installed
3. Test if Docker can access your GPU
4. Install NVIDIA Container Toolkit if needed
5. Build and start the Docker container

## Manual Setup

If you prefer to set up the environment manually:

1. Build the Docker image:
   ```bash
   docker-compose build
   ```

2. Start the container:
   ```bash
   docker-compose up -d
   ```

3. Enter the container:
   ```bash
   docker exec -it style-bert-vits2-dev bash
   ```

4. To stop the container:
   ```bash
   docker-compose down
   ```

## Using Jupyter Lab

To start Jupyter Lab from inside the container:

```bash
jupyter lab --ip=0.0.0.0 --allow-root --no-browser
```

Then access it in your browser at `http://localhost:8888`. The token will be displayed in the terminal.

## Using the Web UI

The Gradio web UI is exposed on port 7860. After starting the appropriate server inside the container, you can access it at `http://localhost:7860`.

## Using VSCode Remote Containers

This project includes configuration for VSCode's Remote Containers extension, which provides an integrated development experience:

1. Install the [Remote - Containers](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers) extension in VSCode
2. Open the project folder in VSCode
3. Click on the green button in the bottom-left corner of VSCode
4. Select "Reopen in Container"

VSCode will build the Docker image and start the container automatically. It will also:
- Forward ports 7860 (Gradio) and 8888 (Jupyter)
- Install useful VSCode extensions for Python development
- Set up Python linting and formatting

## File Structure

- `Dockerfile.dev`: The main Dockerfile for development with GPU support
- `docker-compose.yml`: Configuration for Docker Compose
- `start-dev-env.sh`: Helper script to set up and start the environment
- `.devcontainer/`: Configuration for VSCode Remote Containers

## Troubleshooting

If you encounter issues with GPU access:

1. Make sure your NVIDIA drivers are properly installed:
   ```bash
   nvidia-smi
   ```

2. Check if NVIDIA Container Toolkit is installed:
   ```bash
   dpkg -l | grep nvidia-container-toolkit
   ```

3. Configure Docker to use NVIDIA Container Toolkit:
   ```bash
   sudo nvidia-ctk runtime configure --runtime=docker
   sudo systemctl restart docker
   ```

4. Test GPU access in Docker:
   ```bash
   docker run --rm --gpus all nvidia/cuda:11.0.3-base-ubuntu20.04 nvidia-smi
   ```

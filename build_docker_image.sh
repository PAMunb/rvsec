#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

mvn -B clean install -DskipTests -DskipMopAgent

mvn clean compile -f ./rv-android/pom.xml

# --- Configuration ---
IMAGE_NAME="phtcosta/rvsec"
IMAGE_TAG="0.8.0"
# Dockerfile is in the current directory (rvsec/)
DOCKERFILE_PATH="Dockerfile" 
# Build context is also the current directory (rvsec/)
BUILD_CONTEXT="." 

# --- Build Arguments for Android SDK Setup ---
# These arguments are defined in the Dockerfile and can be customized here.
# Default values are taken from your docker/android/Dockerfile content.
# Adjust these as needed for your specific target emulator/SDK.
BUILD_ARG_API_LEVEL="29"
BUILD_ARG_IMG_TYPE="google_apis"
BUILD_ARG_ARCHITECTURE="x86" 
BUILD_ARG_CMD_LINE_VERSION="8512546_latest" 
BUILD_ARG_DEVICE_ID="pixel"
BUILD_ARG_GPU_ACCELERATED="false"


echo "--- Construindo a Imagem Docker: ${IMAGE_NAME}:${IMAGE_TAG} ---"
echo "Dockerfile: ${DOCKERFILE_PATH}"
echo "Contexto de Build: ${BUILD_CONTEXT}"
echo "Nível da API Android: ${BUILD_ARG_API_LEVEL}"
echo "Arquitetura Android: ${BUILD_ARG_ARCHITECTURE}"

# --- Docker Build Command ---
# The --pull flag ensures we get the latest base images.
# --progress=plain shows detailed build output for easier debugging.
docker build \
  --file "${DOCKERFILE_PATH}" \
  --tag "${IMAGE_NAME}:${IMAGE_TAG}" \
  --build-arg API_LEVEL="${BUILD_ARG_API_LEVEL}" \
  --build-arg IMG_TYPE="${BUILD_ARG_IMG_TYPE}" \
  --build-arg ARCHITECTURE="${BUILD_ARG_ARCHITECTURE}" \
  --build-arg CMD_LINE_VERSION="${BUILD_ARG_CMD_LINE_VERSION}" \
  --build-arg DEVICE_ID="${BUILD_ARG_DEVICE_ID}" \
  --build-arg GPU_ACCELERATED="${BUILD_ARG_GPU_ACCELERATED}" \
  --pull \
  --progress=plain \
  "${BUILD_CONTEXT}"

echo "--- Build da Imagem Docker Concluído! ---"
echo "Você pode agora executar sua imagem usando: docker run -it --rm ${IMAGE_NAME}:${IMAGE_TAG} bash"
echo "Ou executar o comando padrão: docker run -it --rm ${IMAGE_NAME}:${IMAGE_TAG}"
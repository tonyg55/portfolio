#!/bin/bash

IMAGE_NAME="purchase_proba_image"
CONTAINER_NAME="purchase_proba_container"

# Make sure to start at the project root folder
# Build the Image
docker build -t $IMAGE_NAME .

#Start the Container
docker run -d -p 1313:1313 --name $CONTAINER_NAME $IMAGE_NAME

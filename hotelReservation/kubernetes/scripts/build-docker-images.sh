#!/bin/bash

cd $(dirname $0)/..


EXEC="docker buildx"

USER="ghcr.io/talha-waheed"

TAG="latest"

# ENTER THE ROOT FOLDER
cd ../
ROOT_FOLDER=$(pwd)
echo $ROOT_FOLDER
$EXEC create --name mybuilder --use

for i in hotel-reservation #frontend geo profile rate recommendation reserve search user #uncomment to build multiple images
do
  IMAGE=${i}
  echo Processing image ${IMAGE}
  cd $ROOT_FOLDER
  $EXEC build -t "$USER"/"$IMAGE":"$TAG" -f Dockerfile . --platform linux/arm64,linux/amd64 --push
  cd $ROOT_FOLDER

  echo
done


cd - >/dev/null

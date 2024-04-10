#!/bin/bash
set -x
docker build -t ghcr.io/adiprerepa/social-network-microservices .
docker push ghcr.io/adiprerepa/social-network-microservices

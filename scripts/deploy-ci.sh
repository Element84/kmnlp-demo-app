#!/bin/bash

# ##########################################################################################
# Deploy script called in the CI pipeline
#
# This script builds the docker images and pushes them to ECR
#
# NOTE: This script will likely fail if you run it locally.
# Prefer the build_containers and push_containers scripts if you need those effects locally.
# ##########################################################################################

set -euo pipefail

# Install aws tools
echo "Installing aws tools …"
apt-get update && apt-get install -y --no-install-recommends unzip jq
#
# Install the AWS CLi
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
./aws/install


echo "Building docker images …"

docker buildx build \
    --secret id=CI_JOB_TOKEN \
    -t "chainlit-demo/chainlit" \
    --target chainlit \
    --platform linux/amd64 \
    .

docker buildx build \
    --secret id=CI_JOB_TOKEN \
    -t "chainlit-demo/dask" \
    --target dask \
    --platform linux/amd64 \
    .

GITLAB_DEPLOY_ROLE_ARN=${GITLAB_DEPLOY_ROLE_ARN:-}
CREDS=$(aws sts assume-role --role-arn "$GITLAB_DEPLOY_ROLE_ARN" --role-session-name "git-lab-pipeline-push-container-images")
AWS_ACCESS_KEY_ID=$(echo "$CREDS" | jq -r '.Credentials.AccessKeyId')
AWS_SECRET_ACCESS_KEY=$(echo "$CREDS" | jq -r '.Credentials.SecretAccessKey')
AWS_SESSION_TOKEN=$(echo "$CREDS" | jq -r '.Credentials.SessionToken')
AWS_REGION="us-east-1"
AWS_ACCOUNT_ID=${AWS_ACCOUNT_ID:-}

export AWS_ACCESS_KEY_ID
export AWS_SECRET_ACCESS_KEY
export AWS_SESSION_TOKEN
export AWS_REGION
export AWS_ACCOUNT_ID

scripts/push_containers.sh

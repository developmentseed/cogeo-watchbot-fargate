
SHELL = /bin/bash

image:
	docker build --tag watchbot:latest .

# EDIT THIS SECTION
REGION=us-east-1
SERVICE=cog-translator
VERSION=latest

push: image
	eval `aws ecr get-login --no-include-email`
	aws ecr describe-repositories --region ${REGION} --repository-names ${SERVICE} > /dev/null 2>&1 || \
		aws ecr create-repository --region ${REGION} --repository-name ${SERVICE} > /dev/null
	docker tag watchbot:latest "${AWS_ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/${SERVICE}:${VERSION}"
	docker push "${AWS_ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/${SERVICE}:${VERSION}"
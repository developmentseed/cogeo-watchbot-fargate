# Simple AWS Fargate watchbot

Creates Cloud Optimized GeoTIFF

# Build and Deploy

### Requirements 
This project uses [Serverless](https://serverless.com) to manage deploy on AWS.

```bash
# Install and Configure serverless (https://serverless.com/framework/docs/providers/aws/guide/credentials/)
$ npm install serverless -g 
```

### Build ECS images
```
# 1. Build ecs image
make image

# 2. Edit ECR info in `makefile`

# 3. Build and publish ECS image
make push
```

### Config

The instance type (CPU, memory, docker image) has to be specified in [/resources/config.yml](/resources/config.yml)

```yml
ecs:
  image: '{a docker image}'
  
  # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-ecs-taskdefinition.html#cfn-ecs-taskdefinition-memory
  memory: 8192
  
  # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-ecs-taskdefinition.html#cfn-ecs-taskdefinition-cpu
  cpu: 2048

  # Auto scaling
  minInstances: 0
  maxInstances: 10
```

Note: If you need to write/read to different S3 bucket, you'll need to edit [/resources/ecs.yml](/resources/ecs.yml) `TaskRole`.

### Autoscaling

The ECS service will automatically be scaled Up and Down in response to the number of SQS messages. **If no message is in queue the service will be scaled down to {minInstances}**.

### Deploy
```
sls deploy --stage production --bucket "my-bucket-where-to-store-cogs"
```

### Send jobs 

see [/scripts/create_jobs.py](/scripts/create_jobs.py)
```
$ aws s3 ls s3://spacenet-dataset/spacenet/SN5_roads/test_public/AOI_7_Moscow/PS-RGB/ --recursive | awk '{print " https://spacenet-dataset.s3.amazonaws.com/"$NF}' > list.txt

$ cat list.txt | python -m create_jobs - \
    -p webp \
    --co blockxsize=256 \
    --co blockysize=256 \
    --op overview_level=6 \
    --op overview_resampling=bilinear \
    --bucket my-bucket \
    --prefix cogs/spacenet \
    --topic arn:aws:sns:us-east-1:{account}:cogeo-watchbot-fargate-production-snsTopic
```
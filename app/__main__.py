from typing import Dict, Union

import os
import sys
import json
import time

import boto3

from botocore.exceptions import ClientError

from . import translator

sqs = boto3.resource("sqs")


def process(message: Dict) -> bool:
    """Create COGs."""
    if isinstance(message, str):
        message = json.loads(message)

    src_path = message["src_path"]
    dst_bucket = message["dst_bucket"]
    dst_prefix = message["dst_prefix"]

    translator.process(
        src_path,
        dst_bucket,
        dst_prefix,
        profile=message["profile_name"],
        profile_options=message.get("profile_options", {}),
        allow_remote_read=message.get("allow_remote_read", False),
        copy_valid_cog=message.get("copy_valid_cog", False),
        **message.get("options", {}),
    )

    return True


def _parse_message(message: Dict) -> Union[Dict, str]:
    if not message.get("Records"):
        return message

    record = message["Records"][0]
    body = json.loads(record["body"])

    return body["Message"]


def main():
    """Get Message and Process."""
    # Get the queue
    try:
        queue = sqs.get_queue_by_name(QueueName=os.environ["SQS_NAME"])
    except ClientError:
        print("SQS Queue {SQS_NAME} not found".format(SQS_NAME=os.environ["SQS_NAME"]))
        sys.exit(1)

    while True:
        message = False
        for message in queue.receive_messages():
            m = _parse_message(json.loads(message.body))
            print(json.dumps(m))
            process(m)

            # Let the queue know that the message is processed
            message.delete()

        if not message:
            time.sleep(30)  # if no message, let's wait 30secs

        time.sleep(1)


if __name__ == "__main__":
    main()

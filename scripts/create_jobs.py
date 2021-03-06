"""create_job: Feed SQS queue."""

import json
from functools import partial
from concurrent import futures
from collections import Counter
from urllib.parse import urlparse

import click

from boto3.session import Session as boto3_session

from rasterio.rio import options
from rio_tiler.utils import _chunks
from rio_cogeo.profiles import cog_profiles


def sources_callback(ctx, param, value):
    """
    Validate scheme and uniqueness of sources.

    From: https://github.com/mapbox/pxm-manifest-specification/blob/master/manifest.py#L157-L179

    Notes
    -----
    The callback takes a fileobj, but then converts it to a sequence
    of strings.

    Returns
    -------
    list

    """
    sources = list([name.strip() for name in value])

    # Validate scheme.
    schemes = [urlparse(name.strip()).scheme for name in sources]
    invalid_schemes = [
        scheme for scheme in schemes if scheme not in ["s3", "http", "https"]
    ]
    if len(invalid_schemes):
        raise click.BadParameter(
            "Schemes {!r} are not valid and should be on of 's3/http/https'.".format(
                invalid_schemes
            )
        )

    # Identify duplicate sources.
    dupes = [name for (name, count) in Counter(sources).items() if count > 1]
    if len(dupes) > 0:
        raise click.BadParameter(
            "Duplicated sources {!r} cannot be processed.".format(dupes)
        )

    return sources


def sns_worker(messages, topic, subject=None):
    """Send batch of SNS messages."""
    session = boto3_session()
    client = session.client("sns")
    for message in messages:
        client.publish(Message=json.dumps(message), TargetArn=topic)
    return True


@click.command()
@click.argument("sources", default="-", type=click.File("r"), callback=sources_callback)
@click.option(
    "--cog-profile",
    "-p",
    "cogeo_profile",
    type=click.Choice(cog_profiles.keys()),
    default="deflate",
    help="CloudOptimized GeoTIFF profile (default: deflate).",
)
@options.creation_options
@click.option(
    "--options",
    "--op",
    "options",
    metavar="NAME=VALUE",
    multiple=True,
    callback=options._cb_key_val,
    help="rio_cogeo.cogeo.cog_translate input options.",
)
@click.option(
    "--allow-remote-read",
    is_flag=True,
    default=False,
    help="Don't copy file locally and perform remote reads (default: False).",
)
@click.option(
    "--copy-valid-cog",
    is_flag=True,
    default=False,
    help="Perform pure copy if file is already a valid COG (default: False).",
)
@click.option("--bucket", type=str, required=True, help="AWS S3 Output Bucket.")
@click.option("--prefix", type=str, default="cogs", help="AWS S3 Key prefix.")
@click.option("--topic", type=str, required=True, help="SNS Topic")
def cli(
    sources,
    cogeo_profile,
    creation_options,
    options,
    allow_remote_read,
    copy_valid_cog,
    bucket,
    prefix,
    topic,
):
    """
    Create cogeo-watchbot-light jobs.

    Example:
    aws s3 ls s3://spacenet-dataset/spacenet/SN5_roads/test_public/AOI_7_Moscow/PS-RGB/ --recursive | awk '{print " https://spacenet-dataset.s3.amazonaws.com/"$NF}' > list.txt
    cat list.txt | python -m create_jobs - \
        -p webp \
        --co blockxsize=256 \
        --co blockysize=256 \
        --op overview_level=6 \
        --op overview_resampling=bilinear \
        --prefix cogs/spacenet \
        --topic arn:aws:sns:us-east-1:{account}:cogeo-watchbot-fargate-production-snsTopic

    """

    def _create_message(source):
        message = {
            "src_path": source,
            "dst_bucket": bucket,
            "dst_prefix": prefix,
            "profile_name": cogeo_profile,
            "profile_options": creation_options,
            "options": options,
        }
        if allow_remote_read:
            message.update(dict(allow_remote_read=True))

        if copy_valid_cog:
            message.update(dict(copy_valid_cog=True))

        return message

    messages = [_create_message(source) for source in sources]
    parts = _chunks(messages, 50)
    _send_message = partial(sns_worker, topic=topic)
    with futures.ThreadPoolExecutor(max_workers=50) as executor:
        executor.map(_send_message, parts)


if __name__ == "__main__":
    cli()

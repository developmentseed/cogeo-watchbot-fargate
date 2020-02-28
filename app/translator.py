"""translator"""

from typing import Any, Dict

import os
from urllib.parse import urlparse

import wget

from boto3.session import Session as boto3_session

from rasterio.io import MemoryFile
from rio_cogeo.cogeo import cog_translate, cog_validate
from rio_cogeo.profiles import cog_profiles


def _s3_download(
    bucket: str, key: str, out_key: str, client: boto3_session.client = None
) -> str:
    if not client:
        session = boto3_session()
        client = session.client("s3")

    client.download_file(bucket, key, out_key)
    return out_key


def _upload_obj(
    obj: bytes, bucket: str, key: str, client: boto3_session.client = None
) -> bool:
    if not client:
        session = boto3_session()
        client = session.client("s3")

    client.upload_fileobj(obj, bucket, key)
    return True


def process(
    url: str,
    out_bucket: str,
    out_key: str,
    profile: str = "webp",
    profile_options: Dict = {},
    allow_remote_read: bool = False,
    copy_valid_cog: bool = False,
    **options: Any,
) -> None:
    """Download, convert and upload."""
    url_info = urlparse(url.strip())
    if url_info.scheme not in ["http", "https", "s3"]:
        raise Exception(f"Unsuported scheme {url_info.scheme}")

    if allow_remote_read:
        src_path = url
    else:
        src_path = "/tmp/" + os.path.basename(url_info.path)
        if url_info.scheme.startswith("http"):
            wget.download(url, src_path)
        elif url_info.scheme == "s3":
            in_bucket = url_info.netloc
            in_key = url_info.path.strip("/")
            _s3_download(in_bucket, in_key, src_path)

    if copy_valid_cog and cog_validate(src_path):
        with open(src_path, "rb") as f:
            _upload_obj(f, out_bucket, out_key)
    else:
        config = dict(
            GDAL_NUM_THREADS="ALL_CPUS",
            GDAL_TIFF_INTERNAL_MASK=True,
            GDAL_TIFF_OVR_BLOCKSIZE="128",
        )
        output_profile = cog_profiles.get(profile)
        output_profile.update(dict(BIGTIFF="IF_SAFER"))
        output_profile.update(profile_options)

        with MemoryFile() as mem_dst:
            cog_translate(
                src_path,
                mem_dst.name,
                output_profile,
                config=config,
                in_memory=False,  # Limit Memory usage
                quiet=True,
                allow_intermediate_compression=True,  # Limit Disk usage
                **options,
            )
            _upload_obj(mem_dst, out_bucket, out_key)

        del mem_dst

    if not allow_remote_read:
        os.remove(src_path)

    return

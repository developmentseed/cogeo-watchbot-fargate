FROM remotepixel/amazonlinux:gdal3.0-py3.7

COPY app app
COPY setup.py setup.py

# Install dependencies
RUN pip3 install . --no-binary rasterio

ENV \
  GDAL_CACHEMAX=512 \
  PYTHONWARNINGS=ignore

ENTRYPOINT ["python3", "-m", "app"]

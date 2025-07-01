# Gixy as a Service

A Dockerized FastAPI microservice that runs [gixy] on an
nginx configuration dump and returns security findings as JSON.

## Prerequisites

* Docker & Docker Compose installed
* Port 8080 available

## Included Files

* `Dockerfile`        — builds the multi-service image
* `build.sh`          — convenience script to build the image
* `requirements.txt`  — Python dependencies for FastAPI
* `supervisord.conf` — supervisord config for both gixy and recheck
* `app.py`            — FastAPI application source

## Building the Image

Use the provided `build.sh` (or run Docker directly):

```bash
./build.sh
# or

docker build --no-cache -t multi-service-app .
```

## Running the Service

```bash
docker run -d --rm \
  -p 8080:8080 \
  --name multi-service-app \
  multi-service-app
```

This starts two services under supervisord:

* **gixy**      — the FastAPI app listening on port 8080
* **recheck**   — the regex redos recheck HTTP API on port 3001

## API Endpoints

### `POST /scan/{scan_path}`

Scans an nginx config dump and returns gixy findings.

* **Path Param** `scan_path`

  * letters, digits, underscore, hyphen only

* **Request**: multipart form field `file`

  * content-type `text/plain` or `application/octet-stream`
  * payload: the output of `nginx -T`

* **Success (200 OK)**: JSON array of issues

  ```json
  [
    {
      "path": "/tmp/tmpabcd1234/myconf.conf",
      "rule": "ssl_certificate_nx_file",
      "severity": "High",
      "message": "SSL certificate file not found",
      ...
    },
    ...
  ]
  ```

* **Error Responses** (all JSON `{ "detail": "..." }`):

  * `400 Bad Request`

    * invalid `scan_path`
    * empty upload
    * JSON parse error from gixy
    * gixy exited non-zero
  * `415 Unsupported Media Type`

    * upload not plain-text or octet-stream
  * `502 Bad Gateway`

    * gixy binary missing or runtime error
  * `504 Gateway Timeout`

    * gixy scan timed out (15 minutes)

#### Example

```bash
curl -F "file=@nginx.conf" \
  http://localhost:8080/scan/my_config
```

### `GET /` (Help)

Returns a plain-text usage guide wrapped to \~80 columns.

```bash
curl http://localhost:8080/
```

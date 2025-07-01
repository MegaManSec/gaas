#!/usr/bin/env python3
import os
import re
import json
import tempfile
import shutil
import subprocess

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse

app = FastAPI(title="Gixy as a Service")

PREFIXES = [
    "balancer_by_lua_block",
    "body_filter_by_lua_block",
    "content_by_lua_block",
    "header_filter_by_lua_block",
    "init_by_lua_block",
    "init_worker_by_lua_block",
    "log_by_lua_block",
    "lua_ingress",
    "rewrite_by_lua_block",
    "set_by_lua_block",
    "ssl_certificate_by_lua_block",
]

_pattern = re.compile(
    r"^\s*(?!#)\s*(" + "|".join(map(re.escape, PREFIXES)) + r")\b"
)

def remove_blocks(lines):
    out = []
    removing = False
    depth = 0

    for line in lines:
        if not removing:
            if _pattern.match(line):
                removing = True
                depth = line.count("{") - line.count("}")
                if depth <= 0:
                    removing = False
                continue
            out.append(line)
        else:
            depth += line.count("{") - line.count("}")
            if depth <= 0:
                removing = False
            continue

    return out

@app.post("/scan/{scan_path}", response_class=JSONResponse)
async def scan(scan_path: str, file: UploadFile = File(...)):
    if file.content_type not in ("text/plain", "application/octet-stream"):
        raise HTTPException(status_code=415, detail="Expecting a plain-text nginx -T dump")
    if not re.fullmatch(r"[A-Za-z0-9_-]+", scan_path):
        raise HTTPException(status_code=400, detail="Invalid filename in path; only A–Z, a–z, 0–9, underscore and hyphen allowed")

    raw = await file.read()
    if not raw.strip():
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    text = raw.decode() if isinstance(raw, bytes) else raw
    lines = text.splitlines(keepends=True)
    cleaned = remove_blocks(lines)

    temp_dir = tempfile.mkdtemp()
    tmp_conf = os.path.join(temp_dir, f"{scan_path}.conf")
    os.makedirs(os.path.dirname(tmp_conf), exist_ok=True)
    with open(tmp_conf, "w") as f:
        f.writelines(cleaned)

    try:
        proc = subprocess.run(
            ["gixy", "-f", "json", "--regex-redos-url", "http://localhost:3001/recheck", tmp_conf],
            text=True,
            capture_output=True,
            timeout=900,
        )
        output = json.loads(proc.stdout)
        for item in output:
            item['path'] = tmp_conf
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail=proc.stderr or proc.stdout)
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=400, detail="gixy timed out")
    finally:
        try:
            shutil.rmtree(temp_dir)
        except OSError:
            pass

    return JSONResponse(content=output)

@app.get("/", response_class=PlainTextResponse)
async def help():
    help_text = """
    POST /scan/{scan_path}

    Send the output of `nginx -T` as a plain-text file upload under field
    `file`.  The `scan_path` is a user-supplied name (letters, digits,
    underscore, hyphen only) used to name the temp file.

    CONTENT TYPES
      - text/plain
      - application/octet-stream

    USAGE EXAMPLE
      curl -F "file=@nginx.conf" https://yourhost/scan/my_config

    RESPONSES

      200 OK
        JSON array of findings from gixy.  Each item includes at least:
          - path     – the scanned filename (with “.conf” suffix)
          - rule     – gixy rule ID
          - severity – gixy severity level
          - message  – human-readable description

    ERROR CODES

    ERROR CODES (all return JSON with a “detail” field)

      400 Bad Request
        JSON: {"detail": "<message>"}
        - invalid scan_path (only A–Z, a–z, 0–9, underscore, hyphen)
        - empty upload payload
        - JSON parse error (invalid gixy output)
        - gixy returned non-zero exit code

      415 Unsupported Media Type
        JSON: {"detail": "Expecting a plain-text nginx -T dump"}

      502 Bad Gateway
        JSON: {"detail": "<error from gixy or missing binary>"}

      504 Gateway Timeout
        JSON: {"detail": "gixy timed out"}

    """.strip("\n")
    return help_text

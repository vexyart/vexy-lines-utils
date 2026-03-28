#!/usr/bin/env bash
cd "$(dirname "$0")"
uvx hatch clean
gitnextver
uvx hatch build
uv publish

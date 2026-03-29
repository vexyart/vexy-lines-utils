#!/usr/bin/env bash
# this_file: test.sh
# Run all tests including linting, formatting, and functional examples.
set -euo pipefail

echo "=== Lint & Format ==="
fd -e py --exclude '_private' --exclude '.venv' -x uvx autoflake -i {}
fd -e py --exclude '_private' --exclude '.venv' -x uvx pyupgrade --py312-plus {}
fd -e py --exclude '_private' --exclude '.venv' -x uvx ruff check --output-format=github --fix --unsafe-fixes {}
fd -e py --exclude '_private' --exclude '.venv' -x uvx ruff format --respect-gitignore --target-version py312 {}

echo ""
echo "=== Unit Tests ==="
python3 -m pytest tests/ -v --tb=short

echo ""
echo "=== Functional: Parse .lines ==="
python3 examples/parse_lines.py _private/lines-examples/Chameleon.lines 2>/dev/null

echo ""
echo "=== Functional: Extract Images ==="
tmpdir=$(mktemp -d)
python3 examples/extract_images.py _private/lines-examples/Chameleon.lines --output_dir "$tmpdir" 2>/dev/null
ls -la "$tmpdir"
rm -rf "$tmpdir"

echo ""
echo "=== Functional: Style Interpolation (dry-run) ==="
python3 examples/style_interpolation.py \
    --style_a _private/lines-examples/Chameleon.lines \
    --style_b _private/lines-examples/Chameleon.lines \
    --steps 3 2>/dev/null

echo ""
echo "=== CLI: info ==="
python3 -m vexy_lines_utils info _private/lines-examples/girl-linear.lines 2>/dev/null

echo ""
echo "=== CLI: file_tree ==="
python3 -m vexy_lines_utils file_tree _private/lines-examples/Chameleon.lines 2>/dev/null

echo ""
echo "=== All tests passed ==="

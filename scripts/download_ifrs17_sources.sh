#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PDF_DIR="$ROOT_DIR/profiles/ifrs17/source_pdfs"
mkdir -p "$PDF_DIR"

download() {
  local url="$1"
  local filename="$2"
  curl -L --fail --retry 3 --output "$PDF_DIR/$filename" "$url"
}

download "https://www.ifrs.org/content/dam/ifrs/publications/pdf-standards/english/2021/issued/part-a/ifrs-17-insurance-contracts.pdf" "ifrs-17-insurance-contracts.pdf"
download "https://www.ifrs.org/content/dam/ifrs/project/insurance-contracts/ifrs-standard/ifrs-17-effects-analysis.pdf" "ifrs-17-effects-analysis.pdf"
download "https://www.ifrs.org/-/media/project/insurance-contracts/ifrs-standard/ifrs-17-project-summary.pdf" "ifrs-17-project-summary.pdf"
download "https://www.ifrs.org/content/dam/ifrs/project/insurance-contracts/ifrs-standard/ifrs-17-factsheet.pdf" "ifrs-17-factsheet.pdf"
download "https://www.ifrs.org/content/dam/ifrs/project/amendments-to-ifrs-17/project-summary-amends-to-ifrs17.pdf" "project-summary-amends-to-ifrs17.pdf"
download "https://www.ifrs.org/content/dam/ifrs/supporting-implementation/ifrs-17/premium-allocation-approach-example.pdf" "premium-allocation-approach-example.pdf"
download "https://www.ifrs.org/-/media/feature/supporting-implementation/ifrs-17/ifrs-17-reinsurance-contract-held-example.pdf" "ifrs-17-reinsurance-contract-held-example.pdf"
download "https://www.ifrs.org/-/media/feature/supporting-implementation/ifrs-17/webinar-ifrs-17-scope/ifrs-17-scope-slides.pdf" "ifrs-17-scope-slides.pdf"

echo "Downloaded IFRS 17 PDFs to $PDF_DIR"

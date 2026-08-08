#!/usr/bin/env bash
# ============================================================================
# Sync the latest 6 CSVs into your Neo4j import directory.
# ----------------------------------------------------------------------------
# Run this BEFORE your own `neo4j-admin ... --nodes=import/neo4j/...` command
# so the files under import/neo4j/ are NEVER stale / partially copied.
#
# Usage:
#   bash refresh_import.sh                       # uses $NEO4J_IMPORT if set
#   bash refresh_import.sh /path/to/neo4j/import # pass the import root dir
#
# The script creates <import>/neo4j/ and copies all 6 CSVs there.
# ============================================================================
set -euo pipefail

SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ $# -ge 1 ]]; then
  IMPORT_DIR="$1"
elif [[ -n "${NEO4J_IMPORT:-}" ]]; then
  IMPORT_DIR="${NEO4J_IMPORT}"
else
  echo "ERROR: pass your Neo4j import directory, e.g." >&2
  echo "       bash refresh_import.sh /opt/neo4j/import" >&2
  echo "       (or export NEO4J_IMPORT=/opt/neo4j/import)" >&2
  exit 1
fi

DEST="${IMPORT_DIR}/neo4j"
mkdir -p "${DEST}"

echo ">> Copying latest CSVs:"
echo "   from: ${SRC_DIR}"
echo "   to  : ${DEST}"
cp -f "${SRC_DIR}"/products.csv \
      "${SRC_DIR}"/components.csv \
      "${SRC_DIR}"/suppliers.csv \
      "${SRC_DIR}"/rel_product_component.csv \
      "${SRC_DIR}"/rel_component_supplier.csv \
      "${SRC_DIR}"/rel_product_assembly.csv \
      "${DEST}/"

echo ">> Synced. Your import layout is now: ${DEST}/"
echo ">> Then (with the DB STOPPED) run, e.g.:"
echo "   neo4j-admin database import full apple-supply-chain \\"
echo "     --nodes=import/neo4j/products.csv \\"
echo "     --nodes=import/neo4j/components.csv \\"
echo "     --nodes=import/neo4j/suppliers.csv \\"
echo "     --relationships=import/neo4j/rel_product_component.csv \\"
echo "     --relationships=import/neo4j/rel_component_supplier.csv \\"
echo "     --relationships=import/neo4j/rel_product_assembly.csv \\"
echo "     --overwrite-destination"

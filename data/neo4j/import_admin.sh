#!/usr/bin/env bash
# ============================================================================
# Apple Supply Chain Graph - Neo4j OFFLINE bulk import (neo4j-admin)
# ----------------------------------------------------------------------------
# Reads the 6 CSVs DIRECTLY from this folder via ABSOLUTE paths.
# No copying, no import/ directory, no path pitfalls. Works on Desktop /
# Docker / server tarball. Idempotent only if you use a fresh db name or
# pass --overwrite-destination (already included).
#
# IMPORTANT: the target database MUST be STOPPED before running this.
#   - Neo4j Desktop: stop the DB, then "Open Terminal" and run this script.
#   - Server:        sudo systemctl stop neo4j   (or: neo4j stop)
#
# Usage:
#   bash import_admin.sh            # creates DB named "apple-supply-chain"
#   bash import_admin.sh mydb       # custom DB name
# ============================================================================
set -euo pipefail

SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DB="${1:-apple-supply-chain}"

# optional: if neo4j-admin is not on PATH, set NEO4J_HOME and we build the path
if ! command -v neo4j-admin >/dev/null 2>&1; then
  if [[ -n "${NEO4J_HOME:-}" && -x "${NEO4J_HOME}/bin/neo4j-admin" ]]; then
    NEO4J_ADMIN="${NEO4J_HOME}/bin/neo4j-admin"
  else
    echo "ERROR: neo4j-admin not found on PATH. Set NEO4J_HOME or add it to PATH." >&2
    exit 1
  fi
else
  NEO4J_ADMIN="neo4j-admin"
fi

echo ">> Importing from: ${SRC_DIR}"
echo ">> Database name : ${DB}"
echo ">> Using         : ${NEO4J_ADMIN}"

"${NEO4J_ADMIN}" database import full "${DB}" \
  --nodes="${SRC_DIR}/products.csv" \
  --nodes="${SRC_DIR}/components.csv" \
  --nodes="${SRC_DIR}/suppliers.csv" \
  --relationships="${SRC_DIR}/rel_product_component.csv" \
  --relationships="${SRC_DIR}/rel_component_supplier.csv" \
  --relationships="${SRC_DIR}/rel_product_assembly.csv" \
  --overwrite-destination

echo ">> Done. Start the database, then run e.g.:"
echo "   MATCH (p:Product)-[:USES_COMPONENT]->(c:Component)-[:SUPPLIED_BY]->(s:Supplier)"
echo "   RETURN p.name, c.name, s.name LIMIT 25;"
echo ">> If the DB was pre-existing, run in Neo4j:  CREATE DATABASE ${DB} IF NOT EXISTS;"

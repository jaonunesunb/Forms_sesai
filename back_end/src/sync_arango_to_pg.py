import os
import sys
import argparse
import psycopg2
from psycopg2.extras import execute_values
from arango import ArangoClient

ARANGO_URL = os.getenv("ARANGO_URL", "http://arango:8529")
ARANGO_DB = os.getenv("ARANGO_DB", "owl_db")
ARANGO_USER = os.getenv("ARANGO_USER", "root")
ARANGO_PASSWORD = os.getenv("ARANGO_PASSWORD", "pwd")

POSTGRES_DSN = os.getenv(
    "POSTGRES_DSN",
    "postgresql://postgres:postgres@postgres:5432/forms",
)

def ensure_pg_schema(conn):
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS arango_classes (
              class_uri TEXT PRIMARY KEY,
              label     TEXT
            );
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS arango_properties (
              property_uri TEXT PRIMARY KEY,
              label        TEXT,
              domain_uri   TEXT,
              range_uri    TEXT
            );
        """)

def connect_arango():
    client = ArangoClient(hosts=ARANGO_URL)
    return client.db(ARANGO_DB, username=ARANGO_USER, password=ARANGO_PASSWORD)

def connect_pg():
    conn = psycopg2.connect(POSTGRES_DSN)
    conn.autocommit = True
    return conn

def sync_classes(db, conn, batch=1000):
    print("→ Lendo classes do Arango…")
    cursor = db.aql.execute("FOR c IN classes RETURN {uri:c.uri, label:c.label}", batch_size=batch)
    rows = []
    total = 0
    for doc in cursor:
        uri = doc.get("uri")
        if not uri:
            continue
        rows.append((uri, doc.get("label")))
        if len(rows) >= batch:
            upsert_classes(conn, rows)
            total += len(rows)
            rows.clear()
    if rows:
        upsert_classes(conn, rows)
        total += len(rows)
    print(f"✓ Classes upserted: {total}")
    return total

def upsert_classes(conn, rows):
    with conn.cursor() as cur:
        execute_values(cur, """
            INSERT INTO arango_classes (class_uri, label)
            VALUES %s
            ON CONFLICT (class_uri) DO UPDATE
            SET label = EXCLUDED.label
        """, rows)

def sync_properties(db, conn, batch=1000):
    total = 0
    # tenta detectar coleções usadas pelo seu loader
    candidate_colls = []
    for name in ("object_properties", "data_properties", "properties"):
        if db.has_collection(name):
            candidate_colls.append(name)

    if not candidate_colls:
        print("⚠ Nenhuma coleção de propriedades encontrada (object_properties/data_properties/properties). Pulando.")
        return 0

    for coll in candidate_colls:
        print(f"→ Lendo propriedades de '{coll}'…")
        cursor = db.aql.execute(f"FOR p IN {coll} RETURN p", batch_size=batch)
        rows = []
        for p in cursor:
            uri = p.get("uri") or p.get("property_uri")
            if not uri:
                continue
            label = p.get("label")
            domain_uri = p.get("domain") or p.get("domain_uri")
            range_uri  = p.get("range") or p.get("range_uri")

            # se vierem listas, junta em string
            if isinstance(domain_uri, list):
                domain_uri = ";".join(domain_uri)
            if isinstance(range_uri, list):
                range_uri = ";".join(range_uri)

            rows.append((uri, label, domain_uri, range_uri))
            if len(rows) >= batch:
                upsert_properties(conn, rows)
                total += len(rows)
                rows.clear()
        if rows:
            upsert_properties(conn, rows)
            total += len(rows)

    print(f"✓ Propriedades upserted: {total}")
    return total

def upsert_properties(conn, rows):
    with conn.cursor() as cur:
        execute_values(cur, """
            INSERT INTO arango_properties (property_uri, label, domain_uri, range_uri)
            VALUES %s
            ON CONFLICT (property_uri) DO UPDATE
            SET label = EXCLUDED.label,
                domain_uri = COALESCE(EXCLUDED.domain_uri, arango_properties.domain_uri),
                range_uri  = COALESCE(EXCLUDED.range_uri,  arango_properties.range_uri)
        """, rows)

def main():
    parser = argparse.ArgumentParser(description="Sincroniza Arango → Postgres (classes / propriedades)")
    grp = parser.add_mutually_exclusive_group()
    grp.add_argument("--classes", action="store_true", help="sincroniza apenas classes")
    grp.add_argument("--properties", action="store_true", help="sincroniza apenas propriedades")
    grp.add_argument("--all", action="store_true", help="sincroniza classes e propriedades (padrão)")
    args = parser.parse_args()

    if not (args.classes or args.properties or args.all):
        args.classes = True  # default: classes (evita FK no save_instance)

    print(f"ARANGO_URL={ARANGO_URL}  ARANGO_DB={ARANGO_DB}")
    print(f"POSTGRES_DSN={POSTGRES_DSN}")

    db = connect_arango()
    conn = connect_pg()
    ensure_pg_schema(conn)

    try:
        total_classes = total_props = 0
        if args.all or args.classes:
            total_classes = sync_classes(db, conn)
        if args.all or args.properties:
            total_props = sync_properties(db, conn)
        print(f"✔ Fim. classes={total_classes}  props={total_props}")
    finally:
        conn.close()

if __name__ == "__main__":
    sys.exit(main())

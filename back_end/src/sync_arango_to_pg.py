import argparse
import hashlib
import json
import os
import sys
from typing import Dict, Iterable, List, Tuple

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
        cur.execute("""
            CREATE TABLE IF NOT EXISTS ontology_sync (
              id         SERIAL PRIMARY KEY,
              source_uri TEXT NOT NULL,
              signature  TEXT NOT NULL,
              payload    JSONB,
              synced_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
              UNIQUE (source_uri, signature)
            );
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS form_definition_signature (
              form_id   INTEGER PRIMARY KEY REFERENCES form(id) ON DELETE CASCADE,
              signature TEXT NOT NULL,
              field_ids INTEGER[] NOT NULL,
              created_at TIMESTAMPTZ NOT NULL DEFAULT now()
            );
        """)


def connect_arango():
    client = ArangoClient(hosts=ARANGO_URL)
    return client.db(ARANGO_DB, username=ARANGO_USER, password=ARANGO_PASSWORD)


def connect_pg():
    conn = psycopg2.connect(POSTGRES_DSN)
    conn.autocommit = True
    return conn


def sync_classes(db, conn, batch: int = 1000):
    print("→ Lendo classes do Arango…")
    cursor = db.aql.execute(
        "FOR c IN classes RETURN {uri:c.uri, label:c.label, description:c.description}",
        batch_size=batch,
    )
    rows: List[Tuple[str, str]] = []
    total = 0
    classes: List[Dict[str, object]] = []
    for doc in cursor:
        uri = doc.get("uri")
        if not uri:
            continue
        rows.append((uri, doc.get("label")))
        classes.append(
            {
                "uri": uri,
                "label": doc.get("label"),
                "description": doc.get("description"),
            }
        )
        if len(rows) >= batch:
            upsert_classes(conn, rows)
            total += len(rows)
            rows.clear()
    if rows:
        upsert_classes(conn, rows)
        total += len(rows)
    print(f"✓ Classes upserted: {total}")
    return total, classes


def upsert_classes(conn, rows: Iterable[Tuple[str, str]]):
    with conn.cursor() as cur:
        execute_values(cur, """
            INSERT INTO arango_classes (class_uri, label)
            VALUES %s
            ON CONFLICT (class_uri) DO UPDATE
            SET label = EXCLUDED.label
        """, list(rows))


def sync_properties(db, conn, batch: int = 1000):
    total = 0
    candidate_colls: List[str] = []
    for name in ("object_properties", "data_properties", "properties"):
        if db.has_collection(name):
            candidate_colls.append(name)

    if not candidate_colls:
        print("⚠ Nenhuma coleção de propriedades encontrada (object_properties/data_properties/properties). Pulando.")
        return 0, []

    collected: List[Dict[str, object]] = []
    for coll in candidate_colls:
        print(f"→ Lendo propriedades de '{coll}'…")
        cursor = db.aql.execute(f"FOR p IN {coll} RETURN p", batch_size=batch)
        rows: List[Tuple[str, str, str, str]] = []
        for p in cursor:
            uri = p.get("uri") or p.get("property_uri")
            if not uri:
                continue
            label = p.get("label")
            domain_uri = p.get("domain") or p.get("domain_uri")
            range_uri = p.get("range") or p.get("range_uri")

            if isinstance(domain_uri, list):
                domain_uri = ";".join(domain_uri)
            if isinstance(range_uri, list):
                range_uri = ";".join(range_uri)

            rows.append((uri, label, domain_uri, range_uri))
            collected.append(
                {
                    "uri": uri,
                    "label": label,
                    "domain": domain_uri,
                    "range": range_uri,
                }
            )
            if len(rows) >= batch:
                upsert_properties(conn, rows)
                total += len(rows)
                rows.clear()
        if rows:
            upsert_properties(conn, rows)
            total += len(rows)

    print(f"✓ Propriedades upserted: {total}")
    return total, collected


def upsert_properties(conn, rows: Iterable[Tuple[str, str, str, str]]):
    with conn.cursor() as cur:
        execute_values(cur, """
            INSERT INTO arango_properties (property_uri, label, domain_uri, range_uri)
            VALUES %s
            ON CONFLICT (property_uri) DO UPDATE
            SET label = EXCLUDED.label,
                domain_uri = COALESCE(EXCLUDED.domain_uri, arango_properties.domain_uri),
                range_uri  = COALESCE(EXCLUDED.range_uri,  arango_properties.range_uri)
        """, list(rows))


def fetch_data_properties(db) -> List[Dict[str, object]]:
    if not (db.has_collection("data_props") and db.has_collection("domain_data")):
        return []
    query = """
    FOR p IN data_props
        LET domains = (
            FOR edge IN domain_data
                FILTER edge._from == p._id
                LET cls = DOCUMENT(edge._to)
                RETURN { uri: cls.uri, label: cls.label }
        )
        RETURN {
            uri: p.uri,
            label: p.label,
            description: p.description,
            range_datatypes: p.range_datatypes,
            xsd_facets: p.xsd_facets,
            domains: domains
        }
    """
    cursor = db.aql.execute(query)
    return list(cursor)


def sync_field_catalog(conn, data_props: Iterable[Dict[str, object]]) -> Dict[str, int]:
    rows: List[Tuple[str, str, str, str, str]] = []
    uris: List[str] = []
    for prop in data_props:
        uri = prop.get("uri")
        if not uri:
            continue
        uris.append(uri)
        label = prop.get("label") or uri
        description = prop.get("description")
        datatype = None
        ranges = prop.get("range_datatypes")
        if isinstance(ranges, list) and ranges:
            datatype = ranges[0]
        elif isinstance(ranges, str):
            datatype = ranges
        constraints = prop.get("xsd_facets") or {}
        if not isinstance(constraints, dict):
            constraints = {}
        rows.append((uri, label, description, datatype, json.dumps(constraints or {})))

    if rows:
        with conn.cursor() as cur:
            execute_values(cur, """
                INSERT INTO field_catalog (class_uri, label, description, datatype, constraints)
                VALUES %s
                ON CONFLICT (class_uri) DO UPDATE
                SET label = EXCLUDED.label,
                    description = COALESCE(EXCLUDED.description, field_catalog.description),
                    datatype = COALESCE(EXCLUDED.datatype, field_catalog.datatype),
                    constraints = COALESCE(EXCLUDED.constraints, field_catalog.constraints)
            """, rows)

    mapping: Dict[str, int] = {}
    if uris:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, class_uri FROM field_catalog WHERE class_uri = ANY(%s)",
                (uris,),
            )
            for field_id, class_uri in cur.fetchall():
                mapping[class_uri] = field_id
    return mapping


def fetch_form_definitions(db) -> List[Dict[str, object]]:
    if not (db.has_collection("classes") and db.has_collection("domain_data")):
        return []
    query = """
    FOR c IN classes
        LET fieldUris = (
            FOR edge IN domain_data
                FILTER edge._to == c._id
                LET prop = DOCUMENT(edge._from)
                FILTER prop != NULL AND prop.uri != NULL
                RETURN {
                    uri: prop.uri,
                    label: prop.label
                }
        )
        FILTER LENGTH(fieldUris) > 0
        RETURN {
            class_uri: c.uri,
            label: c.label,
            description: c.description,
            fields: fieldUris
        }
    """
    cursor = db.aql.execute(query)
    return list(cursor)


def sync_forms(conn, form_defs: Iterable[Dict[str, object]], field_map: Dict[str, int]):
    total = 0
    for form in form_defs:
        field_uris = [f.get("uri") for f in form.get("fields", []) if f.get("uri")]
        field_ids = [field_map[uri] for uri in field_uris if uri in field_map]
        if not field_ids:
            continue
        form_name = form.get("label") or form.get("class_uri")
        with conn.cursor() as cur:
            cur.execute(
                "SELECT ensure_form_version(%s, %s, %s, %s, %s)",
                (
                    form_name,
                    field_ids,
                    None,
                    form.get("class_uri"),
                    "active",
                ),
            )
            cur.fetchone()
        total += 1
    print(f"✓ Formulários sincronizados: {total}")


def record_signature(
    conn,
    classes: List[Dict[str, object]],
    properties: List[Dict[str, object]],
    data_props: List[Dict[str, object]],
):
    digest = hashlib.sha256()
    for cls in sorted(classes, key=lambda c: c.get("uri") or ""):
        digest.update((cls.get("uri") or "").encode("utf-8"))
        digest.update((cls.get("label") or "").encode("utf-8"))
        desc = cls.get("description")
        if desc:
            digest.update(str(desc).encode("utf-8"))
    for prop in sorted(properties, key=lambda p: p.get("uri") or ""):
        digest.update((prop.get("uri") or "").encode("utf-8"))
        digest.update((prop.get("label") or "").encode("utf-8"))
        digest.update((prop.get("domain") or "").encode("utf-8"))
        digest.update((prop.get("range") or "").encode("utf-8"))
    for dp in sorted(data_props, key=lambda p: p.get("uri") or ""):
        digest.update((dp.get("uri") or "").encode("utf-8"))
        ranges = dp.get("range_datatypes")
        if isinstance(ranges, list):
            for rng in ranges:
                digest.update(str(rng).encode("utf-8"))
        elif isinstance(ranges, str):
            digest.update(ranges.encode("utf-8"))
        constraints = dp.get("xsd_facets") or {}
        if isinstance(constraints, dict):
            for key in sorted(constraints):
                digest.update(key.encode("utf-8"))
                digest.update(str(constraints[key]).encode("utf-8"))
    signature = digest.hexdigest()
    payload = {
        "classes": len(classes),
        "properties": len(properties),
        "data_properties": len(data_props),
    }
    with conn.cursor() as cur:
        cur.execute(
            "SELECT signature FROM ontology_sync WHERE source_uri = %s ORDER BY synced_at DESC LIMIT 1",
            (ARANGO_DB,),
        )
        row = cur.fetchone()
        if row and row[0] == signature:
            print("✓ Nenhuma alteração detectada na ontologia (assinatura inalterada).")
            return signature
        cur.execute(
            """
            INSERT INTO ontology_sync (source_uri, signature, payload)
            VALUES (%s, %s, %s)
            ON CONFLICT (source_uri, signature) DO NOTHING
            """,
            (ARANGO_DB, signature, json.dumps(payload)),
        )
        if cur.rowcount:
            print("✓ Nova assinatura de ontologia registrada.")
        else:
            print("ℹ Assinatura já registrada anteriormente.")
    return signature


def main():
    parser = argparse.ArgumentParser(
        description="Sincroniza Arango → Postgres (classes, propriedades, campos, formulários)"
    )
    parser.add_argument("--classes", action="store_true", help="sincroniza classes")
    parser.add_argument("--properties", action="store_true", help="sincroniza propriedades")
    parser.add_argument(
        "--fields",
        action="store_true",
        help="sincroniza catálogo de campos a partir das data properties",
    )
    parser.add_argument("--forms", action="store_true", help="sincroniza formulários e versionamento")
    parser.add_argument("--signature", action="store_true", help="registra hash/assinatura da ontologia")
    parser.add_argument("--all", action="store_true", help="executa todas as etapas")
    args = parser.parse_args()

    if not any((args.classes, args.properties, args.fields, args.forms, args.signature, args.all)):
        args.all = True

    do_classes = args.all or args.classes
    do_props = args.all or args.properties
    do_fields = args.all or args.fields
    do_forms = args.all or args.forms
    do_signature = args.all or args.signature

    print(f"ARANGO_URL={ARANGO_URL}  ARANGO_DB={ARANGO_DB}")
    print(f"POSTGRES_DSN={POSTGRES_DSN}")

    db = connect_arango()
    conn = connect_pg()
    ensure_pg_schema(conn)

    try:
        total_classes = total_props = 0
        classes: List[Dict[str, object]] = []
        props: List[Dict[str, object]] = []
        data_props: List[Dict[str, object]] = []

        if do_classes:
            total_classes, classes = sync_classes(db, conn)
        if do_props:
            total_props, props = sync_properties(db, conn)
        if do_fields or do_forms or do_signature:
            data_props = fetch_data_properties(db)

        field_map: Dict[str, int] = {}
        if do_fields:
            field_map = sync_field_catalog(conn, data_props)
            print(f"✓ Catálogo de campos sincronizado: {len(field_map)} entradas atualizadas.")
        elif do_forms:
            with conn.cursor() as cur:
                cur.execute("SELECT id, class_uri FROM field_catalog")
                field_map = {uri: fid for fid, uri in cur.fetchall()}

        if do_forms:
            form_defs = fetch_form_definitions(db)
            if form_defs:
                if not field_map and data_props:
                    field_map = sync_field_catalog(conn, data_props)
                sync_forms(conn, form_defs, field_map)
            else:
                print("⚠ Nenhuma definição de formulário encontrada no Arango.")

        if do_signature:
            record_signature(conn, classes, props, data_props)

        print(f"✔ Fim. classes={total_classes}  props={total_props}")
    finally:
        conn.close()

if __name__ == "__main__":
    sys.exit(main())

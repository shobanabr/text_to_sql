from functools import lru_cache

import pandas as pd
from sqlalchemy import create_engine, inspect, text
import pandas as pd
import dataframe_image as dfi
from fpdf import FPDF

#postgresql+psycopg://USERNAME:PASSWORD@HOST:PORT/DATABASE

engine = create_engine(
    "postgresql+psycopg://postgres:shobanabr@localhost:5432/postgres"
)


def execute_query(query, db_name=None):
    # Connect to the requested database, or the default one
    db_engine = engine if db_name is None else create_engine(
        engine.url.set(database=db_name)
    )
    try:
        with db_engine.connect() as conn:
            return pd.read_sql(text(query), conn)
    finally:
        if db_name is not None:
            db_engine.dispose()

def quote_identifier(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def sample_queries(schema_name: str, schema: dict) -> dict:
    return {
        f"Preview {table.rsplit('.', 1)[-1]}":
            f"SELECT * FROM {quote_identifier(schema_name)}."
            f"{quote_identifier(table.rsplit('.', 1)[-1])} LIMIT 10"
        for table in list(schema)[:5]
    }


def get_databases():
    query = """
        SELECT datname
        FROM pg_database
        WHERE datallowconn
          AND NOT datistemplate
          AND has_database_privilege(datname, 'CONNECT')
          AND datname <> 'postgres'
        ORDER BY datname
    """
    return execute_query(query)["datname"].tolist()

def get_all_schemas(db_name):
    query = r"""
        SELECT nspname
        FROM pg_namespace
        WHERE nspname <> 'information_schema'
          AND nspname NOT LIKE 'pg\_%' AND nspname NOT LIKE 'public'
        ORDER BY nspname
    """
    return execute_query(query, db_name)["nspname"].tolist()

for db_name in get_databases():
    print(db_name, get_all_schemas(db_name))

def load_schema_metadata(database: str, schema_name: str) -> dict:
    schema_literal = schema_name.replace("'", "''")
    columns = execute_query(
        "SELECT table_name, column_name, data_type "
        "FROM information_schema.columns "
        f"WHERE table_schema = '{schema_literal}' "
        "ORDER BY table_name, ordinal_position",
        db_name=database,
    )

    schema = {}
    for table_name, column_name, data_type in columns.itertuples(
        index=False, name=None
    ):
        schema.setdefault(f"{schema_name}.{table_name}", []).append(
            (column_name, data_type or "TEXT", False, None)
        )
    return schema


def export_to_excel(df, filename="query_pilot_output.xlsx"):
    df.to_excel(filename, index=False, engine="openpyxl")


def export_to_image(df, filename="query_pilot_output.png"):
    dfi.export(df, filename, table_conversion="matplotlib")


def export_to_pdf(df, filename="query_pilot_output.pdf"):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=10)
    data = [[str(column) for column in df.columns]] + df.astype(str).values.tolist()
    with pdf.table() as table:
        for data_row in data:
            row = table.row()
            for datum in data_row:
                row.cell(str(datum))
    pdf.output(filename)



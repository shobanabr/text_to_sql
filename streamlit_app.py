"""
QueryPilot - generate SQL for a selected PostgreSQL database and schema.

"""
import os
import random
import sqlite3
from datetime import date, timedelta
import tempfile
from main import question_to_sql
from pathlib import Path
from mydb import (
    execute_query,
    get_all_schemas,
    export_to_image,
    export_to_excel,  
    export_to_pdf,  
    get_databases,
    load_schema_metadata,
    sample_queries
)
import pandas as pd
import streamlit as st

# ----------------------------------------------------------------------------
# Page config + styling
# ----------------------------------------------------------------------------
st.set_page_config(page_title="QueryPilot", page_icon="🧭", layout="wide")

st.markdown(
    """
    <style>
    .stApp {
        background: radial-gradient(1200px 600px at 80% -10%, #1e1b4b 0%, transparent 60%),
                    radial-gradient(900px 500px at -10% 10%, #0f766e33 0%, transparent 55%),
                    #0b1020;
        color: #fafbfc;
    }
    header[data-testid="stHeader"] { background: transparent; }

    /* Title */
    .qp-title {
        font-size: 3.2rem; font-weight: 800; letter-spacing: -1px; margin-bottom: 0;
        background: linear-gradient(90deg, #67e8f9, #a78bfa 55%, #f0abfc);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    }
    .qp-caption { color: #9ca3af; font-size: 1.05rem; margin-top: .2rem; margin-bottom: 1.4rem; }

    /* Input */
    div[data-testid="stTextInput"] input {
        background: #111833; color: #f3f4f6; border: 1px solid #312e81;
        border-radius: 14px; padding: 16px 18px; font-size: 1.05rem;
    }
    div[data-testid="stTextInput"] label,
    div[data-testid="stTextInput"] label p {
        color: #f3f4f6;
    }
    div[data-testid="stTextInput"] input:focus {
        border-color: #a78bfa; box-shadow: 0 0 0 3px #a78bfa33;
    }
    div[data-testid="stTextInput"] input::placeholder {
        color: #a0aab0;
        opacity: 1;
    }

    /* Buttons */
    .stButton > button {
        border-radius: 999px; border: 1px solid #312e81; background: #111833;
        color: #c7d2fe; padding: .35rem 1rem; transition: all .15s ease;
    }
    .stButton > button:hover { border-color: #67e8f9; color: #67e8f9; transform: translateY(-1px); }
    .stButton > button[kind="primary"] {
        background: linear-gradient(90deg, #06b6d4, #8b5cf6); border: none; color: white;
        font-weight: 600; padding: .6rem 1.6rem;
    }
    .stButton > button[kind="primary"]:hover { color: yellow; filter: brightness(1.1); }

    .qp-chip-label { color: #9ca3af; font-size: .85rem; margin: .8rem 0 .3rem 0; }

    /* Sidebar */
    section[data-testid="stSidebar"] { background: #0d1326; border-right: 1px solid #1f2547; }
    .qp-side-title { font-weight: 700; font-size: 1.1rem; color: #e0e7ff; }
    .qp-side-sub { color: #6b7280; font-size: .8rem; margin-bottom: .8rem; }
    div[data-testid="stExpander"] {
        background: #111833; border: 1px solid #1f2547; border-radius: 12px;
    }
    div[data-testid="stExpander"] summary,
    div[data-testid="stExpander"] summary p,
    div[data-testid="stExpander"] summary span {
        color: #f3f4f6;
        background-color: transparent;
    }
    div[data-testid="stExpander"] summary:hover,
    div[data-testid="stExpander"] summary:hover p,
    div[data-testid="stExpander"] summary:hover span {
        color: #f3f4f6;
        background-color: #1b2341;
    }
    div[data-testid="stExpander"] strong,
    div[data-testid="stExpander"] p,
    div[data-testid="stExpander"] code {
        color: #f3f4f6;
    }
    div[data-testid="stExpander"] code {
        background-color: #1b2341;
        border: 1px solid #4b5563;
        color: #ffffff;
    }

    .qp-sql {
        background: #f8fafc; border-left: 3px solid #8b5cf6; padding: .6rem 1rem;
        border-radius: 8px; font-family: monospace; color: #000000; white-space: pre-wrap;
    }
    .qp-metric {
        background: #111833; border: 1px solid #1f2547; border-radius: 14px; padding: .8rem 1.1rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.html(
    """
    <style>
    .st-key-selected_database label,
    .st-key-selected_database label *,
    [class*="st-key-selected_schema_"] label,
    [class*="st-key-selected_schema_"] label * {
        color: #f3f4f6 !important;
    }
    .st-key-selected_database [role="combobox"],
    [class*="st-key-selected_schema_"] [role="combobox"] {
        background-color: #111833 !important;
        border-color: #312e81 !important;
        color: #f3f4f6 !important;
    }
    .st-key-selected_database [role="combobox"] *,
    [class*="st-key-selected_schema_"] [role="combobox"] * {
        color: #f3f4f6 !important;
    }
    [role="listbox"] {
        background-color: #111833 !important;
    }
    [role="option"],
    [role="option"] * {
        color: #f3f4f6 !important;
    }
    [role="option"]:hover,
    [role="option"][aria-selected="true"] {
        background-color: #1b2341 !important;
    }
    .st-key-export_png button,
    .st-key-export_xlsx button,
    .st-key-export_pdf button {
        background-color: #111833 !important;
        border: 1px solid #312e81 !important;
        color: #f3f4f6 !important;
    }
    .st-key-export_png button:hover,
    .st-key-export_xlsx button:hover,
    .st-key-export_pdf button:hover {
        background-color: #1b2341 !important;
        border-color: #67e8f9 !important;
        color: #67e8f9 !important;
    }
    </style>
    """
)


# ----------------------------------------------------------------------------
# UI
# ----------------------------------------------------------------------------
st.session_state.setdefault("question", "")
st.session_state.setdefault("generate_query", False)
st.session_state.setdefault("generated_sql", None)
st.session_state.setdefault("query_result", None)
st.session_state.setdefault("query_error", None)

def use_sample(q):
    st.session_state.question = q
    st.session_state.generate_query = True

def submit():
    st.session_state.generate_query = True

def clear_question():
    st.session_state.question = ""
    st.session_state.generate_query = False
    st.session_state.generated_sql = None
    st.session_state.query_result = None
    st.session_state.query_error = None

def clear_query_result():
    st.session_state.generated_sql = None
    st.session_state.query_result = None
    st.session_state.query_error = None
    st.session_state.generate_query = False

# Main
st.markdown('<div class="qp-title">  QueryPilot</div>', unsafe_allow_html=True)

# Database and schema selection
try:
    databases = get_databases()
except Exception as database_error:
    st.error(f"Could not load available databases: {database_error}")
    st.stop()
if not databases:
    st.error("No databases are available to the configured PostgreSQL user.")
    st.stop()

left_space, database_col, schema_col, right_space = st.columns([1, 2, 2, 1])
with database_col:
    selected_database = st.selectbox(
        "Database",
        databases,
        key="selected_database",
        on_change=clear_query_result,
    )

try:
    schema_names = get_all_schemas(selected_database)
except Exception as schema_error:
    st.error(f"Could not load schemas from {selected_database}: {schema_error}")
    st.stop()
if not schema_names:
    st.error(f"No schemas are available in database {selected_database}.")
    st.stop()

schema_widget_key = f"selected_schema_{selected_database}"
with schema_col:
    selected_schema = st.selectbox(
        "Schema",
        schema_names,
        key=schema_widget_key,
        on_change=clear_query_result,
    )

try:
    schema = load_schema_metadata(selected_database, selected_schema)
except Exception as schema_error:
    st.error(f"Could not load schema details: {schema_error}")
    st.stop()

# Sidebar: schema browser
with st.sidebar:
    st.markdown('<div class="qp-side-title">🗂️ Table Schema</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="qp-side-sub">{selected_database} · {selected_schema} · click a table to expand</div>',
        unsafe_allow_html=True,
    )
    if not schema:
        st.caption("No tables or views in this schema.")
    for table, cols in schema.items():
        with st.expander(f"📋  {table.rsplit('.', 1)[-1]}"):
            for name, ctype, is_pk, fk in cols:
                badge = " 🔑" if is_pk else (f" 🔗 → `{fk}`" if fk else "")
                st.markdown(f"**{name}** &nbsp; `{ctype or 'TEXT'}`{badge}")

st.markdown(
    f'<div class="qp-caption">Ask your question to query {selected_database}.{selected_schema}</div>',
    unsafe_allow_html=True,
)

st.text_input(
    "question", key="question", label_visibility="collapsed",
    placeholder="e.g. Which city has the most customers?", on_change=submit,
)
with st.container(horizontal=True, vertical_alignment="bottom"):
    st.button("Submit  🚀", type="primary", on_click=submit)
    st.button("Clear", key="clear_question", on_click=clear_question)

samples = sample_queries(selected_schema, schema)
if samples:
    st.markdown('<div class="qp-chip-label">✨ Try a sample question</div>', unsafe_allow_html=True)
    chip_cols = st.columns(len(samples))
    for col, q in zip(chip_cols, samples):
        col.button(q, key=f"chip_{q}", on_click=use_sample, args=(q,), width="stretch")

# Generate and display SQL without executing it
if st.session_state.generate_query and st.session_state.question.strip():
    st.session_state.generate_query = False
    try:
        with st.spinner("Charting the route..."):
            st.session_state.generated_sql = question_to_sql(
                st.session_state.question,
                schema,
                selected_database,
                selected_schema,
                samples,
            )
        st.session_state.query_result = None
        st.session_state.query_error = None
    except Exception as e:
        st.session_state.generated_sql = None
        st.session_state.query_result = None
        st.error(f"Could not generate SQL: {e}")
        
def make_export_data(dataframe, export_function, filename: str):
    def write_image_fallback(output_path: Path) -> None:
        from PIL import Image, ImageDraw, ImageFont
        font = ImageFont.load_default()
        headers = [str(column) for column in dataframe.columns]
        rows = [
            [str(value).replace("\n", " ") for value in row]
            for row in dataframe.itertuples(index=False, name=None)
        ]
        draw_context = ImageDraw.Draw(Image.new("RGB", (1, 1)))
        cell_texts = [headers] + rows
        column_widths = [
            max(
                100,
                int(
                    max(
                        draw_context.textlength(row[index], font=font)
                        for row in cell_texts
                    )
                )
                + 20,
            )
            for index in range(len(headers))
        ]
        line_height = font.getbbox("Ag")[3] - font.getbbox("Ag")[1]
        row_height = max(28, line_height + 16)
        image = Image.new(
            "RGB",
            (sum(column_widths), row_height * len(cell_texts)),
            "white",
        )
        draw = ImageDraw.Draw(image)
        y = 0
        for row_index, row in enumerate(cell_texts):
            fill = "#dbeafe" if row_index == 0 else (
                "#f3f4f6" if row_index % 2 == 0 else "#ffffff"
            )
            x = 0
            for column_index, value in enumerate(row):
                width = column_widths[column_index]
                draw.rectangle(
                    (x, y, x + width, y + row_height),
                    fill=fill,
                    outline="#cbd5e1",
                )
                draw.text((x + 10, y + 8), value, fill="#111827", font=font)
                x += width
            y += row_height
        image.save(output_path, format="PNG")

    def write_excel_fallback(output_path: Path) -> None:
        import numbers
        import xml.etree.ElementTree as ET
        from zipfile import ZIP_DEFLATED, ZipFile

        main_ns = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
        office_rel_ns = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
        package_rel_ns = "http://schemas.openxmlformats.org/package/2006/relationships"
        content_ns = "http://schemas.openxmlformats.org/package/2006/content-types"
        ET.register_namespace("", main_ns)
        ET.register_namespace("r", office_rel_ns)

        def qname(namespace: str, tag: str) -> str:
            return f"{{{namespace}}}{tag}"

        def column_name(index: int) -> str:
            name = ""
            while index:
                index, remainder = divmod(index - 1, 26)
                name = chr(65 + remainder) + name
            return name

        def clean_text(value: str) -> str:
            return "".join(
                character
                for character in value
                if character in "\t\n\r"
                or ord(character) >= 32
            )

        worksheet = ET.Element(qname(main_ns, "worksheet"))
        sheet_data = ET.SubElement(worksheet, qname(main_ns, "sheetData"))
        values = [list(dataframe.columns)] + list(
            dataframe.itertuples(index=False, name=None)
        )
        for row_number, values_row in enumerate(values, start=1):
            row_element = ET.SubElement(
                sheet_data,
                qname(main_ns, "row"),
                {"r": str(row_number)},
            )
            for column_index, value in enumerate(values_row, start=1):
                cell = ET.SubElement(
                    row_element,
                    qname(main_ns, "c"),
                    {"r": f"{column_name(column_index)}{row_number}"},
                )
                try:
                    missing = pd.isna(value)
                    if not hasattr(missing, "__len__") and bool(missing):
                        continue
                except (TypeError, ValueError):
                    pass
                if isinstance(value, bool):
                    cell.set("t", "b")
                    ET.SubElement(cell, qname(main_ns, "v")).text = str(int(value))
                elif isinstance(value, numbers.Number):
                    ET.SubElement(cell, qname(main_ns, "v")).text = str(value)
                else:
                    cell.set("t", "inlineStr")
                    inline = ET.SubElement(cell, qname(main_ns, "is"))
                    text_element = ET.SubElement(inline, qname(main_ns, "t"))
                    text_element.set(
                        "{http://www.w3.org/XML/1998/namespace}space", "preserve"
                    )
                    text_element.text = clean_text(str(value))

        workbook = ET.Element(qname(main_ns, "workbook"))
        sheets = ET.SubElement(workbook, qname(main_ns, "sheets"))
        ET.SubElement(
            sheets,
            qname(main_ns, "sheet"),
            {
                "name": "Query results",
                "sheetId": "1",
                qname(office_rel_ns, "id"): "rId1",
            },
        )

        def relationships(namespace: str, items: list) -> bytes:
            root = ET.Element(qname(namespace, "Relationships"))
            for relationship_id, relationship_type, target in items:
                ET.SubElement(
                    root,
                    qname(namespace, "Relationship"),
                    {
                        "Id": relationship_id,
                        "Type": relationship_type,
                        "Target": target,
                    },
                )
            return ET.tostring(root, encoding="utf-8", xml_declaration=True)

        content_types = ET.Element(qname(content_ns, "Types"))
        ET.SubElement(
            content_types,
            qname(content_ns, "Default"),
            {
                "Extension": "rels",
                "ContentType": "application/vnd.openxmlformats-package.relationships+xml",
            },
        )
        ET.SubElement(
            content_types,
            qname(content_ns, "Default"),
            {"Extension": "xml", "ContentType": "application/xml"},
        )
        ET.SubElement(
            content_types,
            qname(content_ns, "Override"),
            {
                "PartName": "/xl/workbook.xml",
                "ContentType": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml",
            },
        )
        ET.SubElement(
            content_types,
            qname(content_ns, "Override"),
            {
                "PartName": "/xl/worksheets/sheet1.xml",
                "ContentType": "application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml",
            },
        )

        with ZipFile(output_path, "w", ZIP_DEFLATED) as workbook_file:
            workbook_file.writestr(
                "[Content_Types].xml",
                ET.tostring(content_types, encoding="utf-8", xml_declaration=True),
            )
            workbook_file.writestr(
                "_rels/.rels",
                relationships(
                    package_rel_ns,
                    [
                        (
                            "rId1",
                            "http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument",
                            "xl/workbook.xml",
                        )
                    ],
                ),
            )
            workbook_file.writestr(
                "xl/workbook.xml",
                ET.tostring(workbook, encoding="utf-8", xml_declaration=True),
            )
            workbook_file.writestr(
                "xl/_rels/workbook.xml.rels",
                relationships(
                    package_rel_ns,
                    [
                        (
                            "rId1",
                            "http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet",
                            "worksheets/sheet1.xml",
                        )
                    ],
                ),
            )
            workbook_file.writestr(
                "xl/worksheets/sheet1.xml",
                ET.tostring(worksheet, encoding="utf-8", xml_declaration=True),
            )
    def generate_file():
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / filename
            try:
                export_function(dataframe, str(output_path))
            except ModuleNotFoundError as error:
                if export_function is export_to_image and error.name == "matplotlib":
                    write_image_fallback(output_path)
                elif export_function is export_to_excel and error.name == "openpyxl":
                    write_excel_fallback(output_path)
                else:
                    raise
            return output_path.read_bytes()
    return generate_file

if st.session_state.generated_sql:
    st.divider()
    st.markdown("##### Generated SQL")
    st.code(st.session_state.generated_sql, language="sql")
    if st.button("Run query", type="primary", key="run_query"):
        try:
            with st.spinner("Running query..."):
                result_df = execute_query(
                    st.session_state.generated_sql,
                    db_name=selected_database,
                )
            st.session_state.query_result = {
                "sql": st.session_state.generated_sql,
                "database": selected_database,
                "schema": selected_schema,
                "data": result_df,
            }
            st.session_state.query_error = None
        except Exception as query_error:
            st.session_state.query_result = None
            st.session_state.query_error = str(query_error)

    if st.session_state.query_error:
        st.error(f"Query could not be run: {st.session_state.query_error}")

    result = st.session_state.query_result
    if (
        result
        and result["sql"] == st.session_state.generated_sql
        and result["database"] == selected_database
        and result["schema"] == selected_schema
    ):
        df = result["data"]
        m1, m2 = st.columns(2)
        m1.markdown(f'<div class="qp-metric">Rows returned<br><b style="font-size:1.6rem">{len(df)}</b></div>',
                    unsafe_allow_html=True)
        m2.markdown(f'<div class="qp-metric">Columns<br><b style="font-size:1.6rem">{len(df.columns)}</b></div>',
                    unsafe_allow_html=True)
        st.markdown("##### Results")
        st.dataframe(df, hide_index=True, alt="Query result table")
        if len(df.columns) == 2 and pd.api.types.is_numeric_dtype(df.iloc[:, 1]):
            st.bar_chart(
                df.set_index(df.columns[0]),
                alt="Query results grouped by the first column",
            )

        st.divider()
        st.markdown("##### Export results")
        export_cols = st.columns(3)
        export_options = [
            (
                "Export as image",
                export_to_image,
                "query_pilot_output.png",
                "image/png",
            ),
            (
                "Export as Excel",
                export_to_excel,
                "query_pilot_output.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ),
            (
                "Export as PDF",
                export_to_pdf,
                "query_pilot_output.pdf",
                "application/pdf",
            ),
        ]
        for col, (label, exporter, filename, mime_type) in zip(
            export_cols, export_options
        ):
            col.download_button(
                label,
                data=make_export_data(df, exporter, filename),
                file_name=filename,
                mime=mime_type,
                key=f"export_{filename.rsplit('.', 1)[-1]}",
                on_click="ignore",
                width="stretch",
            )


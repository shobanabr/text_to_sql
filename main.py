from anyio import Path
from openai import OpenAI
from dotenv import load_dotenv
import os
import streamlit as st
import tempfile

load_dotenv()

#my_key = os.getenv('OPENAI_API_KEY')
# client = OpenAI()


def question_to_sql(question: str, schema: dict, database: str,
                    schema_name: str, samples: dict) -> str:
    # 1) exact / close match with a sample question
    key = question.strip().lower().rstrip("?.")
    for q, sql in samples.items():
        if key == q.lower():
            print(f"Using sample query for question: {question!r}")
            return sql

    # 2) LLM (needs ANTHROPIC_API_KEY)
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "Set ANTHROPIC_API_KEY to answer free-form questions, or choose a sample query."
        )
    import anthropic

    ddl = "\n".join(
        f"{t}({', '.join(f'{c[0]} {c[1]}' for c in cols)})" for t, cols in schema.items()
    )
    client = anthropic.Anthropic(api_key=api_key)
    msg = client.messages.create(
        model="claude-sonnet-5-5",
        max_tokens=500,
        system=(
            "You translate questions into a single read-only PostgreSQL SELECT query. "
            f"Only query database {database!r} and schema {schema_name!r}; "
            "do not reference any other schema. "
            "Return ONLY the SQL, no markdown, no explanation.\nSchema:\n" + ddl
        ),
        messages=[{"role": "user", "content": question}],
    )
    return msg.content[0].text.strip().strip("`").replace("sql\n", "", 1).strip()




if __name__ == "__main__":
    app = st.App("streamlit_app.py")
    app.run()

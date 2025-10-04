from __future__ import annotations

import re
import time
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import Table, text
from sqlalchemy.engine import Engine
from sqlalchemy.sql import Select
from sqlalchemy.sql import column, func, select
from sqlalchemy.sql import table as sa_table

from ..utils.cache import TTLCache
from ..utils.db import get_engine
from ..utils.logger import get_logger
from ..utils.state import AppState
from .schema_discovery import SchemaDiscovery

_logger = get_logger(__name__)


_SQL_KEYWORDS = {"count", "average", "avg", "sum", "list", "show", "top", "highest", "lowest", "by", "department", "salary", "hired", "join", "reports"}
_DOC_KEYWORDS = {"resume", "resumes", "document", "documents", "review", "reviews", "performance"}


class QueryEngine:
    def __init__(self, connection_string: str, app_state: AppState) -> None:
        self.connection_string = connection_string
        self.engine: Engine = get_engine(connection_string)
        self.schema = SchemaDiscovery().analyze_database(connection_string)
        self.cache: TTLCache = app_state.query_cache
        self.state = app_state

    def classify(self, user_query: str) -> str:
        q = user_query.lower()
        is_sql = any(k in q for k in _SQL_KEYWORDS)
        is_doc = any(k in q for k in _DOC_KEYWORDS)
        if is_sql and is_doc:
            return "hybrid"
        if is_doc:
            return "document"
        return "sql"

    def process_query(self, user_query: str) -> Dict[str, Any]:
        start = time.time()
        qtype = self.classify(user_query)
        cache_key = f"{qtype}:{user_query.strip().lower()}"
        hit, cached = self.cache.get(cache_key)
        if hit and cached is not None:
            result = {**cached, "performance_metrics": {**cached.get("performance_metrics", {}), "cache_hit": True, "took_ms": int((time.time() - start) * 1000)}}
            return result

        results: Dict[str, Any] = {"query_type": qtype}
        if qtype in ("sql", "hybrid"):
            try:
                sql_result = self._process_sql(user_query)
            except Exception as exc:  # noqa: BLE001
                sql_result = {"error": str(exc), "rows": []}
            results["sql"] = sql_result
        if qtype in ("document", "hybrid"):
            try:
                doc_result = self._process_documents(user_query)
            except Exception as exc:  # noqa: BLE001
                doc_result = {"error": str(exc), "chunks": []}
            results["documents"] = doc_result

        took_ms = int((time.time() - start) * 1000)
        results["performance_metrics"] = {"took_ms": took_ms, "cache_hit": False}

        # cache
        self.cache.set(cache_key, results)
        return results

    def _process_documents(self, user_query: str) -> Dict[str, Any]:
        vs = self.state.vector_store
        if vs is None or vs.size() == 0:
            return {"chunks": [], "note": "No documents indexed"}
        # Embed query using same embedding provider as DocumentProcessor via fallback hashing
        from .document_processor import EmbeddingProvider

        emb = EmbeddingProvider().embed_texts([user_query])[0]
        matches = vs.search(emb, top_k=5)
        chunks = [
            {
                "score": float(score),
                "text": md.get("text") or "",
                "doc": md,
            }
            for score, md in matches
        ]
        return {"chunks": chunks}

    def _process_sql(self, user_query: str) -> Dict[str, Any]:
        mapping = SchemaDiscovery().map_natural_language_to_schema(user_query, self.schema)
        emp_table = mapping.get("employee_table")
        if not emp_table:
            raise ValueError("Could not identify employee-like table")
        dept_table = mapping.get("department_table")
        salary_col = mapping.get("salary_column")
        hire_col = mapping.get("hire_date_column")
        name_col = mapping.get("name_column")
        reports_col = mapping.get("reports_to_column")
        dept_ref_col = mapping.get("dept_ref_column")

        q = user_query.lower()
        with self.engine.connect() as conn:
            if "how many" in q or q.strip().startswith("count"):
                sql = f"SELECT COUNT(*) as count FROM {emp_table}"
                rows = [dict(r._mapping) for r in conn.execute(text(sql))]
                return {"rows": rows, "sql": sql}

            if ("average" in q or "avg" in q) and "department" in q and dept_table and dept_ref_col and salary_col:
                sql = f"SELECT {dept_ref_col} as department, AVG({salary_col}) as average_salary FROM {emp_table} GROUP BY {dept_ref_col} ORDER BY average_salary DESC LIMIT 50"
                rows = [dict(r._mapping) for r in conn.execute(text(sql))]
                return {"rows": rows, "sql": sql}

            if ("hired" in q or "this year" in q or "join" in q) and hire_col:
                sql = f"SELECT * FROM {emp_table} WHERE strftime('%Y', {hire_col}) = strftime('%Y', 'now') LIMIT 100"
                # For non-SQLite, try year-based comparison
                try:
                    rows = [dict(r._mapping) for r in conn.execute(text(sql))]
                except Exception:
                    sql = f"SELECT * FROM {emp_table} WHERE EXTRACT(YEAR FROM {hire_col}) = EXTRACT(YEAR FROM CURRENT_DATE) LIMIT 100"
                    rows = [dict(r._mapping) for r in conn.execute(text(sql))]
                return {"rows": rows, "sql": sql}

            if "reports to" in q and reports_col and name_col:
                # Extract manager name
                m = re.search(r"reports to\s+(.+)$", q)
                manager_name = (m.group(1).strip() if m else "").strip("'\"")
                sql = f"SELECT * FROM {emp_table} WHERE {reports_col} LIKE :mgr LIMIT 100"
                rows = [dict(r._mapping) for r in conn.execute(text(sql), {"mgr": f"%{manager_name}%"})]
                return {"rows": rows, "sql": sql}

            if ("top" in q or "highest" in q) and "department" in q and salary_col and dept_ref_col:
                # extract N
                m = re.search(r"top\s+(\d+)", q)
                n = int(m.group(1)) if m else 5
                sql = (
                    "SELECT * FROM ("
                    f"SELECT *, ROW_NUMBER() OVER (PARTITION BY {dept_ref_col} ORDER BY {salary_col} DESC) as rn "
                    f"FROM {emp_table}) t WHERE rn <= :n"
                )
                rows = [dict(r._mapping) for r in conn.execute(text(sql), {"n": n})]
                return {"rows": rows, "sql": sql}

            if ("python" in q or "skill" in q) and salary_col:
                # heuristic: salary threshold
                m = re.search(r"over\s+(\d{2,6})", q)
                threshold = int(m.group(1)) if m else 100000
                # find likely skills column
                skills_col = None
                for c in self.schema["tables"][emp_table]["columns"].keys():
                    cl = c.lower()
                    if "skill" in cl or "keywords" in cl or "tags" in cl:
                        skills_col = c
                        break
                if skills_col is None:
                    # fallback: name or position contains Python
                    if name_col is None:
                        # pick any text-like column
                        skills_col = name_col or next(iter(self.schema["tables"][emp_table]["columns"].keys()))
                sql = f"SELECT * FROM {emp_table} WHERE {salary_col} >= :thr AND ({skills_col} LIKE :kw OR {name_col} LIKE :kw) ORDER BY {salary_col} DESC LIMIT 100"
                rows = [dict(r._mapping) for r in conn.execute(text(sql), {"thr": threshold, "kw": "%python%"})]
                return {"rows": rows, "sql": sql}

            # Default: list some employees
            cols = list(self.schema["tables"][emp_table]["columns"].keys())
            select_cols = ", ".join(cols[:6])
            sql = f"SELECT {select_cols} FROM {emp_table} LIMIT 50"
            rows = [dict(r._mapping) for r in conn.execute(text(sql))]
            return {"rows": rows, "sql": sql}

    def optimize_sql_query(self, sql: str) -> str:
        # Basic limit safeguard
        if " limit " not in sql.lower():
            sql += " LIMIT 100"
        return sql

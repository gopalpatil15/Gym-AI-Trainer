from __future__ import annotations

import re
from collections import defaultdict
from typing import Any, Dict, List, Optional

from sqlalchemy import MetaData, Table, inspect, text
from sqlalchemy.engine import Engine

from ..utils.db import get_engine
from ..utils.logger import get_logger

_logger = get_logger(__name__)


_EMPLOYEE_SYNONYMS = ["employee", "employees", "emp", "staff", "personnel", "people", "worker"]
_DEPT_SYNONYMS = ["dept", "department", "division", "team"]
_SALARY_SYNONYMS = ["salary", "compensation", "pay", "wage", "pay_rate", "annual_salary"]
_MANAGER_SYNONYMS = ["manager", "head", "lead", "reports_to"]
_HIRE_DATE_SYNONYMS = ["join_date", "hired_on", "start_date", "hire_date"]
_NAME_SYNONYMS = ["name", "full_name", "employee_name"]


class SchemaDiscovery:
    def analyze_database(self, connection_string: str) -> Dict[str, Any]:
        engine = get_engine(connection_string)
        inspector = inspect(engine)

        schema: Dict[str, Any] = {"tables": {}, "relationships": []}
        table_sample_data: Dict[str, List[Dict[str, Any]]] = {}

        for table_name in inspector.get_table_names():
            columns = inspector.get_columns(table_name)
            fks = inspector.get_foreign_keys(table_name)
            schema["tables"][table_name] = {
                "columns": {c["name"]: str(c.get("type")) for c in columns},
                "primary_key": [pk["constrained_columns"][0] for pk in inspector.get_pk_constraint(table_name).get("constrained_columns", [])] if inspector.get_pk_constraint(table_name) else [],
                "foreign_keys": [
                    {
                        "constrained_columns": fk.get("constrained_columns"),
                        "referred_table": fk.get("referred_table"),
                        "referred_columns": fk.get("referred_columns"),
                    }
                    for fk in fks
                ],
            }
            # Sample data (up to 3 rows)
            try:
                with engine.connect() as conn:
                    result = conn.execute(text(f"SELECT * FROM {table_name} LIMIT 3"))
                    rows = [dict(row._mapping) for row in result]
                    table_sample_data[table_name] = rows
            except Exception:  # noqa: BLE001
                table_sample_data[table_name] = []

        schema["samples"] = table_sample_data
        schema["hints"] = self._infer_table_purposes(schema)
        return schema

    def _infer_table_purposes(self, schema: Dict[str, Any]) -> Dict[str, str]:
        hints: Dict[str, str] = {}
        for t in schema["tables"].keys():
            lower = t.lower()
            if any(s in lower for s in _EMPLOYEE_SYNONYMS):
                hints[t] = "employees"
            elif any(s in lower for s in _DEPT_SYNONYMS):
                hints[t] = "departments"
            else:
                # Try to infer by columns
                cols = list(schema["tables"][t]["columns"].keys())
                if any(c.lower() in _NAME_SYNONYMS for c in cols) and any(c.lower() in _HIRE_DATE_SYNONYMS for c in cols):
                    hints[t] = "employees"
                elif any("dept" in c.lower() or "division" in c.lower() for c in cols):
                    hints[t] = "departments"
                else:
                    hints[t] = "unknown"
        return hints

    def map_natural_language_to_schema(self, query: str, schema: Dict[str, Any]) -> Dict[str, Any]:
        tokens = re.findall(r"[a-zA-Z_]+", query.lower())
        table_scores: Dict[str, int] = defaultdict(int)
        col_scores: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))

        for tname, tdata in schema.get("tables", {}).items():
            lower = tname.lower()
            for tok in tokens:
                if tok in lower:
                    table_scores[tname] += 2
            for col in tdata.get("columns", {}).keys():
                cl = col.lower()
                for tok in tokens:
                    if tok in cl:
                        col_scores[tname][col] += 2

        # Synonym boosts
        for tname, tdata in schema.get("tables", {}).items():
            cols = {c.lower(): c for c in tdata.get("columns", {}).keys()}
            if any(s in tname.lower() for s in _EMPLOYEE_SYNONYMS) or any(k in cols for k in _NAME_SYNONYMS):
                table_scores[tname] += 3
            if any(s in tname.lower() for s in _DEPT_SYNONYMS) or any("dept" in k or "division" in k for k in cols.keys()):
                table_scores[tname] += 2

            for syn in _SALARY_SYNONYMS:
                for k, orig in cols.items():
                    if syn in k:
                        col_scores[tname][orig] += 3
            for syn in _HIRE_DATE_SYNONYMS:
                for k, orig in cols.items():
                    if syn in k:
                        col_scores[tname][orig] += 3
            for syn in _NAME_SYNONYMS:
                for k, orig in cols.items():
                    if syn in k:
                        col_scores[tname][orig] += 2
            for syn in _MANAGER_SYNONYMS:
                for k, orig in cols.items():
                    if syn in k:
                        col_scores[tname][orig] += 2

        # Candidate tables
        ranked_tables = sorted(table_scores.items(), key=lambda x: x[1], reverse=True)
        candidate_employee_table = next((t for t, _ in ranked_tables if schema["hints"].get(t) == "employees"), (ranked_tables[0][0] if ranked_tables else None))
        candidate_dept_table = next((t for t, _ in ranked_tables if schema["hints"].get(t) == "departments"), None)

        # Best columns for common concepts
        def best_col_for(synonyms: List[str], table: Optional[str]) -> Optional[str]:
            if not table:
                return None
            scores = col_scores[table]
            if not scores:
                return None
            # choose highest scoring column among synonyms
            best = None
            best_score = -1
            for col, sc in scores.items():
                name = col.lower()
                if any(s in name for s in synonyms):
                    if sc > best_score:
                        best_score = sc
                        best = col
            if best is None:
                # fallback to highest scoring overall
                best = max(scores.items(), key=lambda x: x[1])[0]
            return best

        mapping = {
            "employee_table": candidate_employee_table,
            "department_table": candidate_dept_table,
            "salary_column": best_col_for(_SALARY_SYNONYMS, candidate_employee_table),
            "hire_date_column": best_col_for(_HIRE_DATE_SYNONYMS, candidate_employee_table),
            "name_column": best_col_for(_NAME_SYNONYMS, candidate_employee_table),
            "reports_to_column": best_col_for(_MANAGER_SYNONYMS, candidate_employee_table),
            "dept_ref_column": None,
        }

        # find column in employee table that references dept
        if candidate_employee_table and candidate_dept_table:
            emp_cols = list(schema["tables"][candidate_employee_table]["columns"].keys())
            for c in emp_cols:
                cl = c.lower()
                if "dept" in cl or "division" in cl or "department" in cl:
                    mapping["dept_ref_column"] = c
                    break

        mapping["_debug"] = {
            "table_scores": table_scores,
            "col_scores": {k: dict(v) for k, v in col_scores.items()},
        }
        return mapping

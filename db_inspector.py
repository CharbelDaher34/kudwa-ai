#%%
from sqlalchemy import create_engine, inspect, text
from typing import Dict, Any, List, Optional
from db import DATABASE_URL


class DatabaseInspector:
    def __init__(
        self,
        db_url: str = DATABASE_URL,
        skip_tables: List[str] = ["message", "conversation"],
        distinct_fields: Dict[str, List[str]] = {"financialstatement": ["account_name"]}
    ):
        """
        db_url: database URL
        skip_tables: list of table names to omit from schema output
        distinct_fields: mapping of table -> list of column names for which to fetch DISTINCT values
        """
        self.db_url = db_url
        self.skip_tables = set(skip_tables or [])
        self.distinct_fields = distinct_fields or {}
        self._engine = None
        self._inspector = None

    @property
    def engine(self):
        """Lazy initialization of database engine"""
        if self._engine is None:
            self._engine = create_engine(self.db_url)
        return self._engine

    @property
    def inspector(self):
        """Lazy initialization of database inspector"""
        if self._inspector is None:
            self._inspector = inspect(self.engine)
        return self._inspector

    def _is_safe_identifier(self, name: str) -> bool:
        """Basic whitelist check for table/column names (alphanumeric + underscore)."""
        return bool(name) and all(ch.isalnum() or ch == "_" for ch in name)

    def _get_distinct_values(self, table: str, column: str) -> List[Any]:
        """Return distinct values for table.column, empty list on error or if unsafe identifier."""
        if not (self._is_safe_identifier(table) and self._is_safe_identifier(column)):
            return []
        query = f"SELECT DISTINCT {column} FROM {table}"
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(query))
                rows = result.fetchall()
                return [row[0] for row in rows]
        except Exception:
            return []

    def get_tables_info(self) -> Dict[str, Any]:
        try:
            tables_info = {}
            for table_name in self.inspector.get_table_names():
                if table_name in self.skip_tables:
                    continue

                columns = self.inspector.get_columns(table_name)
                foreign_keys = self.inspector.get_foreign_keys(table_name)

                col_info = []
                col_names = {c['name'] for c in columns}
                for col in columns:
                    info = {
                        'name': col['name'],
                        'type': str(col['type']),
                        'nullable': col['nullable'],
                    }
                    # Extract description (from COMMENT, set by SQLModel's Field(description=...))
                    if col.get('comment'):
                        info['description'] = col['comment']

                    # If user requested distinct values for this table/column, fetch them
                    if table_name in self.distinct_fields:
                        requested = self.distinct_fields.get(table_name, [])
                        if col['name'] in requested:
                            info['distinct_values'] = self._get_distinct_values(table_name, col['name'])

                    col_info.append(info)

                # Extract relationships
                relationships = []
                for fk in foreign_keys:
                    local_col = fk['constrained_columns'][0]
                    ref_table = fk['referred_table']
                    ref_col = fk['referred_columns'][0]
                    relationships.append({
                        'from': local_col,
                        'to': f"{ref_table}.{ref_col}"
                    })

                tables_info[table_name] = {
                    'columns': col_info,
                    'relationships': relationships
                }
            return tables_info
        except Exception as e:
            # Return error information that can be useful for debugging
            return {
                'error': f"Failed to retrieve database schema: {str(e)}",
                'db_url_hint': self.db_url[:50] + "..." if len(self.db_url) > 50 else self.db_url
            }

    def print_select_info(self):
        """Prints schema info useful for writing SELECT queries."""
        info = self.get_tables_info()
        for table, data in info.items():
            print(f"\n📌 Table: {table}")
            print("  📄 Columns:")
            for col in data['columns']:
                null = "NULL" if col['nullable'] else "NOT NULL"
                desc = f" → {col['description']}" if 'description' in col else ""
                print(f"    • {col['name']} ({col['type']}, {null}){desc}")
                if 'distinct_values' in col:
                    vals = col['distinct_values']
                    sample = vals[:10]  # show up to 10 values
                    print(f"       ↳ distinct ({len(vals)}): {sample}")

            if data['relationships']:
                print("  🔗 Relationships:")
                for rel in data['relationships']:
                    print(f"    • {rel['from']} → {rel['to']}")
    def get_schema_text(self) -> str:
        """Returns the full database schema as a formatted text string."""
        info = self.get_tables_info()
        lines = []
        for table, data in info.items():
            lines.append(f"Table: {table}")
            lines.append("  Columns:")
            for col in data['columns']:
                null = "NULL" if col['nullable'] else "NOT NULL"
                desc = f" - {col['description']}" if 'description' in col else ""
                line = f"    {col['name']} ({col['type']}, {null}){desc}"
                lines.append(line)
                if 'distinct_values' in col:
                    vals = col['distinct_values']
                    lines.append(f"      Distinct values ({len(vals)}): {vals}")

            if data['relationships']:
                lines.append("  Relationships:")
                for rel in data['relationships']:
                    lines.append(f"    {rel['from']} → {rel['to']}")
            lines.append("")  # Blank line between tables
        return "\n".join(lines)
#%%
# Example usage:
if __name__ == "__main__":
    
    from db import DATABASE_URL
    try:
        # skip messages and conversation tables, and request distinct account_name values
        inspector = DatabaseInspector(
            DATABASE_URL,
            skip_tables=["message", "conversation"],
            distinct_fields={"financialstatement": ["account_name"]},
        )

        # Print schema information
        print(inspector.get_schema_text())
    except Exception as e:
        print(f"Error: {e}")
# %%

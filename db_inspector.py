from sqlalchemy import create_engine, inspect
from typing import Dict, Any
from sqlalchemy import create_engine, inspect
from typing import Dict, Any

class DatabaseInspector:
    def __init__(self, db_url: str):
        self.engine = create_engine(db_url)
        self.inspector = inspect(self.engine)

    def get_tables_info(self) -> Dict[str, Any]:
        tables_info = {}
        for table_name in self.inspector.get_table_names():
            columns = self.inspector.get_columns(table_name)
            foreign_keys = self.inspector.get_foreign_keys(table_name)

            col_info = []
            for col in columns:
                info = {
                    'name': col['name'],
                    'type': str(col['type']),
                    'nullable': col['nullable'],
                }
                # Extract description (from COMMENT, set by SQLModel's Field(description=...))
                if col.get('comment'):
                    info['description'] = col['comment']
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
                lines.append(f"    {col['name']} ({col['type']}, {null}){desc}")

            if data['relationships']:
                lines.append("  Relationships:")
                for rel in data['relationships']:
                    lines.append(f"    {rel['from']} → {rel['to']}")
            lines.append("")  # Blank line between tables
        return "\n".join(lines)
# Example usage:
if __name__ == "__main__":
    from db import DATABASE_URL

    
    try:
        inspector = DatabaseInspector(DATABASE_URL)

        # Print schema information
        inspector.print_select_info()
    except Exception as e:
        print(f"Error: {e}")
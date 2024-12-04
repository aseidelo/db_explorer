from sqlalchemy import (
    event,
    Engine
)


def enforce_read_only(engine: Engine):
    """
    Configura o SQLAlchemy para lançar exceções em qualquer tentativa de escrita.
    Funciona para qualquer banco de dados suportado pelo SQLAlchemy.
    
    Args:
        engine: Uma instância SQLAlchemy Engine.
    """
    @event.listens_for(engine, "before_cursor_execute")
    def block_write_operations(conn, cursor, statement, parameters, context, executemany):
        if statement.strip().upper().startswith(("INSERT", "UPDATE", "DELETE", "CREATE", "DROP", "ALTER")):
            raise Exception("Operações de escrita não são permitidas: Somente leitura está habilitado.")

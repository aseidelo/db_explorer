import json
from sqlalchemy import (
    create_engine,
    MetaData,
    text
)
import pandas as pd
from db.templates import DBData
from db.utils import (
    enforce_read_only
)


class Db:
    def __init__(
            self,
            type: str,
            db_name: str,
            username: str = None,
            password: str = None, 
            host: str = None,
            port: str = None) -> None:

        self.type = type
        self.db_name = db_name
        self.engine = None
        self.metadata = None
        self.set_connection_url(username, password, host, port)

        self.connect(self.type, self.db_name, username, password, host, port)

        if self.is_connected():
            self.fetch_metadata()

    def is_connected(self):
        return self.engine is not None

    def set_connection_url(
            self,
            username: str = None,
            password: str = None, 
            host: str = None,
            port: str = None) -> bool:

        if self.type == "sqlite":
            # Conexão para SQLite
            self.connection_url = f"sqlite:///{self.db_name}"
        elif self.type == "mysql":
            assert username is not None
            assert password is not None
            assert host is not None
            assert port is not None
            # Conexão para MySQL
            self.connection_url = f"mysql+pymysql://{username}:{password}@{host}:{port}/{self.db_name}"
        elif self.type == "postgres":
            assert username is not None
            assert password is not None
            assert host is not None
            assert port is not None
            # Conexão para PostgreSQL
            self.connection_url = f"postgresql+psycopg2://{username}:{password}@{host}:{port}/{self.db_name}"
        else:
            raise ValueError("Tipo de banco de dados inválido. Use 'sqlite', 'mysql' ou 'postgres'.")

    def connect(
            self,
            type: str,
            db_name: str,
            username: str = None,
            password: str = None, 
            host: str = None,
            port: str = None) -> bool:
        """
        Cria uma engine SQLAlchemy para SQLite, MySQL ou PostgreSQL e retorna.
        
        Args:
            type (str): Tipo de banco de dados ('sqlite', 'mysql', 'postgres').
            db_name (str): Nome do banco de dados ou caminho do arquivo para SQLite.
            username (str): Nome de usuário (não usado para SQLite).
            password (str): Senha do usuário (não usado para SQLite).
            host (str): Endereço do host (não usado para SQLite).
            port (int or str): Porta do banco de dados (não usado para SQLite).
        Returns:
            bool: Se conexão funcionou
        """
        try:
            if type == "sqlite":
                # Conexão para SQLite
                self.connection_url = f"sqlite:///{db_name}"
            elif type == "mysql":
                # Conexão para MySQL
                self.connection_url = f"mysql+pymysql://{username}:{password}@{host}:{port}/{db_name}"
            elif type == "postgres":
                # Conexão para PostgreSQL
                self.connection_url = f"postgresql+psycopg2://{username}:{password}@{host}:{port}/{db_name}"
            else:
                raise ValueError("Tipo de banco de dados inválido. Use 'sqlite', 'mysql' ou 'postgres'.")

            # Criar a engine
            self.engine = create_engine(self.connection_url)

            # tenta uma primeira conexão
            self.engine.connect()

            # garante que totas as operações serão só de leitura
            enforce_read_only(self.engine)

            return True
        except Exception as e:
            self.engine = None
            print(e)
            return False

    def fetch_metadata(self):
        metadata_dict = {
            'name': self.db_name,
            'tables': []
        }

        # Configurar e refletir metadados
        metadata = MetaData()
        metadata.reflect(bind=self.engine)

        if self.type == "postgres":
            metadata_dict['description'] = self.__get_db_description_pgsql()
        elif self.type == "mysql":
            metadata_dict['description'] = self.__get_db_description_mysql()
        else:
            metadata_dict['description'] = None

        for table_name, table in metadata.tables.items():
            table_dict = {
                'name': table_name,
                'description': table.comment,
                'columns': []
            }

            for column in table.columns:
                column_dict = {
                    'name': column.name,
                    'type': str(column.type),
                    'description': column.comment
                }
                table_dict['columns'].append(column_dict)
            
            metadata_dict['tables'].append(table_dict)
        
        self.metadata = DBData(**metadata_dict)

    def __get_db_description_pgsql(self):
        # Recuperar o comentário do banco de dados
        with self.engine.connect() as connection:
            result = connection.execute(
                text("SELECT description FROM pg_shdescription "
                    "WHERE objoid = (SELECT oid FROM pg_database WHERE datname = :dbname)"),
                {"dbname": self.db_name}
            ).fetchone()
        if result:
            return result[0]
        return None

    def __get_db_description_mysql(self):
        # Recuperar o comentário do banco de dados
        with self.engine.connect() as connection:
            result = connection.execute(
                text("SELECT SCHEMA_COMMENT FROM information_schema.schemata WHERE SCHEMA_NAME = :dbname"),
                {"dbname": self.db_name}
            ).fetchone()
        if result:
            return result['SCHEMA_COMMENT']
        return None
    
    def json(self):
        return self.metadata.model_dump_json()

    def full_description(self) -> str:
        return {
            'db_name': self.db_name,
            'db_type': self.type,
            'db_description': self.metadata.description,
            'tables': [
                {
                    'name': table.name,
                    'description': table.description,
                    'columns': [
                        {
                            'name': col.name,
                            'data_type': col.type,
                            'description': col.description
                        }
                        for col in table.columns
                    ]
                }
                for table in self.metadata.tables
            ]
        }

    def short_description(self) -> str:
        return {
            'db_name': self.db_name,
            'db_type': self.type,
            'db_description': self.metadata.description,
            'tables': [
                {
                    'name': table.name,
                    'description': table.description
                }
                for table in self.metadata.tables
            ]
        }

    def query(self, sql_query: str, parameters: dict):
        with self.engine.connect() as conn:
            df = pd.read_sql(text(sql_query), conn, params=parameters)
            # result = conn.execute(text(sql_query), parameters)
            # json_result = json.dumps([dict(row) for row in result], indent=4)
            return df


if __name__ == '__main__':
    connection_data = {
        'type': 'postgres',
        'db_name': 'futebol_brasileiro',
        'username': 'postgres',
        'password': '2626',
        'host': 'localhost',
        'port': '5432'
    }
    db = Db(**connection_data)

    print(db)

import sys
from pathlib import Path
from typing import Literal

import pandas as pd
from loguru import logger
from sqlalchemy.engine.base import Engine
from sqlalchemy.sql.schema import MetaData

from data.config import FILES_DIR
from utils.db_api.db import DB


def load_all_database_url():
    files_dir = Path(FILES_DIR)
    databases = list(files_dir.glob("*.db"))
    if not databases:
        raise FileNotFoundError("Не найдены базы данных для экспорта, проверьте что база данных инициализирована.")
    return [str(database) for database in databases]


class CSVExporter:
    def __init__(
        self,
        database_type: Literal["sqlite"] = "sqlite",
        export_private_keys: bool = False,
        mode: Literal["overwrite", "suffix", "merge"] = "overwrite",
    ):
        self.mode = mode
        self.export_private_keys = export_private_keys
        self.output_dir: Path = Path(FILES_DIR)
        self.database_type = database_type
        try:
            self._database_urls = load_all_database_url()
        except FileNotFoundError as e:
            logger.error("Ошибка при инициализации класса экспортера: {0}", e)
            sys.exit(1)

    def __call__(self, *args, **kwargs):
        return self.process_model_to_export()

    def _connect_to_db(self, database_url: str) -> DB:
        try:
            return DB(db_url=database_url)
        except Exception as e:
            logger.error("Failed to connect to database: {0}", e)
            return None

    def read_model_to_export(
        self,
        database_url: str,
    ):
        database = self._connect_to_db(database_url)
        if database is None:
            logger.error("Database connection failed. Going next")
            return None
        metadata = MetaData()
        metadata.reflect(bind=database.engine)
        tables = metadata.tables
        if not tables:
            logger.error("Failed to find tables in database.")
        return self.export_to_csv(tables, database.engine, database_url)

    def export_to_csv(self, table: dict[str, str], engine: Engine, database_url: str) -> bool:
        logger.debug("Start export to CSV")
        success = False
        db_name = self._change_csv_table_name_if_exists(database_url)

        for table_name, table_data in table.items():
            df = pd.read_sql_table(table_name, engine)

            if not self.export_private_keys:
                logger.debug("Trying delete private keys")
                df = df.drop(columns=["private_key"], errors="ignore")

            # === Логика выбора пути в зависимости от режима ===
            if self.mode == "overwrite":
                csv_path = self.output_dir / f"{table_name}.csv"

            elif self.mode == "suffix":
                csv_path = self.output_dir / f"{table_name}_{db_name}.csv"

            elif self.mode == "merge":
                df["source_db"] = db_name
                csv_path = self.output_dir / f"{table_name}.csv"
            else:
                raise ValueError(f"Unknown mode: {self.mode}")

            # === Сохранение ===
            if self.mode == "merge" and csv_path.exists():
                logger.debug("Appending to existing CSV {0}", csv_path)
                df.to_csv(csv_path, mode="a", header=False, index=False)
            else:
                logger.debug("Writing CSV to {0}", csv_path)
                df.to_csv(csv_path, index=False)

            logger.debug("CSV exported to: {csv_path}", csv_path=csv_path)
            success = True

        return success

    def _change_csv_table_name_if_exists(self, database_url: str):
        name_by_list = database_url.split("/")
        file_name = name_by_list[-1]
        if file_name.find(".db") != -1:
            file_name = file_name[: file_name.find(".db")]
        return file_name

    def process_model_to_export(
        self,
    ):
        database_urls = load_all_database_url()
        if self.database_type == "sqlite":
            database_urls = [f"sqlite:///{database_url}" for database_url in database_urls]
            logger.debug("Prepare urls to connect: {0}", database_urls)
        results = []
        for database_url in database_urls:
            results.append(self.read_model_to_export(database_url))
        return results, self.output_dir


def export_to_csv(
    export_private_keys: bool,
    mode: Literal["overwrite", "suffix", "merge"] = "overwrite",
):
    result, export_patch = CSVExporter(
        export_private_keys=export_private_keys,
        mode=mode,
    )()
    return all(result), export_patch

import logging
import os

from sqlalchemy import text
from sqlalchemy.engine import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.sql.schema import Column, MetaData, Table
from sqlalchemy.types import String

from etl.exceptions import ImproperlyConfigured

# Configure the connection to our data store.
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL is None:
    raise ImproperlyConfigured("You must supply DATABASE_URL.")

# https://docs.sqlalchemy.org/en/14/core/engines.html
engine = create_engine(DATABASE_URL)

logger = logging.getLogger(__name__)


def create_schema() -> None:
    """Create the database schema."""
    metadata_obj = MetaData()

    processed_uuids = Table(
        "processed_uuids",
        metadata_obj,
        Column("uuid", String(36), primary_key=True),
    )

    metadata_obj.create_all(engine)


def import_uuids_from_set(uuids: set[str]) -> None:
    """Import processed UUIDs into the database."""
    with Session(engine) as session:
        session.execute(
            text("INSERT INTO processed_uuids (uuid) VALUES (:uuid)"),
            [{"uuid": uuid} for uuid in uuids],
        )
        session.commit()


def get_all_processed_uuids() -> list[str]:
    """Get a list of all processed UUIDs."""
    with Session(engine) as session:
        result = session.execute(text("SELECT uuid FROM processed_uuids"))
        return result.scalars().all()

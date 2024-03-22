import logging
import os

from sqlalchemy import text
from sqlalchemy.engine import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.sql.schema import Column, MetaData, Table
from sqlalchemy.types import CHAR

from image_deid_etl.exceptions import ImproperlyConfigured

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
        # Orthanc uses the term "UUID" when referring to a study, but this is
        # misleading. Orthanc actually derives identifiers from an SHA-1 hash.
        # https://github.com/jodogne/OrthancMirror/blob/305b1798a9c90adc128fcbcdd6a357fa9a547498/OrthancFramework/Sources/Toolbox.cpp#L750-L775
        Column("uuid", CHAR(45), primary_key=True),
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

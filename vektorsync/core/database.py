import json
from datetime import datetime, timezone
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = "sqlite:///./vektorsync_ledger.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_utc_now():
    return datetime.now(timezone.utc)

class DocumentLedger(Base):
    __tablename__ = "document_ledger"

    id = Column(String(64), primary_key=True, index=True)
    version = Column(Integer, default=1, nullable=False)
    vector_clock = Column(Text, default="{}", nullable=False)
    data_payload = Column(Text, default="{}", nullable=False)
    last_modified_by = Column(String(64), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=get_utc_now, onupdate=get_utc_now)

class MutationJournal(Base):
    __tablename__ = "mutation_journal"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(String(64), index=True, nullable=False)
    client_id = Column(String(64), nullable=False)
    idempotency_key = Column(String(128), unique=True, index=True, nullable=False)
    sync_result = Column(String(64), nullable=False)
    payload_snapshot = Column(Text, nullable=False)
    recorded_at = Column(DateTime(timezone=True), default=get_utc_now)

class SnapshotLedger(Base):
    __tablename__ = "snapshot_ledger"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(String(64), index=True, nullable=False)
    version = Column(Integer, nullable=False)
    data_payload = Column(Text, nullable=False)
    vector_clock = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=get_utc_now)

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
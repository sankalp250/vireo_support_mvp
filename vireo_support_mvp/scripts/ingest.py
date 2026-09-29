from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.core.config import get_settings
from app.db.session import SessionLocal, init_db
from app.services.ingest import load_csv

settings=get_settings(); init_db(); db=SessionLocal()
try:
    path=Path(settings.data_dir)/"tickets.csv"
    n=load_csv(db,str(path),replace=True)
    print(f"Imported {n} tickets from {path}")
finally: db.close()

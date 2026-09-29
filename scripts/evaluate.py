from pathlib import Path
import sys
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.db.session import SessionLocal
from app.db.models import ReviewLabel, Classification
from app.services.analytics import evaluation
from app.schemas.classification import CATEGORIES

sample=Path("review_sample.csv")
if not sample.exists():
    raise SystemExit("review_sample.csv not found")
df=pd.read_csv(sample).fillna("")
missing=df[~df.gold_category.isin(CATEGORIES)]
if not missing.empty:
    raise SystemExit(f"{len(missing)} rows still need a valid manually reviewed gold_category")
db=SessionLocal()
try:
    db.query(ReviewLabel).delete(); db.commit()
    for _,r in df.iterrows():
        db.add(ReviewLabel(ticket_id=r.ticket_id,gold_category=r.gold_category,reviewer="manual"))
    db.commit()
    print(evaluation(db))
finally:
    db.close()

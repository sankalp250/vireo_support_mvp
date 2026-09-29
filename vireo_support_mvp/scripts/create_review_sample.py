from pathlib import Path
import sys
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.services.ticket_logic import normalize_timestamps, apply_analysis_window
from app.core.config import get_settings

settings=get_settings(); path=Path(settings.data_dir)/"tickets.csv"
df=apply_analysis_window(normalize_timestamps(pd.read_csv(path)))
sample=(df.groupby("category", group_keys=False).apply(lambda x:x.sample(n=min(len(x),20), random_state=42)).reset_index(drop=True))
cols=["ticket_id","channel","category","customer_message","agent_notes"]
out=sample[cols].rename(columns={"category":"suggested_category"})
out.insert(2,"gold_category","")
out.to_csv("review_sample.csv",index=False)
print(f"Created review_sample.csv with {len(sample)} tickets. Manually fill gold_category; suggested_category is only the existing weak tag.")

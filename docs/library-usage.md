# Data/ML Library Usage

## Pandas

Pandas is a core part of ingestion, cleaning, timestamp normalization, filtering, aggregation, profiling, and evaluation preparation.

## NumPy

NumPy is used directly by `scripts/profile_data.py` for numeric profiling and percentile calculations.

## Matplotlib

Matplotlib is used by `scripts/profile_data.py` to generate lightweight data-quality/EDA charts outside the API runtime.

## Seaborn

Seaborn is intentionally not required. The MVP only needs a small number of diagnostic plots, so Matplotlib is sufficient and keeps the dependency surface smaller.

## Scikit-learn

Used for accuracy, macro-F1, and confusion matrix evaluation after human labels are supplied.

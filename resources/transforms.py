# resources/transforms.py
from pyspark.sql import DataFrame
from pyspark.sql.functions import col

def normalize_types(df: DataFrame) -> DataFrame:
    cast_cols = []
    if "id" in df.columns:
        cast_cols.append(col("id").cast("long").alias("id"))
    if "ts" in df.columns:
        cast_cols.append(col("ts").cast("timestamp").alias("ts"))
    passthrough = [c for c in df.columns if c not in ("id", "ts")]
    return df.select(*(cast_cols + [col(c) for c in passthrough]))
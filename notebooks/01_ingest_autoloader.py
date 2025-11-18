# Databricks notebook source
# notebooks/01_ingest_autoloader.py
import os, yaml
from pyspark.sql.functions import input_file_name, current_timestamp

# COMMAND ----------

# --- Load config ---
config_path = os.environ.get("CONFIG_PATH", "/Workspace/Users/alan.silva@databricks.com/Customers/spdji/autoloader-demo/configs/dev.yaml")
with open(config_path, "r") as f:
    cfg = yaml.safe_load(f)

source_url            = cfg["source_url"]            # /Volumes/... path
checkpoint_path       = cfg["checkpoint_path"]       # /Volumes/... path
target_table          = cfg["target_table"]
file_format           = cfg.get("file_format", "json")
detection_mode        = cfg.get("detection_mode", "directory")
infer_column_types    = cfg.get("infer_column_types", True)
schema_evolution_mode = cfg.get("schema_evolution_mode", "addNewColumns")

# COMMAND ----------

# --- Build Auto Loader reader ---
reader = (
    spark.readStream
         .format("cloudFiles")
         .option("cloudFiles.format", file_format)
         .option("cloudFiles.schemaLocation", checkpoint_path)       # enables schema inference/evolution tracking
         .option("cloudFiles.schemaEvolutionMode", schema_evolution_mode)
)

# COMMAND ----------

# Typed inference for JSON/CSV/XML (otherwise these infer as strings by default)
if infer_column_types:
    reader = reader.option("cloudFiles.inferColumnTypes", True)

# Detection modes (Volumes default = directory listing)
if detection_mode == "useNotifications":
    reader = reader.option("cloudFiles.useNotifications", True)      # legacy notifications per stream (external locations)
elif detection_mode == "fileEvents":
    reader = reader.option("cloudFiles.useManagedFileEvents", True)  # UC file events (external locations only)

df = reader.load(source_url) \
           .withColumn("_file_path", input_file_name()) \
           .withColumn("_ingest_ts", current_timestamp())

# COMMAND ----------

import sys

# Add the absolute path to your resources directory
sys.path.insert(
    0,
    "/Workspace/Users/alan.silva@databricks.com/Customers/spdji/autoloader-demo/resources"
)

# COMMAND ----------

from transforms import normalize_types
df2 = normalize_types(df)

query = (
    df2.writeStream
       .option("checkpointLocation", checkpoint_path)
       .toTable(target_table)
)
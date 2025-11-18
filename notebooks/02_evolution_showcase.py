# Databricks notebook source
import os, yaml
from pyspark.sql.functions import input_file_name

config_path = os.environ.get("CONFIG_PATH", "//Workspace/Users/alan.silva@databricks.com/Customers/spdji/autoloader-demo/configs/dev.yaml")
with open(config_path, "r") as f:
    cfg = yaml.safe_load(f)

# COMMAND ----------

reader = (
    spark.readStream
         .format("cloudFiles")
         .option("cloudFiles.format", cfg.get("file_format", "json"))
         .option("cloudFiles.schemaLocation", cfg["checkpoint_path"])
         .option("cloudFiles.inferColumnTypes", cfg.get("infer_column_types", True))
         .option("cloudFiles.schemaEvolutionMode", cfg.get("schema_evolution_mode", "addNewColumns"))
)

mode = cfg.get("detection_mode", "directory")
if mode == "useNotifications":
    reader = reader.option("cloudFiles.useNotifications", True)
elif mode == "fileEvents":
    reader = reader.option("cloudFiles.useManagedFileEvents", True)

df = reader.load(cfg["source_url"]).withColumn("_file_path", input_file_name())

(df.writeStream
   .option("checkpointLocation", cfg["checkpoint_path"])
   .toTable(cfg["target_table"]))
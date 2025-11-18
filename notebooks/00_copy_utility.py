# Databricks notebook source
# From a notebook cell
# Ensure these paths match your dev.yaml
base = "/Volumes/acs/autoloader/autoloader_demo/raw/events/"

dbutils.fs.mkdirs(base + "batch_01/")
dbutils.fs.mkdirs(base + "batch_02/")
dbutils.fs.mkdirs(base + "batch_03_drift/")

# Copy local files to Volumes (replace <local_path>)
dbutils.fs.cp(
    "file:/Workspace/Users/alan.silva@databricks.com/Customers/spdji/autoloader-demo/sample_data/batch_01/file_0001.json",
    base + "batch_01/file_0001.json"
)
dbutils.fs.cp(
    "file:/Workspace/Users/alan.silva@databricks.com/Customers/spdji/autoloader-demo/sample_data/batch_01/file_0002.json",
    base + "batch_01/file_0002.json"
)
dbutils.fs.cp(
    "file:/Workspace/Users/alan.silva@databricks.com/Customers/spdji/autoloader-demo/sample_data/batch_02/file_0003.json",
    base + "batch_02/file_0003.json"
)
# Later, copy drift:
dbutils.fs.cp(
    "file:/Workspace/Users/alan.silva@databricks.com/Customers/spdji/autoloader-demo/sample_data/batch_03_drift/file_0004.json",
    base + "batch_03_drift/file_0004.json"
)
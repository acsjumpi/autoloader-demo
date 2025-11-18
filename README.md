# Auto Loader Demo

This project demonstrates **Databricks Auto Loader** (`cloudFiles` format) for incremental file ingestion with automatic schema inference and evolution. It showcases best practices for building production-ready data pipelines using Unity Catalog Volumes, configuration-driven notebooks, and programmatic job creation.

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Project Structure](#project-structure)
4. [Key Features](#key-features)
5. [Configuration](#configuration)
6. [Notebooks](#notebooks)
7. [Transformations](#transformations)
8. [Setup Instructions](#setup-instructions)
9. [Execution Steps](#execution-steps)
10. [Schema Evolution](#schema-evolution)
11. [Detection Modes](#detection-modes)
12. [Job Automation](#job-automation)
13. [Sample Data](#sample-data)
14. [Troubleshooting](#troubleshooting)

---

## Overview

**Auto Loader** is Databricks' optimized file ingestion tool that:
- Automatically detects and processes new files as they arrive
- Infers schema and handles schema evolution
- Provides exactly-once processing guarantees
- Scales efficiently from small to large workloads

This demo project shows how to:
- Configure Auto Loader with YAML files
- Handle schema changes without pipeline failures
- Apply custom transformations during ingestion
- Deploy pipelines as scheduled Databricks jobs

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Source Data                                 │
│     Unity Catalog Volume: /Volumes/.../raw/events/                  │
│                 (JSON files arrive incrementally)                   │
└────────────────────────┬────────────────────────────────────────────┘
                         │
                         │ Auto Loader monitors for new files
                         │ (directory listing, notifications, or file events)
                         │
┌────────────────────────▼────────────────────────────────────────────┐
│                    Auto Loader Reader                               │
│  • Schema inference (cloudFiles.inferColumnTypes)                   │
│  • Schema evolution (addNewColumns mode)                            │
│  • Checkpoint tracking (/Volumes/.../checkpoints/)                  │
└────────────────────────┬────────────────────────────────────────────┘
                         │
                         │ Streaming DataFrame
                         │
┌────────────────────────▼────────────────────────────────────────────┐
│                    Custom Transforms                                │
│  • Type normalization (id → long, ts → timestamp)                   │
│  • Add metadata columns (_file_path, _ingest_ts)                    │
└────────────────────────┬────────────────────────────────────────────┘
                         │
                         │ Transformed DataFrame
                         │
┌────────────────────────▼────────────────────────────────────────────┐
│                     Delta Lake Table                                │
│         Unity Catalog: acs.autoloader.raw_events                    │
│              (ACID transactions, time travel)                       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Project Structure

```
autoloader-demo/
│
├── configs/
│   └── dev.yaml                          # Configuration for dev environment
│
├── notebooks/
│   ├── 00_copy_utility.py                # Helper to copy sample files to Volumes
│   ├── 01_ingest_autoloader.py           # Main Auto Loader ingestion pipeline
│   ├── 02_evolution_showcase.py          # Minimal schema evolution example
│   └── 03_job_creation.py                # Programmatic job creation with SDK
│
├── resources/
│   └── transforms.py                     # Reusable transformation functions
│
├── sample_data/
│   ├── batch_01/                         # Initial schema (id, ts, val)
│   │   ├── file_0001.json
│   │   └── file_0002.json
│   ├── batch_02/                         # Same schema
│   │   └── file_0003.json
│   └── batch_03_drift/                   # Schema evolution (adds new_col)
│       └── file_0004.json
│
└── README.md                             # This file
```

---

## Key Features

| Feature | Description |
|---------|-------------|
| **Auto Loader** | Incremental file processing with automatic detection |
| **Schema Inference** | Automatically infers column types from JSON/CSV/XML |
| **Schema Evolution** | Handles new columns without pipeline failures |
| **Unity Catalog** | Uses UC Volumes for governed storage |
| **Configuration-Driven** | YAML-based config for easy environment management |
| **Custom Transforms** | Modular Python functions for data transformations |
| **Metadata Tracking** | Adds `_file_path` and `_ingest_ts` columns |
| **Checkpoint Management** | Ensures exactly-once processing semantics |
| **Multiple Detection Modes** | Directory, notifications, or file events |

---

## Configuration

Configuration is managed via YAML files in the `configs/` directory.

### Example: `configs/dev.yaml`

```yaml
# Source location (Unity Catalog Volume path)
source_url: "/Volumes/acs/autoloader/autoloader_demo/raw/events/"

# Checkpoint location (tracks processed files and schema)
checkpoint_path: "/Volumes/acs/autoloader/autoloader_demo/checkpoints/autoloader_demo"

# Target Delta table (Unity Catalog)
target_table: "acs.autoloader.raw_events"

# File format: json, csv, parquet, xml, avro
file_format: "json"

# Detection mode: directory | useNotifications | fileEvents
detection_mode: "directory"

# Enable typed inference for JSON/CSV/XML (otherwise strings)
infer_column_types: true

# Schema evolution mode: addNewColumns | rescue | none | failOnNewColumns
schema_evolution_mode: "addNewColumns"
```

### Configuration Parameters

| Parameter | Options | Description |
|-----------|---------|-------------|
| `source_url` | Path | Unity Catalog Volume or cloud storage path |
| `checkpoint_path` | Path | Location to store Auto Loader state |
| `target_table` | Catalog.schema.table | Destination Delta table |
| `file_format` | json, csv, parquet, xml, avro | Input file format |
| `detection_mode` | directory, useNotifications, fileEvents | How Auto Loader detects new files |
| `infer_column_types` | true/false | Type inference for JSON/CSV/XML |
| `schema_evolution_mode` | addNewColumns, rescue, none, failOnNewColumns | How to handle schema changes |

---

## Notebooks

### 1. `00_copy_utility.py`

**Purpose**: Helper utility to copy sample data files to Unity Catalog Volumes.

**Usage**:
```python
# Run this notebook first to set up sample data
# Copies files from sample_data/ to the configured source_url
```

**When to use**: Initial setup or when adding new sample files for testing.

---

### 2. `01_ingest_autoloader.py`

**Purpose**: Main production ingestion pipeline using Auto Loader.

**What it does**:
1. Loads configuration from YAML
2. Configures Auto Loader with schema inference and evolution
3. Reads streaming data from source Volume
4. Applies custom type normalization transforms
5. Adds metadata columns (`_file_path`, `_ingest_ts`)
6. Writes to Delta Lake table with checkpoint tracking

**Key Code Flow**:
```python
# 1. Load config
config_path = os.environ.get("CONFIG_PATH", "/Workspace/.../configs/dev.yaml")
cfg = yaml.safe_load(open(config_path))

# 2. Build Auto Loader reader
reader = (
    spark.readStream
         .format("cloudFiles")
         .option("cloudFiles.format", file_format)
         .option("cloudFiles.schemaLocation", checkpoint_path)
         .option("cloudFiles.schemaEvolutionMode", schema_evolution_mode)
)

# 3. Load and transform
df = reader.load(source_url) \
           .withColumn("_file_path", input_file_name()) \
           .withColumn("_ingest_ts", current_timestamp())

from transforms import normalize_types
df2 = normalize_types(df)

# 4. Write to Delta
query = (
    df2.writeStream
       .option("checkpointLocation", checkpoint_path)
       .toTable(target_table)
)
```

**Environment Variables**:
- `CONFIG_PATH`: Override default config location

---

### 3. `02_evolution_showcase.py`

**Purpose**: Minimal example demonstrating schema evolution capabilities.

**What it demonstrates**:
- Simplified Auto Loader setup
- Schema evolution handling with `addNewColumns` mode
- Direct streaming write without custom transforms

**Use case**: Learning and testing schema evolution behavior.

---

### 4. `03_job_creation.py`

**Purpose**: Programmatically create Databricks jobs using the SDK.

**What it does**:
```python
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.jobs import Task, NotebookTask, Source

w = WorkspaceClient()

job = w.jobs.create(
    name="autoloader-demo-job",
    tasks=[
        Task(
            task_key="ingest",
            notebook_task=NotebookTask(
                notebook_path="/Workspace/.../01_ingest_autoloader",
                base_parameters={},
                source=Source("WORKSPACE")
            ),
            existing_cluster_id="0908-155147-maxf059n"
        )
    ]
)
print(job.job_id)
```

**When to use**: Automating job deployment for CI/CD pipelines or multi-environment setups.

---

## Transformations

Custom transformations are defined in `resources/transforms.py` for reusability.

### `normalize_types(df: DataFrame) -> DataFrame`

**Purpose**: Cast specific columns to appropriate types.

**Implementation**:
```python
from pyspark.sql import DataFrame
from pyspark.sql.functions import col

def normalize_types(df: DataFrame) -> DataFrame:
    """
    Normalizes column types:
    - id: cast to long
    - ts: cast to timestamp
    - Other columns: passed through unchanged
    """
    cast_cols = []

    if "id" in df.columns:
        cast_cols.append(col("id").cast("long").alias("id"))

    if "ts" in df.columns:
        cast_cols.append(col("ts").cast("timestamp").alias("ts"))

    passthrough = [c for c in df.columns if c not in ("id", "ts")]

    return df.select(*(cast_cols + [col(c) for c in passthrough]))
```

**Why this matters**:
- JSON files infer numeric types as strings by default (if `inferColumnTypes` is false)
- Explicit casting ensures correct data types in Delta Lake
- Centralized transformation logic for consistency

**Extending transforms**:
Add more functions to `transforms.py` as needed:
```python
def enrich_with_country(df: DataFrame) -> DataFrame:
    # Add geolocation lookups, business logic, etc.
    pass
```

---

## Setup Instructions

### Prerequisites

1. **Databricks Workspace** with Unity Catalog enabled
2. **Unity Catalog Volume** for storing raw files and checkpoints
3. **Databricks Runtime** 13.3 LTS or higher (with Auto Loader support)
4. **Permissions**:
   - READ on source Volume
   - WRITE on target catalog/schema
   - CREATE TABLE on target schema

### Step-by-Step Setup

#### 1. Create Unity Catalog Resources

```sql
-- Create catalog (if needed)
CREATE CATALOG IF NOT EXISTS acs;

-- Create schema
CREATE SCHEMA IF NOT EXISTS acs.autoloader;

-- Create volumes for data storage
CREATE VOLUME IF NOT EXISTS acs.autoloader.autoloader_demo;
```

#### 2. Upload Project Files to Workspace

Upload the entire project directory to your Databricks Workspace:
```
/Workspace/Users/<your-email>/Customers/spdji/autoloader-demo/
```

Or use Databricks CLI:
```bash
databricks workspace import-dir ./autoloader-demo \
  /Workspace/Users/<your-email>/Customers/spdji/autoloader-demo
```

#### 3. Configure Environment

Edit `configs/dev.yaml` to match your environment:
```yaml
source_url: "/Volumes/<catalog>/<schema>/<volume>/raw/events/"
checkpoint_path: "/Volumes/<catalog>/<schema>/<volume>/checkpoints/autoloader_demo"
target_table: "<catalog>.<schema>.raw_events"
```

#### 4. Copy Sample Data (Optional)

Run `00_copy_utility.py` to copy sample files to your Volume for testing.

#### 5. Verify Transforms Module Path

In `01_ingest_autoloader.py`, update the `sys.path.insert()` line to match your Workspace path:
```python
sys.path.insert(
    0,
    "/Workspace/Users/<your-email>/Customers/spdji/autoloader-demo/resources"
)
```

---

## Execution Steps

### Manual Execution

#### Step 1: Run Copy Utility (First Time Only)
```python
# Open and run: notebooks/00_copy_utility.py
# This copies sample_data/ files to your source Volume
```

#### Step 2: Run Main Ingestion Pipeline
```python
# Open and run: notebooks/01_ingest_autoloader.py
# This starts the Auto Loader streaming job

# The job will:
# 1. Detect files in source_url
# 2. Infer schema from JSON
# 3. Apply transforms
# 4. Write to target_table
# 5. Continue monitoring for new files
```

#### Step 3: Verify Data
```sql
-- Check ingested data
SELECT * FROM acs.autoloader.raw_events ORDER BY id;

-- Expected output:
-- +---+---------------------+-----+----------+----------------------+---------------------------+
-- | id| ts                  | val | new_col  | _file_path           | _ingest_ts                |
-- +---+---------------------+-----+----------+----------------------+---------------------------+
-- | 1 | 2025-10-21 10:00:00 | A   | null     | .../file_0001.json   | 2025-11-18 14:30:15.123   |
-- | 2 | 2025-10-21 10:05:00 | B   | null     | .../file_0002.json   | 2025-11-18 14:30:15.456   |
-- | 3 | 2025-10-21 10:10:00 | C   | null     | .../file_0003.json   | 2025-11-18 14:30:15.789   |
-- | 4 | 2025-10-21 10:15:00 | D   | appeared | .../file_0004.json   | 2025-11-18 14:30:16.012   |
-- +---+---------------------+-----+----------+----------------------+---------------------------+

-- Verify schema evolution handled new_col
DESCRIBE TABLE acs.autoloader.raw_events;
```

#### Step 4: Test Schema Evolution
```bash
# Add a new file with additional columns to source_url
# Example: {"id": 5, "ts": "2025-10-21T10:20:00Z", "val": "E", "new_col": "test", "another_col": "extra"}

# Auto Loader will automatically:
# 1. Detect the new column (another_col)
# 2. Add it to the table schema
# 3. Populate existing rows with NULL
# 4. Process the new file successfully
```

---

### Scheduled Execution

#### Option A: Using Databricks UI

1. Go to **Workflows** > **Jobs** > **Create Job**
2. Configure:
   - **Name**: `autoloader-demo-job`
   - **Task Type**: Notebook
   - **Notebook Path**: `/Workspace/.../01_ingest_autoloader`
   - **Cluster**: Choose existing or create new
   - **Schedule**: Set desired frequency (e.g., hourly, daily)
3. Click **Create** and **Run Now** to test

#### Option B: Using SDK (Programmatic)

Run `03_job_creation.py` to create the job automatically:
```python
# This notebook will:
# 1. Connect to Databricks Workspace
# 2. Create a job definition
# 3. Print the job_id

# Update the existing_cluster_id to match your cluster
# Or change to new_cluster configuration
```

Example output:
```
Job created with ID: 123456789
View at: https://<workspace-url>/#job/123456789
```

---

## Schema Evolution

Auto Loader provides four schema evolution modes:

### 1. `addNewColumns` (Default in this project)

**Behavior**:
- New columns are automatically added to the table
- Existing rows get NULL for new columns
- Pipeline continues without interruption

**Example**:
```json
// Initial file
{"id": 1, "ts": "2025-10-21T10:00:00Z", "val": "A"}

// Later file with new column
{"id": 4, "ts": "2025-10-21T10:15:00Z", "val": "D", "new_col": "appeared"}
```

**Result**: Table schema expands to include `new_col`. No pipeline failure.

### 2. `rescue`

**Behavior**:
- New columns are placed in a special `_rescued_data` column (JSON string)
- Original table schema remains unchanged
- Use for strict schema enforcement with audit trail

**Use case**: Compliance scenarios where schema changes require approval.

### 3. `none`

**Behavior**:
- Schema is inferred once and never changes
- New columns in later files are ignored
- No pipeline failure, but data loss possible

**Use case**: Strictly controlled schemas where new fields are unexpected errors.

### 4. `failOnNewColumns`

**Behavior**:
- Pipeline fails immediately if new columns appear
- Requires manual intervention to restart

**Use case**: Strict data quality gates in regulated environments.

### Demonstrating Schema Evolution

Run these steps to see schema evolution in action:

```python
# 1. Ingest batch_01 and batch_02 (same schema)
# Schema: id, ts, val, _file_path, _ingest_ts

spark.sql("SELECT * FROM acs.autoloader.raw_events").show()
# +---+---------------------+-----+----------------------+---------------------------+
# | id| ts                  | val | _file_path           | _ingest_ts                |
# +---+---------------------+-----+----------------------+---------------------------+
# | 1 | 2025-10-21 10:00:00 | A   | .../file_0001.json   | ...                       |
# | 2 | 2025-10-21 10:05:00 | B   | .../file_0002.json   | ...                       |
# | 3 | 2025-10-21 10:10:00 | C   | .../file_0003.json   | ...                       |
# +---+---------------------+-----+----------------------+---------------------------+

# 2. Ingest batch_03_drift (adds new_col)
# Schema automatically evolves: id, ts, val, new_col, _file_path, _ingest_ts

spark.sql("SELECT * FROM acs.autoloader.raw_events").show()
# +---+---------------------+-----+----------+----------------------+---------------------------+
# | id| ts                  | val | new_col  | _file_path           | _ingest_ts                |
# +---+---------------------+-----+----------+----------------------+---------------------------+
# | 1 | 2025-10-21 10:00:00 | A   | null     | .../file_0001.json   | ...                       |
# | 2 | 2025-10-21 10:05:00 | B   | null     | .../file_0002.json   | ...                       |
# | 3 | 2025-10-21 10:10:00 | C   | null     | .../file_0003.json   | ...                       |
# | 4 | 2025-10-21 10:15:00 | D   | appeared | .../file_0004.json   | ...                       |
# +---+---------------------+-----+----------+----------------------+---------------------------+

# 3. Check schema history
spark.sql("DESCRIBE HISTORY acs.autoloader.raw_events").show()
# You'll see schema change operations logged
```

---

## Detection Modes

Auto Loader supports three detection modes for finding new files:

### 1. `directory` (Default)

**How it works**:
- Periodically lists files in the source directory
- Compares with previously processed files in checkpoint
- Processes new files

**Configuration**:
```yaml
detection_mode: "directory"
```

**Best for**:
- Unity Catalog Volumes (recommended for Volumes)
- Small to medium file arrival rates
- Simpler setup (no cloud infrastructure)

**Performance**:
- Listing overhead scales with total file count
- Good for < 10,000 files

---

### 2. `useNotifications`

**How it works**:
- Sets up cloud storage notifications (S3 Event Notifications, ADLS Event Grid)
- Receives real-time events when files are created
- Processes files immediately

**Configuration**:
```yaml
detection_mode: "useNotifications"
```

**Setup required**:
```python
reader = reader.option("cloudFiles.useNotifications", True)
# Databricks will create notification infrastructure automatically
```

**Best for**:
- External cloud storage (S3, ADLS, GCS)
- High file arrival rates (> 1000 files/hour)
- Low-latency requirements

**Performance**:
- Near real-time processing
- Scales to millions of files

**Note**: Not supported for Unity Catalog Volumes.

---

### 3. `fileEvents` (Managed File Events)

**How it works**:
- Uses Unity Catalog's native file event system
- Tracks file creation at the storage layer
- More efficient than directory listing

**Configuration**:
```yaml
detection_mode: "fileEvents"
```

**Setup required**:
```python
reader = reader.option("cloudFiles.useManagedFileEvents", True)
# Only works with external locations registered in Unity Catalog
```

**Best for**:
- External locations registered in Unity Catalog
- Large-scale ingestion (> 10,000 files)
- Shared file tracking across multiple pipelines

**Limitations**:
- Only available for external locations, not Volumes
- Requires UC external location registration

---

### Comparison Table

| Feature | directory | useNotifications | fileEvents |
|---------|-----------|------------------|------------|
| **Volumes Support** | Yes (recommended) | No | No |
| **External Storage** | Yes | Yes | Yes (UC external only) |
| **Setup Complexity** | Low | Medium (cloud notifications) | Medium (UC external location) |
| **Latency** | Minutes | Seconds | Seconds |
| **File Scale** | < 10K files | Millions | Millions |
| **Cost** | Low | Medium (cloud notifications) | Low |

**Recommendation**: Use `directory` mode for Unity Catalog Volumes (this project's default).

---

## Job Automation

### Creating Jobs Programmatically

The `03_job_creation.py` notebook demonstrates using the Databricks SDK to create jobs:

```python
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.jobs import Task, NotebookTask, Source

w = WorkspaceClient()

job = w.jobs.create(
    name="autoloader-demo-job",
    tasks=[
        Task(
            task_key="ingest",
            notebook_task=NotebookTask(
                notebook_path="/Workspace/Users/alan.silva@databricks.com/Customers/spdji/autoloader-demo/notebooks/01_ingest_autoloader",
                base_parameters={},
                source=Source("WORKSPACE")
            ),
            existing_cluster_id="0908-155147-maxf059n"
        )
    ]
)

print(f"Created job with ID: {job.job_id}")
```

### Advanced Job Configuration

For production deployments, consider:

#### 1. Job Clusters (Recommended)

```python
from databricks.sdk.service.compute import ClusterSpec

job = w.jobs.create(
    name="autoloader-demo-job",
    tasks=[
        Task(
            task_key="ingest",
            notebook_task=NotebookTask(...),
            new_cluster=ClusterSpec(
                spark_version="13.3.x-scala2.12",
                node_type_id="i3.xlarge",
                num_workers=2,
                autoscale={"min_workers": 1, "max_workers": 5}
            )
        )
    ]
)
```

**Benefits**:
- Cost-effective (cluster terminates after job)
- Isolated environment per job
- Auto-scaling based on workload

#### 2. Multi-Task Workflows

```python
tasks=[
    Task(
        task_key="ingest",
        notebook_task=NotebookTask(
            notebook_path=".../01_ingest_autoloader"
        ),
        new_cluster=...
    ),
    Task(
        task_key="validate",
        depends_on=[{"task_key": "ingest"}],
        notebook_task=NotebookTask(
            notebook_path=".../04_data_quality_checks"
        ),
        new_cluster=...
    ),
    Task(
        task_key="notify",
        depends_on=[{"task_key": "validate"}],
        notebook_task=NotebookTask(
            notebook_path=".../05_send_notifications"
        ),
        new_cluster=...
    )
]
```

#### 3. Retry and Alerting

```python
job = w.jobs.create(
    name="autoloader-demo-job",
    tasks=[...],
    max_concurrent_runs=1,
    timeout_seconds=7200,  # 2 hours
    email_notifications={
        "on_failure": ["team@company.com"],
        "on_success": ["team@company.com"]
    }
)
```

### Schedule Configuration

```python
from databricks.sdk.service.jobs import CronSchedule

job = w.jobs.create(
    name="autoloader-demo-job",
    tasks=[...],
    schedule=CronSchedule(
        quartz_cron_expression="0 0 * * * ?",  # Hourly
        timezone_id="America/New_York",
        pause_status="UNPAUSED"
    )
)
```

**Common Schedules**:
- Hourly: `0 0 * * * ?`
- Daily at 2 AM: `0 0 2 * * ?`
- Every 15 minutes: `0 0/15 * * * ?`

---

## Sample Data

The `sample_data/` directory contains example JSON files demonstrating schema evolution:

### Batch 01 (Initial Schema)

**Files**: `file_0001.json`, `file_0002.json`

```json
{"id": 1, "ts": "2025-10-21T10:00:00Z", "val": "A"}
{"id": 2, "ts": "2025-10-21T10:05:00Z", "val": "B"}
```

**Schema**: `id`, `ts`, `val`

---

### Batch 02 (Same Schema)

**Files**: `file_0003.json`

```json
{"id": 3, "ts": "2025-10-21T10:10:00Z", "val": "C"}
```

**Schema**: `id`, `ts`, `val` (no change)

---

### Batch 03 (Schema Drift)

**Files**: `file_0004.json`

```json
{"id": 4, "ts": "2025-10-21T10:15:00Z", "val": "D", "new_col": "appeared"}
```

**Schema**: `id`, `ts`, `val`, `new_col` (new column added)

**Result**: Auto Loader automatically adds `new_col` to the table schema with `addNewColumns` mode.

---

## Troubleshooting

### Issue: "File not found" when reading config

**Error**:
```
FileNotFoundError: [Errno 2] No such file or directory: '/Workspace/.../configs/dev.yaml'
```

**Solution**:
1. Verify config file exists in Workspace
2. Update `CONFIG_PATH` environment variable or hardcoded path in notebook
3. Check file permissions

---

### Issue: Schema evolution not working

**Symptoms**: New columns don't appear in table, or pipeline fails on new columns

**Solutions**:
1. Verify `schema_evolution_mode: "addNewColumns"` in config
2. Check that `cloudFiles.schemaEvolutionMode` is set in notebook
3. Inspect checkpoint location for schema files:
   ```python
   dbutils.fs.ls(checkpoint_path + "/_schemas")
   ```
4. If needed, reset checkpoint (WARNING: reprocesses all files):
   ```python
   dbutils.fs.rm(checkpoint_path, recurse=True)
   ```

---

### Issue: Checkpoint conflicts or "Stream already active"

**Error**:
```
org.apache.spark.sql.streaming.StreamingQueryException: Another instance of the streaming query is already running
```

**Solutions**:
1. Stop any running streams:
   ```python
   for stream in spark.streams.active:
       stream.stop()
   ```
2. Wait 30 seconds for cleanup
3. Restart the notebook
4. If persistent, reset checkpoint (reprocesses all files):
   ```python
   dbutils.fs.rm(checkpoint_path, recurse=True)
   ```

---

### Issue: Transform module not found

**Error**:
```
ModuleNotFoundError: No module named 'transforms'
```

**Solution**:
1. Verify `resources/transforms.py` exists in Workspace
2. Update `sys.path.insert()` in notebook to correct Workspace path:
   ```python
   sys.path.insert(0, "/Workspace/Users/<your-email>/.../resources")
   ```
3. Verify path is absolute (starts with `/Workspace`)

---

### Issue: Unity Catalog permissions errors

**Error**:
```
PermissionDeniedException: User does not have permission to CREATE TABLE in schema
```

**Solution**:
1. Grant catalog permissions:
   ```sql
   GRANT USE CATALOG ON CATALOG acs TO `user@company.com`;
   GRANT USE SCHEMA ON SCHEMA acs.autoloader TO `user@company.com`;
   GRANT CREATE TABLE ON SCHEMA acs.autoloader TO `user@company.com`;
   ```
2. For Volumes:
   ```sql
   GRANT READ VOLUME ON VOLUME acs.autoloader.autoloader_demo TO `user@company.com`;
   GRANT WRITE VOLUME ON VOLUME acs.autoloader.autoloader_demo TO `user@company.com`;
   ```

---

### Issue: Duplicate data after restart

**Symptoms**: Same files processed multiple times

**Causes**:
- Checkpoint directory was deleted
- Checkpoint location changed between runs
- Force restart without graceful shutdown

**Solutions**:
1. Use consistent checkpoint location across runs
2. Never delete checkpoint without intending full reprocessing
3. Use `.stop()` to gracefully stop streams before restart

---

### Issue: Job creation fails with cluster ID error

**Error**:
```
InvalidParameterValue: Cluster 0908-155147-maxf059n not found
```

**Solution**:
1. Get valid cluster IDs:
   ```python
   from databricks.sdk import WorkspaceClient
   w = WorkspaceClient()
   for c in w.clusters.list():
       print(f"{c.cluster_id}: {c.cluster_name}")
   ```
2. Update `existing_cluster_id` in `03_job_creation.py`
3. Or use `new_cluster` configuration instead

---

## Best Practices

### 1. Checkpoint Management
- Use a consistent checkpoint location per pipeline
- Never share checkpoint directories between different streams
- Include environment name in checkpoint path:
  ```yaml
  checkpoint_path: "/Volumes/.../checkpoints/autoloader_demo_prod"
  ```

### 2. Configuration Management
- Create separate config files per environment (dev, staging, prod)
- Use environment variables to select config:
  ```python
  env = os.environ.get("ENV", "dev")
  config_path = f"/Workspace/.../configs/{env}.yaml"
  ```
- Store sensitive values (credentials) in Databricks Secrets

### 3. Schema Evolution Strategy
- Use `addNewColumns` for development/testing
- Use `rescue` for production (audit trail of schema changes)
- Monitor `_rescued_data` column and alert on non-null values
- Review and promote rescued columns to schema manually

### 4. Monitoring and Alerts
- Monitor stream health:
  ```python
  query.lastProgress  # Check processing metrics
  query.status  # Check stream state
  ```
- Set up Databricks SQL alerts on:
  - Record count trends
  - Processing latency
  - Error rates
  - Schema change events

### 5. Performance Optimization
- Use appropriate detection mode (directory for Volumes)
- Partition target tables by date for better query performance:
  ```python
  df.writeStream.partitionBy("date").toTable(...)
  ```
- Tune batch size:
  ```python
  .option("maxFilesPerTrigger", 1000)  # Process 1000 files per batch
  ```
- Enable optimized writes:
  ```python
  spark.conf.set("spark.databricks.delta.optimizeWrite.enabled", "true")
  ```

---

## Additional Resources

### Databricks Documentation
- [Auto Loader Documentation](https://docs.databricks.com/ingestion/auto-loader/index.html)
- [Schema Evolution Guide](https://docs.databricks.com/ingestion/auto-loader/schema.html)
- [Unity Catalog Volumes](https://docs.databricks.com/data-governance/unity-catalog/volumes.html)
- [Structured Streaming Programming Guide](https://spark.apache.org/docs/latest/structured-streaming-programming-guide.html)

### Related Examples
- [Auto Loader Best Practices](https://docs.databricks.com/ingestion/auto-loader/best-practices.html)
- [Delta Lake Guide](https://docs.databricks.com/delta/index.html)
- [Databricks Jobs](https://docs.databricks.com/workflows/jobs/jobs.html)

---

## Support

For issues or questions:
1. Check [Troubleshooting](#troubleshooting) section
2. Review Databricks documentation
3. Contact your Databricks support team
4. File issues in your internal repository

---

## License

This demo project is provided as-is for educational and demonstration purposes.

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2025-11-18 | Initial release with Auto Loader demo |

---

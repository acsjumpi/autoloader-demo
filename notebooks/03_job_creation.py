# Databricks notebook source
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
print(job.job_id)
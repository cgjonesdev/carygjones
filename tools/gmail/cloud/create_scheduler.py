#!/usr/bin/env python3
"""Create or update Cloud Scheduler job for recruiter-scan (gcloud workaround)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from google.cloud import resourcemanager_v3
from google.cloud import scheduler_v1
from google.iam.v1 import policy_pb2

CONFIG = Path(__file__).resolve().parent / "config.env"


def load_config() -> dict[str, str]:
    values: dict[str, str] = {}
    if CONFIG.exists():
        for line in CONFIG.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            values[key.strip()] = val.strip()
    for key in (
        "GCP_PROJECT",
        "GCP_REGION",
        "SCHEDULER_NAME",
        "JOB_NAME",
        "SCHEDULE_CRON",
        "SCHEDULE_TIMEZONE",
    ):
        values.setdefault(key, os.environ.get(key, ""))
    values.setdefault("GCP_REGION", "us-west1")
    values.setdefault("SCHEDULER_NAME", "recruiter-scan-weekdays")
    values.setdefault("JOB_NAME", "recruiter-scan")
    values.setdefault("SCHEDULE_CRON", "*/10 * * * 1-5")
    values.setdefault("SCHEDULE_TIMEZONE", "America/Los_Angeles")
    return values


def grant_scheduler_run_developer(project: str, scheduler_sa: str) -> None:
    rm = resourcemanager_v3.ProjectsClient()
    resource = f"projects/{project}"
    policy = rm.get_iam_policy(request={"resource": resource})
    member = f"serviceAccount:{scheduler_sa}"
    role = "roles/run.developer"
    for binding in policy.bindings:
        if binding.role == role:
            if member not in binding.members:
                binding.members.append(member)
            break
    else:
        policy.bindings.append(policy_pb2.Binding(role=role, members=[member]))
    rm.set_iam_policy(request={"resource": resource, "policy": policy})


def main() -> int:
    cfg = load_config()
    project = cfg.get("GCP_PROJECT") or os.environ.get("GCP_PROJECT", "")
    if not project:
        print("Set GCP_PROJECT in cloud/config.env", file=sys.stderr)
        return 1

    region = cfg["GCP_REGION"]
    scheduler_name = cfg["SCHEDULER_NAME"]
    job_name = cfg["JOB_NAME"]
    scheduler_sa = f"recruiter-scan-scheduler@{project}.iam.gserviceaccount.com"
    parent = f"projects/{project}/locations/{region}"
    full_name = f"{parent}/jobs/{scheduler_name}"
    run_uri = (
        f"https://{region}-run.googleapis.com/apis/run.googleapis.com/v1/"
        f"namespaces/{project}/jobs/{job_name}:run"
    )

    grant_scheduler_run_developer(project, scheduler_sa)

    client = scheduler_v1.CloudSchedulerClient()
    schedule = cfg["SCHEDULE_CRON"]
    time_zone = cfg["SCHEDULE_TIMEZONE"]
    job = scheduler_v1.Job(
        name=full_name,
        schedule=schedule,
        time_zone=time_zone,
        description=(
            "Trigger recruiter Gmail scan Cloud Run Job "
            f"({schedule}, {time_zone})"
        ),
        http_target=scheduler_v1.HttpTarget(
            uri=run_uri,
            http_method=scheduler_v1.HttpMethod.POST,
            oauth_token=scheduler_v1.OAuthToken(
                service_account_email=scheduler_sa,
                scope="https://www.googleapis.com/auth/cloud-platform",
            ),
        ),
    )
    try:
        created = client.create_job(request={"parent": parent, "job": job})
        print(f"Created scheduler: {created.name}")
    except Exception as exc:
        if "ALREADY_EXISTS" in str(exc) or "409" in str(exc):
            updated = client.update_job(job=job)
            print(f"Updated scheduler: {updated.name}")
        else:
            raise
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

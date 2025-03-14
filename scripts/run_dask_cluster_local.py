import logging  # noqa: INP001
import os
import signal
import sys
from types import FrameType

import boto3
from dask_cloudprovider.aws import (  # type: ignore[reportMissingTypeStubs]
    FargateCluster,
)

ECR_REPO = "chainlit-demo/dask"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

log = logging.getLogger(__name__)

cluster: FargateCluster


def handle_termination(signum: int, frame: FrameType) -> None:  # noqa: ARG001
    """Call .close() on cluster if terminated."""
    log.info("Termination signal received. Cleaning up...")
    cluster.close()
    log.info("Cleanup complete. Exiting.")
    sys.exit(0)


def get_ecr_docker_image_uri(repo_name: str, tag: str = "latest") -> str:
    """Get full URI of docker image from an ECR repo."""
    ecr = boto3.client("ecr")  # type: ignore[reportUnknownMemberType]
    ecr_repos = ecr.describe_repositories()["repositories"]  # type: ignore[reportUnknownMemberType]
    try:
        dask_repo = next(  # type: ignore[reportUnknownVariableType]
            repo
            for repo in ecr_repos  # type: ignore[reportUnknownVariableType]
            if repo["repositoryName"] == repo_name  # type: ignore[reportUnknownArgumentType]
        )
    except StopIteration:
        msg = f"ECR repo '{repo_name}' not found."
        raise ValueError(msg) from None
    docker_image_uri = f"{dask_repo['repositoryUri']}:{tag}"
    return docker_image_uri


signal.signal(signal.SIGTERM, handle_termination)  # type: ignore[reportArgumentType]
signal.signal(signal.SIGINT, handle_termination)  # type: ignore[reportArgumentType]


docker_image = get_ecr_docker_image_uri(ECR_REPO)
env = {
    "ZARR_REFERENCE_PATH": os.getenv("ZARR_REFERENCE_PATH"),
}

# launch cluster
log.info("Launching cluster (this can take a while) ...")
cluster = FargateCluster(
    image=docker_image,
    # this environment is passed to all scheduler and worker instances
    environment=env,
    n_workers=4,
    # scheduler auto shuts down if no client connection in this period of time
    scheduler_timeout="60 days",
    # runs into a permission issue if this is not set
    skip_cleanup=True,
    task_role_policies=[
        "arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess",
    ],
)
# enable auto-scaling (i.e. adding/removing workers to the cluster based on
# workload)
cluster.adapt(
    # min workers
    minimum=4,
    # max workers
    maximum=16,
    # Number of consecutive times that a worker should be suggested for removal
    # before we remove it.
    wait_count=3,
    # Time between checks
    interval="5 minutes",
    # Amount of time we want a computation to take. This affects how
    # aggressively we scale up.
    target_duration="30s",
)

log.info("Cluster: %s", cluster.cluster_name)  # type: ignore[reportUnknownMemberType]
log.info("Dashboard link: %s", cluster.dashboard_link)
log.info("Scheduler address: %s", cluster.scheduler_address)

input("Press ENTER to shutdown the cluster ...\n")

log.info("Shutting down cluster (this can take a while) ...")
cluster.close()

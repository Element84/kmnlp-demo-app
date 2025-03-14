# demo-app
Demo app.

## Developing

1. Checkout the code.
1. Create/activate your Python environment of choice.
1. Install uv: `pip install uv`.
1. Install dependencies: `scripts/recreate_venv.sh`.
    - If you do not want to delete and recreate your venv, you can run the following directly:
        - `uv pip sync requirements.txt`
    - If you would like to also update the commits used from git repository dependencies:
        - `scripts/refresh_requirements.sh`
1. Run `pre-commit install` to install pre-commit hooks.
1. Configure your editor for realtime linting:
	- For VS Code:
		- Set the correct Python environment for the workspace via `ctrl+shift+P` > `Python: Select Interpreter`.
		- Install the Pylance and Ruff extensions.
1. Make changes.
1. Verify linting passes `scripts/lint.sh`.
1. Verify tests pass `scripts/test.sh`.
1. Commit and push your changes.

## Usage

### Scientific Python Agent

You will need 3 separate terminals. Remember to activate the correct Python environment in each terminal.

Launch Dask cluster:
1. Start Dask scheduler:
	```sh
	# Specify AWS credentials. E.g., if you have a profile configured:
	export AWS_PROFILE="kmnlp"
	dask scheduler --host="127.0.0.1" --port="8786"
	```
2. In a separate terminal, start Dask workers:
	```sh
	# Specify AWS credentials. E.g., if you have a profile configured:
	export AWS_PROFILE="kmnlp"
	dask worker tcp://127.0.0.1:8786 --nworkers="auto"
		```
3. Monitor the Dask dashboard at http://localhost:8787/status.

Launch Chainlit app:
1. In a separate terminal, start the chainlit app:
	```sh
	# Specify address to Dask scheduler
	export DASK_ADDRESS="tcp://127.0.0.1:8786"
	# Specify AWS credentials. E.g., if you have a profile configured:
	export AWS_PROFILE="kmnlp"
	# Set `ZARR_REFERENCE_PATH` var:
	export ZARR_REFERENCE_PATH="s3://data-c6c22a2e42294c11b52ee7f0c792c071/crw/5km/v3.1/nc/v1.0/daily/sst/zarr_reference.json"

	chainlit run src/app.py -w
	```

#### Example questions

- _Tell me about the dataset_
- _What can I ask about?_
- _What was the mean SST in the Black Sea on June 01, 2024?_
- _What was the maximum SST in the region defined by the bounding box (20N to 30N, -97W to -87W) on 12 Oct 2024?_
- _Show the daily average SST within the Chesapeake Bay over the year 2024 as a time series._

## Docker
Use the scripts in the `scripts/` dir.

### Build
```sh
# app image
scripts/build_container.sh chainlit

# dask image (to be used by dask scheduler and workers)
scripts/build_container.sh dask
```

### Run app
```sh
# Specify address to Dask scheduler
export DASK_ADDRESS="tcp://127.0.0.1:8786"
# Specify AWS credentials. E.g., if you have a profile configured:
export AWS_PROFILE="kmnlp"
# Set `ZARR_REFERENCE_PATH` var:
export ZARR_REFERENCE_PATH="s3://data-c6c22a2e42294c11b52ee7f0c792c071/crw/5km/v3.1/nc/v1.0/daily/sst/zarr_reference.json"

scripts/run.sh
```
Navigate to http://0.0.0.0:8000/.

### Push to ECR
App repo: chainlit-demo/chainlit
Dask repo: chainlit-demo/dask

https://us-east-1.console.aws.amazon.com/ecr/private-registry/repositories?region=us-east-1

```sh
# app image
scripts/push_container.sh chainlit

# dask image (to be used by dask scheduler and workers)
scripts/push_container.sh dask
```

## Launch and connect to a Dask cluster on AWS

### Run
Launch a Dask Fargate cluster by running this script:
```sh
export AWS_PROFILE="kmnlp"
export ZARR_REFERENCE_PATH="s3://data-c6c22a2e42294c11b52ee7f0c792c071/crw/5km/v3.1/nc/v1.0/daily/sst/zarr_reference.json"

python scripts/run_dask_cluster_local.py
```
Once the cluster is launched, the script will print out
- the URL to the dashboard, which you can open in your browser and
- the address of the scheduler, which you will need to pass to the Chainlit app in the step below.

You can monitor the ECS cluster in the AWS console here: https://us-east-1.console.aws.amazon.com/ecs/v2/clusters?region=us-east-1.

### Connect to it using the Chainlit app
Assuming other env variables are already set, launch the app like so (using the scheduler address from the step above):
```sh
DASK_ADDRESS="<scheduler address>" scripts/run_container.sh chainlit
```

## Notes
- To enable `dask_cloudprovider.aws.FargateCluster` to run, a default VPC had to be created via
	```sh
	aws2 ec2 create-default-vpc --profile kmnlp
	```
	since there wasn't an existing one in the account. This step does not need to be repeated.
- It is important for the Python environments of the Dask clients, workers, and scheduler to be identical. This is currently ensured by using the same `requirements.txt` during `docker build`.
- The arguments to `cluster.adapt()` in [scripts/run_dask_cluster_local.py](scripts/run_dask_cluster_local.py) might need to be further tuned to get the best performance.

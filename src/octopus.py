import requests
import argparse
import sys
import json
import logging
import pathlib
import os
import enum


logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)


class OctopusTaskState(enum.StrEnum):
    FAILED = "Failed"
    SUCCESS = "Success"


class ResourceType:
    def __init__(self, data):
        self.logger = logging.getLogger(__name__)
        self.logger.info("Setup")
        self.api_key = data["source"]["api_key"]
        self.space_id = data["source"]["space_id"]
        self.octopus_server_uri = data["source"]["octopus_server_uri"]
        self.project_id = data["source"]["project_id"]
        self.version = data.get("version", {}).get("ref")
        self.auth_header = {"X-Octopus-ApiKey": self.api_key}

        self.params = data.get("params")
        self.metadata = data.get("metadata")

        session = requests.Session()
        session.headers.update(self.auth_header)
        self.requests_session = session

        if data["source"].get("debug"):
            self.logger.setLevel(logging.DEBUG)

    def _metadata_from_deployment(self, deployment):
        return [
            {"name": "Name", "value": deployment["Name"]},
            {"name": "DeployedBy", "value": deployment.get("DeployedBy")},
            {
                "name": "Deployment",
                "value": f"{self.octopus_server_uri}{deployment['Links']['Web']}",
            },
            {
                "name": "Release",
                "value": f"{self.octopus_server_uri}{deployment['Links']['Release']}",
            },
        ]

    def concourse_in(self, filepath):
        self.logger.info("Running in")
        self.logger.debug("concourse in with filepath: %s", filepath)
        deployment = self._get_deployment(self.version)
        output = {
            "version": {"ref": self.version},
            "metadata": self._metadata_from_deployment(deployment),
        }

        with open(os.path.join(filepath, "deployment.json"), "w") as file:
            file.write(json.dumps(deployment))

        release_variables = self._get_variables(deployment["Links"]["Variables"])
        with open(os.path.join(filepath, "variables.json"), "w") as file:
            file.write(json.dumps(release_variables))

        self.logger.debug("Variables: %s", release_variables)
        self.logger.debug("Output: %s", output)
        print(json.dumps(output))

    def concourse_out(self, filepath):
        self.logger.info("Running in")
        self.logger.debug("concourse out with filepath: %s", filepath)
        self.logger.debug("filepath listdir: %s", os.listdir(filepath))
        self.logger.debug(
            "artifacts listdir: %s", os.listdir(os.path.join(filepath, "artifacts"))
        )
        f = open(
            os.path.join(filepath, self.params.get("path"), "deployment.json"), "r"
        )
        deployment = json.load(f)
        self.logger.debug("deployment file: %s", deployment)
        f.close()

        artifact_path = self.params.get("artifact_path")
        if artifact_path:
            artifact = self._create_artifact_resource(
                deployment["TaskId"], os.path.basename(artifact_path)
            )
            self._upload_artifact(artifact["Id"], os.path.join(filepath, artifact_path))

        output = {
            "version": {"ref": deployment["Id"]},
            "metadata": self._metadata_from_deployment(deployment),
        }
        self.logger.debug("Output: %s", output)
        print(json.dumps(output))

    def concourse_check(self):
        self.logger.info("Running check")
        take = 30
        if not self.version:
            take = 1

        url = f"{self.octopus_server_uri}/api/{self.space_id}/deployments?projects={self.project_id}&taskState=Success&take={take}"
        response = self.requests_session.get(url)
        items = self._latest_deployments_since_deploymentid(
            response.json(), self.version
        )
        self.logger.debug("Output: %s", items)
        print(json.dumps(items))

    def _get_deployment(self, deployment_id):
        self.logger.info("Calling deployment API for ID: %s", deployment_id)
        url = f"{self.octopus_server_uri}/api/spaces/{self.space_id}/deployments/{deployment_id}"
        response = self.requests_session.get(url)
        return response.json()

    def _upload_artifact(self, artifact_id, filepath):
        self.logger.info("Uploading artifact: %s, %s", artifact_id, filepath)
        url = f"{self.octopus_server_uri}/api/spaces/{self.space_id}/artifacts/{artifact_id}/content"
        with open(filepath, "rb") as f:
            response = self.requests_session.put(url, data=f)
            self.logger.debug("Artifact upload reponse: %s", response.status_code)

        return

    def _create_artifact_resource(self, server_task_id, filename):
        self.logger.info("Creating artifact resource: %s, %s", server_task_id, filename)
        url = f"{self.octopus_server_uri}/api/spaces/{self.space_id}/artifacts"
        data = {
            "ServerTaskId": server_task_id,
            "Filename": filename,
        }
        self.logger.debug("Create artifact body: %s", data)
        response = self.requests_session.post(url, data=json.dumps(data))
        output = response.json()
        self.logger.debug("Create Artifact response: %s", output)
        return output

    def _latest_deployments_since_deploymentid(self, deployments, deploymentid):
        result = []
        for deployment in deployments["Items"]:
            result.append({"ref": deployment["Id"]})
            if deploymentid == deployment["Id"]:
                break
        return result.reverse()

    def _get_variables(self, path):
        self.logger.info("Retrieving variable set.")
        url = f"{self.octopus_server_uri}/{path}"
        response = self.requests_session.get(url)
        variables = {}
        for i in response.json()["Variables"]:
            var_name = self._sanitize_variable_name(i["Name"])
            variables[var_name] = i["Value"]
        return variables

    def _sanitize_variable_name(self, variable_name):
        self.logger.info("Sanitizing variables.")
        output = variable_name.replace(" ", "_")
        output = output.replace("[", ".")
        return output.replace("]", "")


if __name__ == "__main__":
    logger = logging.getLogger(__name__)
    parser = argparse.ArgumentParser(description="Process some integers.")
    parser.add_argument("function", choices=["check", "in", "out"])
    parser.add_argument(
        "--input-file",
        "-i",
        type=argparse.FileType("r"),
        default=sys.stdin,
        help="Input file name containing a valid JSON.",
    )
    parser.add_argument("filepath", nargs="?", type=pathlib.Path)

    args = parser.parse_args()

    datain = json.load(args.input_file)
    logger.debug("Parse args: %s", args)
    resourceType = ResourceType(datain)

    if args.function == "check":
        resourceType.concourse_check()
    elif args.function == "out":
        resourceType.concourse_out(args.filepath)
    else:
        resourceType.concourse_in(args.filepath)

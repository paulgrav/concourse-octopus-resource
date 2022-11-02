import requests
import argparse
import sys
import json
import logging
import pathlib
import os
import enum

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")


class OctopusTaskState(enum.StrEnum):
    FAILED = "Failed"
    SUCCESS = "Success"


class ResourceType:
    def __init__(self, data):
        logging.debug("Setup")
        self.api_key = data["source"]["api_key"]
        self.space_id = data["source"]["space_id"]
        self.octopus_server_uri = data["source"]["octopus_server_uri"]
        self.project_id = data["source"]["project_id"]
        self.version = data.get("version", {}).get("ref")
        self.auth_header = {"X-Octopus-ApiKey": self.api_key}

        self.params = data.get("params")
        self.metadata = data.get("metadata")
        if data["source"].get("debug"):
            logging.basicConfig(
                format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                level=logging.DEBUG,
            )

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
        logging.debug("concourse in with filepath: %s", filepath)
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

        logging.debug("Variables: %s", release_variables)
        logging.debug("Output: %s", output)
        print(json.dumps(output))

    def concourse_out(self, filepath):
        logging.debug("concourse out with filepath: %s", filepath)
        logging.debug("filepath listdir: %s", os.listdir(filepath))
        f = open(
            os.path.join(filepath, self.params.get("path"), "deployment.json"), "r"
        )
        deployment = json.load(f)
        logging.debug("deployment file: %s", deployment)
        f.close()

        output = {
            "version": {"ref": deployment["Id"]},
            "metadata": self._metadata_from_deployment(deployment),
        }
        logging.debug("Output: %s", output)
        print(json.dumps(output))

    def concourse_check(self):
        take = 30
        if not self.version:
            take = 1

        url = f"{self.octopus_server_uri}/api/{self.space_id}/deployments?projects={self.project_id}&taskState=Success&take={take}"
        response = self._get_octopus_response(url)
        items = self._latest_deployments_since_deploymentid(
            response.json(), self.version
        )
        logging.debug("Output: %s", items)
        print(json.dumps(items))

    def _get_octopus_response(self, url):
        return requests.get(url, headers=self.auth_header)

    def _post_octopus_response(self, url, data):
        headers = self.auth_header
        return requests.post(url, headers=headers, data=json.dumps(data))

    def _get_deployment(self, deployment_id):
        url = f"{self.octopus_server_uri}/api/spaces/{self.space_id}/deployments/{deployment_id}"
        response = self._get_octopus_response(url)
        return response.json()

    def _set_task_state(self, task_id, state, reason):
        url = f"{self.octopus_server_uri}/api/tasks/{task_id}/state"
        body = {"Reason": reason, "State": state}
        response = self._post_octopus_response(url, body)
        return response.json()

    def _latest_deployments_since_deploymentid(self, deployments, deploymentid):
        result = []
        for deployment in deployments["Items"]:
            result.append({"ref": deployment["Id"]})
            if deploymentid == deployment["Id"]:
                break
        return result

    def _get_variables(self, path):
        url = f"{self.octopus_server_uri}/{path}"
        response = self._get_octopus_response(url)
        variables = {}
        for i in response.json()["Variables"]:
            var_name = i["Name"].replace(" ", "_")
            var_name = var_name.replace("[", ".")
            var_name = var_name.replace("]", "")
            variables[var_name] = i["Value"]
        return variables


if __name__ == "__main__":
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
    logging.debug("Data received: %s", datain)
    logging.debug("Parse args: %s", args)
    resourceType = ResourceType(datain)

    if args.function == "check":
        resourceType.concourse_check()
    elif args.function == "out":
        resourceType.concourse_out(args.filepath)
    else:
        resourceType.concourse_in(args.filepath)

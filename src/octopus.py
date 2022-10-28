import requests
import argparse
import sys
import json

class ResourceType:
    def __init__(self, data):
        self.api_key = data['source']['api_key']
        self.space_id = data['source']['space_id']
        self.octopus_server_uri = data['source']['octopus_server_uri']
        self.project_id = data['source']['project_id']
        self.version = data.get('version').get('DeploymentId')


    def concourse_in(data):
        pass

    def concourse_out(data):
        pass

    def concourse_check(self):
        take = 30
        if not self.version:
            take = 1

        url = f"{self.octopus_server_uri}/api/{self.space_id}/deployments?projects={self.project_id}&taskState=Success&take={take}"
        req = requests.Request('GET', url, headers={ "X-Octopus-ApiKey": self.api_key})
        prepped = req.prepare()
        s = requests.Session()
        response = s.send(prepped)
        items = self.latest_deployments_since_deploymentid(response.json(), self.version)
        print(json.dumps(items))

    def latest_deployments_since_deploymentid(self, deployments, deploymentid):
        result = []
        for deployment in deployments['Items']:
            result.append(
                {   "DeploymentId":     deployment['Id'],
                    "WebRef":           f"{self.octopus_server_uri}{deployment['Links']['Web']}"
                }
            )
            if deploymentid == deployment['Id']:
                break
        return result

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Process some integers.')
    parser.add_argument('function',choices=["check","in","out"])
    parser.add_argument( '--input-file', '-i', type=argparse.FileType('r'), default=sys.stdin, help='Input file name containing a valid JSON.')

    args = parser.parse_args()

    datain=json.load(args.input_file)
    resourceType = ResourceType(datain)

    if args.function == "check":
        resourceType.concourse_check()
    elif args.function == "out":
        resourceType.concourse_out()
    else:
        resourceType.concourse_in()

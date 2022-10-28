import requests
import argparse
import sys
import json

def concourse_in(data):
    pass

def concourse_out(data):
    pass

def concourse_check(data):
    api_key = data['source']['api_key']
    space_id = data['source']['space_id']
    octopus_server_uri = data['source']['octopus_server_uri']
    project_id = data['source']['project_id']

    assert (space_id != None)
    url = f"{octopus_server_uri}/api/{space_id}/deployments?projects={project_id}&taskState=Success"
    req = requests.Request('GET', url, headers={ "X-Octopus-ApiKey": api_key})
    prepped = req.prepare()
    s = requests.Session()
    response = s.send(prepped)
    items = [ {"DeploymentId": i['Id'], "WebRef": f"{octopus_server_uri}{i['Links']['Web']}"} for i in response.json()['Items']]
    print(json.dumps(items))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Process some integers.')
    parser.add_argument('function',choices=["check","in","out"])
    parser.add_argument( '--input-file', '-i', type=argparse.FileType('r'), default=sys.stdin, help='Input file name containing a valid JSON.')

    args = parser.parse_args()

    datain=json.load(args.input_file)

    if args.function == "check":
        concourse_check(datain)
    elif args.function == "out":
        concourse_out(datain)
    else:
        concourse_in(datain)

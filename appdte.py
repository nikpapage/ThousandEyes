# coding: utf8
# **********************************************************************
# Script Name:      appdynamics_te.py
# Author:           Nik Papageorgiou
# Created Date:     6 November 2020
# Purpose:          AppDynamics & Integration Script using both AppD and TE APIs
# Prerequisites:    Compatible with python3 and python2, requires requests and pyyaml packages
# Change history:   0.1 - Initial version
#
# THE SCRIPT IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
# PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
# DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
# ARISING FROM, OUT OF OR IN CONNECTION WITH THIS SCRIPT OR THE USE OR OTHER DEALINGS IN THE SCRIPT.
# **********************************************************************


import requests
import base64
import json
import yaml
from datetime import date
import time
import os

print("Started AppDynamics & Thousand Eyes Extension")

def appdynamics_create_schema(schema):
  print("Creating Script for Analytics Schema Creation......")
  command = "curl -X POST \"${events_service}:${port}/events/schema/$schemaName\" -H\"X-Events-API-AccountName:${accountName}\" -H\"X-Events-API-Key:${apiKey}\" -H\"Content-type: application/vnd.appd.events+json;v=2\" -d '{\"schema\":"+json.dumps(schema)+ "}'"
  with open ('createSchema.sh', 'w') as rsh:
    rsh.write('''\
    #!/bin/bash
    schemaName=
    accountName=
    apiKey=
    events_service=
    port=
    while test $# -gt 0; do
        case $1 in
          -h|--help)
             echo "AppDynamics Analytics Schema Creation"
             echo " "
             echo "-------------------------------------"
             echo " "
             echo "options:"
             echo "-h,  --help                show brief help"
             echo "-sc, --schema              AppDynamics Schema Name specify an action to use"
             echo "-ac, --accountname         AppDynamics Global Account Name"
             echo "-k , --key                 AppDynamics Analytics API Key"
             echo "-es                        AppDynamics events service host name, inc protocol Example: https://analytics.api.appdynamics.com"
             echo "-port                      AppDynamics events service port"
             exit 0
         ;;
            -sc | --schema )        shift
                                    schemaName="$1"
                                    ;;
            -ac | --accountname )   shift
                                    accountName="$1"
                                    ;;
            -k | --key )            shift
                                    apiKey="$1"
                                    ;;
            -es)                    shift
                                    events_service="$1"
                                    ;;
            -port)                  shift
                                    port=$1
                                    ;;
            * )                     usage
                                    exit 1
         esac
         shift
     done
    ''')
    rsh.write(command)
    rsh.close()

#Dynamically load attributes to be reported into AppD
test_fields=[]
metric_fields=[]
te_config=[]
appd_config=[]
testIds=[]

try:
  print("Opening configuration file from "+os.getcwd())
  with open('te_appd.yml') as f:
    data = yaml.safe_load(f)

    #Create the schema creation command
    schema_dict={}
    schema_dict.update(data['ThousandEyes']['Test'])
    schema_dict.update(data['ThousandEyes']['Metrics'])
    if not os.path.exists("./createSchema.sh"):
      appdynamics_create_schema(schema_dict)
    for item in data['ThousandEyes']['Test']:
      test_fields.append(item)
    for item in data['ThousandEyes']['Metrics']:
      metric_fields.append(item)
    te_config=data['ThousandEyes']['TEConfig']
    test_ids=te_config['tetestId']
    appd_config=data['ThousandEyes']['AppDynamics']
except:
  print ("Failed to parse te_appd.yml in the following directory "+ os.getcwd())

username=te_config['teUsername']
api_key=te_config['teKey']
te_api=te_config['teAPI']
authentication=username+":"+api_key


#Create Client
client=requests.session()

def post_appdynamics_data(data):
  events_service_url = appd_config['appdEventsService']
  schema_name = appd_config['schemaName']
  events_service_url = events_service_url + "/events/publish/" + schema_name
  api_key = appd_config['analyticsApiKey']
  account_name = appd_config['globalAccountName']
  headers = {
    'X-Events-API-AccountName': account_name,
    'X-Events-API-Key': api_key,
    'Content-type': 'application/vnd.appd.events+json;v=2'
  }
  schema = json.dumps(data)
  schema = "[" + schema + "]"
  try:
    response = requests.request("POST", events_service_url, headers=headers, data=schema)
  except requests.exceptions.RequestException as e:  # This is the correct syntax
    print(e)
    raise SystemExit(e)


for test_id in test_ids:
  print("PullingThousand Eyes data for testid: "+str(test_id))
  te_api_url=te_api+str(test_id)+".json"
  authstr= 'Basic '+  base64.b64encode(authentication.encode('utf-8')).decode('utf-8')
  payload = {}
  headers = {
    'Authorization': authstr
  }
  test_json=''
  try:
    response = requests.request("GET", te_api_url, headers=headers, data = payload)
    test_json=response.json()
  except requests.exceptions.RequestException as e:  # This is the correct syntax
    print(e)
    raise SystemExit(e)



  test_dictionary={}
  for test_field in test_fields:
    test_value=test_json['net']['test'][test_field]
    if 'date' in test_field:
      time_tuple = time.strptime(test_value, '%Y-%m-%d %H:%M:%S')
      time_epoch = time.mktime(time_tuple)*1000
      test_dictionary[test_field]= int(time_epoch)
    elif 'Date' in test_field:
      time_tuple = time.strptime(test_value, '%Y-%m-%d %H:%M:%S')
      time_epoch = time.mktime(time_tuple)*1000
      test_dictionary[test_field]= int(time_epoch)
    elif 'apiLinks' in test_field:
      test_dictionary[test_field] = test_value[0]['href']
    else:
      test_dictionary[test_field] = test_value

  for agent in test_json['net']['metrics']:
    metric_dictionary={}
    for metric_field in metric_fields:
      metric_value = agent[metric_field]
      if 'date' in metric_field:
        time_tuple = time.strptime(metric_value, '%Y-%m-%d %H:%M:%S')
        time_epoch = time.mktime(time_tuple)*1000
        metric_dictionary[metric_field] = int(time_epoch)
      elif 'createdDate' in metric_field:
        time_tuple = time.strptime(metric_value, '%Y-%m-%d %H:%M:%S')
        time_epoch = time.mktime(time_tuple)*1000
        metric_dictionary[metric_field] = int(time_epoch)
      else:
        metric_dictionary[metric_field] = metric_value
    appd_dictionary={}
    appd_dictionary.update(test_dictionary)
    appd_dictionary.update(metric_dictionary)
    print("Posting Thousand Eyes data into custom schema for test: "+str(test_id)+" and agent: "+metric_dictionary['agentName'])
    post_appdynamics_data(appd_dictionary)

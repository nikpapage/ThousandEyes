# coding: utf8
# **********************************************************************
# Script Name:      appdynamics_te.py
# Author:           Nik Papageorgiou
# Created Date:     6 November 2020
# Purpose:          AppDynamics & Integration Script using both AppD and TE APIs
# Prerequisites:    Compatible with python3 and python2, requires requests and pyyaml packages
# Change history:   0.2 - Added Logging, Added the ability to use parameters
#
# THE SCRIPT IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
# PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
# DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
# ARISING FROM, OUT OF OR IN CONNECTION WITH THIS SCRIPT OR THE USE OR OTHER DEALINGS IN THE SCRIPT.
# **********************************************************************
import errno
import requests
import json
import getopt
import yaml
from datetime import date
import time
import os
import logging
import sys
from requests.auth import HTTPBasicAuth

if not os.path.exists('logs'):
    os.makedirs('logs')
logging.basicConfig(filename='logs/appd_te.log', format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)


config_file='te_appd.yml'
log_level=logging.INFO

# Get full command-line arguments
full_cmd_arguments = sys.argv

# Keep all but the first
argument_list = full_cmd_arguments[1:]
short_options = "hc:v"
long_options = ["help", "config=", "verbose"]
try:
    arguments, values = getopt.getopt(argument_list, short_options, long_options)
except getopt.error as err:
    # Output error, and return with an error code
    logging.error(str(err))
    pass
for current_argument, current_value in arguments:
    if current_argument in ("-v", "--verbose"):
        logging.info("Setting log level to DEBUG")
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)
        logging.basicConfig(filename='logs/appd_te.log', format='%(asctime)s - %(levelname)s - %(message)s', level=logging.DEBUG)
    elif current_argument in ("-h", "--help"):
        print ("Displaying help")
    elif current_argument in ("-c", "--config"):
        config_file=current_value
        logging.info("Config file location changed to "+config_file)


logging.info("Started AppDynamics & Thousand Eyes Extension")
test_fields = []
metric_fields = []
te_config = []
appd_config = []
testIds = []
# Create Client
client = requests.session()

def appdynamics_create_schema(schema):
    logging.info("Creating Script for Analytics Schema Creation......")
    command = "curl -X POST \"${events_service}:${port}/events/schema/$schemaName\" -H\"X-Events-API-AccountName:${accountName}\" -H\"X-Events-API-Key:${apiKey}\" -H\"Content-type: application/vnd.appd.events+json;v=2\" -d '{\"schema\":" + json.dumps(
        schema) + "}'"
    with open('createSchema.sh', 'w') as rsh:
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
        logging.info("Custom schema creation has been created. Please navigate to: "+os.getcwd())
        logging.info("Change permissions to createSchema.sh chmod +x createSchema.sh")
        logging.info("execute createSchema.sh in order to create the AppDynamics Analytics schema")
        sys.exit()



try:
    logging.info("Opening configuration file " + config_file)
    with open(config_file) as f:
        data = yaml.safe_load(f)
        logging.debug("Full Config Loaded from file: "+str(data))
        # Create the schema creation command
        schema_dict = {}
        schema_dict.update(data['ThousandEyes']['Test'])
        schema_dict.update(data['ThousandEyes']['Metrics'])
        if not os.path.exists("./createSchema.sh"):
            appdynamics_create_schema(schema_dict)
        for item in data['ThousandEyes']['Test']:
            test_fields.append(item)
        for item in data['ThousandEyes']['Metrics']:
            metric_fields.append(item)
        te_config = data['ThousandEyes']['TEConfig']
        test_ids = te_config['tetestId']
        appd_config = data['ThousandEyes']['AppDynamics']
except Exception as err:
    logging.error("Failed to parse te_appd.yml in the following directory " + os.getcwd())
    logging.error(err)


username = te_config['teUsername']
logging.debug("Setting thousand eyes username = "+username)
api_key = te_config['teKey']
logging.debug("Setting thousand eyes api_key = "+api_key)
te_api = te_config['teAPI']
logging.debug("Setting thousand eyes API URL = "+te_api)
account_group = te_config['teAccountGroup']
logging.debug("Setting thousand eyes Account Group = "+account_group)
logging.debug("Setting authentication to username + API key")
te_auth_user=HTTPBasicAuth(username,api_key)




def get_thousandeyes_accountid():
    logging.info("Extracting the account-group for user")
    accounts_url = te_api + "account-groups"
    headers = {
        'accept': 'application/json',
        'content-type': 'application/json'
    }
    cafile="/Users/npapageo/development/ThousandEyes/npm/thousandeyes.pem"

    response = requests.request('GET', accounts_url, headers=headers, auth=te_auth_user)
    if(response.status_code>299):
        logging.warning("Failed to extract account groups for thousand eyes username")
        logging.debug("Failed to extract thousandeyes account group using url "+accounts_url +" and authentication user "+username)
    try:
        accounts = response.json()['accountGroups']
        for account in accounts:
            if account['accountGroupName'] == account_group:
                return account['aid']
    except(KeyError):
        logging.error(KeyError)


def get_appdynamics_schema():
    events_service_url = appd_config['appdEventsService']
    schema_name = appd_config['schemaName']
    retrieve_schema_url = events_service_url + "/events/schema/" + schema_name
    api_key = appd_config['analyticsApiKey']
    account_name = appd_config['globalAccountName']
    headers = {
        'X-Events-API-AccountName': account_name,
        'X-Events-API-Key': api_key,
        'Content-type': 'application/vnd.appd.events+json;v=2'
    }
    schema = {}
    try:
        response = requests.request("GET", retrieve_schema_url, headers=headers)
        schema = response.json()
        if(response.status_code==404):
            logging.error("Cannot retrieve Analytics Schema")
            logging.error("Run createSchema.sh and validate the schema has been created in AppDynamics")
    except requests.exceptions.RequestException as e:  # This is the correct syntax
        logging.error("Failed to collect information on the AppDynamics analytics schema")
        logging.error(e)
        raise SystemExit(e)
    return schema


def update_appdynamics_schema():
    schema_old={}
    try:
        schema_old = get_appdynamics_schema()['schema']
    except(KeyError):
        logging.error("Cannot retrieve Analytics Schema")
        logging.error("Run createSchema.sh and validate the schema has been created in AppDynamics")
        sys.exit()
    set_1 = set(schema_old.items())
    set_2 = set(schema_dict.items())
    difference = dict(set_2 - set_1)
    if (difference):
        diff_payload = {}
        diff_payload.update({'add': difference})
        events_service_url = appd_config['appdEventsService']
        schema_name = appd_config['schemaName']
        events_service_url = events_service_url + "/events/schema/" + schema_name
        api_key = appd_config['analyticsApiKey']
        account_name = appd_config['globalAccountName']
        headers = {
            'X-Events-API-AccountName': account_name,
            'X-Events-API-Key': api_key,
            'Content-type': 'application/vnd.appd.events+json;v=2',
            'Accept-type': 'Accept: application/vnd.appd.events+json;v=2'
        }
        payload = "[" + json.dumps(diff_payload) + "]"
        try:
            logging.info("Updating custom schema fields: " + payload)
            response = requests.patch(events_service_url, headers=headers, data=payload)
        except requests.exceptions.RequestException as e:  # This is the correct syntax
            logging.error("Failed to update Appdynamics Custom Schema")
            logging.error(e.message)
            raise SystemExit(e)


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
        logging.info("Pushing data into AppDynamics schema")
        logging.debug("Pushing data into AppDynamics schema: "+schema)
        response = requests.request("POST", events_service_url, headers=headers, data=schema)
        if(response.status_code>204):
            logging.warning("POST data to AppDynamics failed with code: "+response.status_code)
            logging.debug("POST data to AppDynamics failed with response: "+response.text)
    except requests.exceptions.RequestException as e:  # This is the correct syntax
        logging.error("Failed to POST data to the AppDynamics analytics schema")
        logging.error(e)
        raise SystemExit(e)


update_appdynamics_schema()


def get_metrics_and_update(url):
    logging.debug("Pulling metrics from thousand eyes API: "+url)
    payload = {}
    metrics = {}
    headers = {
        'content-type': 'application/json',
        'accept': 'application/json'
    }
    test_json = ''
    params = {}
    te_params = {}
    test_json = {}
    try:
        if (te_config['teAccountGroup']):
            te_params.update({'aid': get_thousandeyes_accountid()})
    except(KeyError):
        logging.warning(KeyError)
        pass
    try:
        response = requests.request("GET", url, headers=headers,auth=te_auth_user) if params is None else requests.request("GET",
                                                                                                                url,
                                                                                                                headers=headers,
                                                                                                                params=te_params, auth=te_auth_user)
        if(response.status_code>299):
            logging.warning("Pulling test metrics from thousand eyes failed with error code "+response.status_code)

        test_json = response.json()
    except requests.exceptions.RequestException as e:  # This is the correct syntax
        logging.error(e)
        raise SystemExit(e)
    return test_json


def get_test_details(url):
    payload = {}
    headers = {
        'content-type': 'application/json',
        'accept': 'application/json'
    }
    test_json = ''
    params = {}
    te_params = {}
    test_json = {}
    try:
        if (te_config['teAccountGroup']):
            te_params.update({'aid': get_thousandeyes_accountid()})
    except:
        pass
    try:
        response = requests.request("GET", te_api_url, headers=headers, auth=te_auth_user) if params is None else requests.request("GET",
                                                                                                                te_api_url,
                                                                                                                headers=headers,
                                                                                                                params=te_params,auth=te_auth_user)
        test_json = response.json()
    except requests.exceptions.RequestException as e:  # This is the correct syntax
        print(e)
        raise SystemExit(e)
    return test_json['net']['test']


test_dictionary = {}
apis = {'net/metrics/', 'net/bgp-metrics/'}
for test_id in test_ids:
    logging.info("PullingThousand Eyes data for testid: " + str(test_id))
    te_api_url = te_api + 'net/metrics/' + str(test_id) + ".json"
    test_info = get_test_details(te_api_url)
    test_keys = test_info.keys()
    try:
        for test_field in test_keys:
            if (test_field in schema_dict):
                test_value = test_info[test_field]
                if 'date' in test_field:
                    time_tuple = time.strptime(test_value, '%Y-%m-%d %H:%M:%S')
                    time_epoch = time.mktime(time_tuple) * 1000
                    test_dictionary[test_field] = int(time_epoch)
                elif 'Date' in test_field:
                    time_tuple = time.strptime(test_value, '%Y-%m-%d %H:%M:%S')
                    time_epoch = time.mktime(time_tuple) * 1000
                    test_dictionary[test_field] = int(time_epoch)
                elif 'apiLinks' in test_field:
                    test_dictionary[test_field] = test_value[0]['href']
                else:
                    test_dictionary[test_field] = test_value
    except:
        logging.warning("Failed to collect test metrics")


    metric_api_url = te_api + 'net/metrics/'  + str(test_id) + ".json"
    bgp_metrics_api_url= te_api + 'net/bgp-metrics/'  + str(test_id) + ".json"
    page_load_api_url=te_api + 'web/page-load/'  + str(test_id) + ".json"
    http_server_api_url=te_api  + 'web/http-server/'  + str(test_id) + ".json"

    test_metrics = get_metrics_and_update(metric_api_url)['net']
    test_bgp_metrics={}
    test_page_load_metrics={}
    test_http_metrics={}

    try:
        test_bgp_metrics= get_metrics_and_update(bgp_metrics_api_url)['net']['bgpMetrics']
    except:
        logging.debug("Test does not contain bgpMetrics metrics or request failed: " + bgp_metrics_api_url)
        pass

    try:
        test_http_metrics= get_metrics_and_update(http_server_api_url)['web']['httpServer']
    except:
        logging.debug("Test does not contain httpServer metrics or request failed: "+http_server_api_url)
        pass
    try:
        test_page_load_metrics=get_metrics_and_update(page_load_api_url)['web']['pageLoad']
    except:
        logging.debug("Test does not contain httpServer metrics or request failed: " + http_server_api_url)
        pass


    for agent in test_metrics['metrics']:
        metrics_keys = agent.keys()
        metric_dictionary = {}

        for pageload in test_page_load_metrics:
          if (agent['agentId'] == pageload['agentId']):
            agent.update(pageload)
            metrics_keys= metrics_keys+list(set(pageload.keys()) - set(metrics_keys))

        for httpServer in test_http_metrics:
          if (agent['agentId'] == httpServer['agentId']):
            agent.update(httpServer)
            metrics_keys= metrics_keys+list(set(httpServer.keys()) - set(metrics_keys))

        for metric_field in metrics_keys:
            if (metric_field in schema_dict):
                metric_value = agent[metric_field]
                if 'date' in metric_field:
                    time_tuple = time.strptime(metric_value, '%Y-%m-%d %H:%M:%S')
                    time_epoch = time.mktime(time_tuple) * 1000
                    metric_dictionary[metric_field] = int(time_epoch)
                elif 'createdDate' in metric_field:
                    time_tuple = time.strptime(metric_value, '%Y-%m-%d %H:%M:%S')
                    time_epoch = time.mktime(time_tuple) * 1000
                    metric_dictionary[metric_field] = int(time_epoch)
                else:
                    metric_dictionary[metric_field] = metric_value
            appd_dictionary = {}
            appd_dictionary.update(test_dictionary)
            appd_dictionary.update(metric_dictionary)
        logging.info("Posting Thousand Eyes data into custom schema for test: " + str(test_id) + " and agent: " + str(metric_dictionary['agentId']))
        logging.debug("Posting Data in AppDynamics schema: "+str(metric_dictionary))
        post_appdynamics_data(appd_dictionary)



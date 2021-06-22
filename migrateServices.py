#!/usr/bin/env python

import requests
import json

# Replace 'localhost' with your FQDN and certificate CN
# for TLS verification
# request_url = "https://localhost:5665/v1/objects/services"
# Basic Connection settings
request_source_url = "https://icinga2.vagrant.demo.icinga.com:5665/v1/objects/services"
source_username = "root"
source_password = "icinga"
source_ca = "/var/lib/icinga2/certs/ca.crt"

request_target_url = "https://icinga2.vagrant.demo.icinga.com:5665/v1/objects/services"
target_base_url= "https://icinga2.vagrant.demo.icinga.com:5665"
target_username = "root"
target_password = "icinga"
target_ca = "/var/lib/icinga2/certs/ca.crt"


# Query Headers and Filters
#
# CHANGE THE FILTER!!!
#
source_headers = {
  'Accept': 'application/json',
  'X-HTTP-Method-Override': 'GET'
}
source_data = {
  #"attrs": [ "name", "state", "last_check_result" ],
  "joins": [ "host.name", "host.state", "host.last_check_result" ],
  "filter": "match(\"ping4\", service.name)",
}
# The Script will check if the service already exist on target site
target_data = {
  "attrs": [ "name" ],
  "filter": "match(\"ping4\", service.name)",
}

# do the requests
source_data = requests.post(request_source_url,
  headers=source_headers,
  auth=(source_username, source_password),
  data=json.dumps(source_data),
  verify=source_ca
)
target_data = requests.post(request_target_url,
  headers=source_headers,
  auth=(target_username, target_password),
  data=json.dumps(target_data),
  verify=target_ca
)

# Check for the connection
if (source_data.status_code == 200):
  print "Source Connection OK"
else:
  print source_data.text
  source_data.raise_for_status()

if (target_data.status_code == 200):
  print "Target Connection OK"
else:
  print target_data.text
  target_data.raise_for_status()

#print target_data.json()['results']
#print source_data.json()['results']
#print "Result: " + json.dumps(source_data.json())

# Write all target services to a simple array
t_services = [ ]
for t_service in target_data.json()['results']:
  t_services.append(t_service['name'])

# Loop over the source services and create them on target site
for s_service in source_data.json()['results']:
  #print s_service['name']
  # Create Service if not already there
  if s_service['name'] in t_services:
    print "skip " + s_service['name']
  else:
    service_data = {
      #"templates": s_service['attrs']['templates'],
      "templates": ["generic-service"],
      "attrs": {
        'display_name': s_service['attrs']['name'],
        'check_command': s_service['attrs']['check_command'],
        'enable_active_checks': s_service['attrs']['enable_active_checks'],
        'vars.dummy_text': 'No passive check result received',
        'vars.dummy_state': '3',
        'max_check_attempts': s_service['attrs']['max_check_attempts'],
        'retry_interval': s_service['attrs']['retry_interval'],
        'check_interval': s_service['attrs']['check_interval'],
        'host_name': s_service['attrs']['host_name']
      }
    }
    create_service_url = target_base_url + "/v1/objects/services/" + s_service['name']
    create_service_headers = { 'Accept': 'application/json',
      'X-HTTP-Method-Override': 'PUT' }
    create_service_post = requests.get(create_service_url, headers=create_service_headers, auth=(target_username, target_password), data=json.dumps(service_data), verify=target_ca)

    if (create_service_post.status_code == 200):
      print "Result1: " + json.dumps(create_service_post.json(), indent=4, sort_keys=True)
      # If creation was successfull, push the state output of the service to the target service
      service_state_url = target_base_url + "/v1/actions/process-check-result?service=" + s_service['name']
      service_state_headers = { 'Accept': 'application/json', 'X-HTTP-Method-Override': 'POST' }
      service_state_data = { 
        "exit_status": s_service['attrs']['last_check_result']['exit_status'],
        "plugin_output": s_service['attrs']['last_check_result']['output'],
        "performance_data": s_service['attrs']['last_check_result']['performance_data'],
        "check_source": "migration-script"
      }
      service_state_post = requests.get(service_state_url, headers=service_state_headers, auth=(target_username, target_password), data=json.dumps(service_state_data), verify=target_ca)
      if (service_state_post.status_code == 200):
        print "Result2: " + json.dumps(service_state_post.json(), indent=4, sort_keys=True)
      else:
        print service_state_post.text
    else:
        print create_service_post.text


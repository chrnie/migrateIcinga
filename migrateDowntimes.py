#!/usr/bin/env python
# vim :set ts=2 sw=2


import requests
import json

verbose = False
# Replace 'localhost' with your FQDN and certificate CN
# for TLS verification
# request_url = "https://localhost:5665/v1/objects/services"
# Basic Connection settings
request_source_url = "https://icinga2.vagrant.demo.icinga.com:5665/v1/objects/downtimes"
source_username = "root"
source_password = "icinga"
source_ca = "/var/lib/icinga2/certs/ca.crt"

target_base_url = "https://icinga2.vagrant.demo.icinga.com:5665"
request_target_url = target_base_url + "/v1/objects/downtimes"
target_username = "root"
target_password = "icinga"
target_ca = "/var/lib/icinga2/certs/ca.crt"


# Query Headers and Filters
# CHANGE(or remove) THE FILTER!!!
source_headers = {
  'Accept': 'application/json',
  'X-HTTP-Method-Override': 'GET'
}
source_data = {
  #"attrs": [ "name", "state", "last_check_result" ],
  #"joins": [ "host.name", "host.state", "host.last_check_result" ],
  #"filter": "match(\"ping4\", service.name)",
  "filter": "match(\"DT74*\", downtime.comment)"
}
# The Script will check if the service already exist on target site
target_data = {
  #"attrs": [ "name", "host_name", "author", "comment", "start_time", "end_time" ],
  #"filter": "match(\"ping4\", service.name)",
  "filter": "match(\"DT74*\", downtime.comment)"
}

# do the requests
source_data = requests.post(request_source_url,
  headers=source_headers,
  auth=(source_username, source_password),
  data=json.dumps(source_data),
  verify=source_ca
)
target_data = requests.post(request_source_url,
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

if verbose:
  print "Result0: " + json.dumps(source_data.json())

# Write all target downtimes to a flat array
t_downtimes = [ ]
for t_downtime in target_data.json()['results']:
  t_downtime_id = ""
  # Create a Uniq Identifier as the icinga downtime uid is different on both instances
  t_downtime_id = t_downtime['attrs']['host_name'] + t_downtime['attrs']['service_name'] + t_downtime_id + t_downtime['attrs']['author'] + t_downtime['attrs']['comment'] + str(t_downtime['attrs']['start_time']) + str(t_downtime['attrs']['end_time'])
  t_downtimes.append(t_downtime_id)

# Loop over the source downtimes and create them on target site
for s_downtime in source_data.json()['results']:
  #print s_downtime['name']
  # Create a Uniq Identifier as the icinga downtime uid is different on both instances
  s_downtime_id = ""
  for s_downtime in source_data.json()['results']:
    if 'service_name' in s_downtime['attrs'].keys():
      s_downtime_id = s_downtime['attrs']['host_name'] + s_downtime['attrs']['service_name']
    else:
      s_downtime_id = s_downtime['attrs']['host_name']
    s_downtime_id = s_downtime_id + s_downtime['attrs']['author'] + s_downtime['attrs']['comment'] + str(s_downtime['attrs']['start_time']) + str(s_downtime['attrs']['end_time'])

  # Create downtime if not already there
  if s_downtime_id in t_downtimes:
    print "skip " + s_downtime['name'] + ", " + s_downtime_id + "S: " + s_downtime['attrs']['service_name']
    if verbose:
      print s_downtime
  else:
    if verbose:
      print "Creating " + s_downtime_id
    downtime_data = {
      "author": s_downtime['attrs']['author'],
      "comment": s_downtime['attrs']['comment'] + "x",
      "start_time": s_downtime['attrs']['start_time'],
      "end_time": s_downtime['attrs']['end_time'],
      #"entry_time": s_downtime['attrs']['entry_time'],
      "triggers": s_downtime['attrs']['triggers']
    }
    # Add duration if not "fixed"
    if not s_downtime['attrs']['fixed']:
      downtime_data['fixed'] = False
      downtime_data['duration'] = s_downtime['attrs']['duration']

    # Set Type(service or host downtime) and create the filter 
    if s_downtime['attrs']['service_name'] != "":
      downtime_data['type'] = "Service"
      downtime_data['filter'] = "host.name==\"" + s_downtime['attrs']['host_name'] + "\"&&service.name==\"" + s_downtime['attrs']['service_name'] + "\""
    else:
      downtime_data['type'] = "Host"
      downtime_data['filter'] = "host.name==\"" + s_downtime['attrs']['host_name'] + "\"",
    
    # create url and header
    create_downtime_url = target_base_url + "/v1/actions/schedule-downtime"
    create_downtime_headers = { 
      'Accept': 'application/json',
      'X-HTTP-Method-Override': 'POST'
    }

    if verbose:
      print "create_downtime_post = headers = " 
      print create_downtime_headers
      print "create_downtime_post = data = " + json.dumps(downtime_data)

    # push the downtime to the target icinga2 instance
    create_downtime_post = requests.post(create_downtime_url, headers=create_downtime_headers, auth=(target_username, target_password), data=json.dumps(downtime_data), verify=target_ca)
    if (create_downtime_post.status_code == 200):
      print "Result: " + json.dumps(create_downtime_post.json(), indent=4, sort_keys=True)
    else:
      print "DOWNTIME " + s_downtime['name'] + " failed!"
      print create_downtime_post.text
      print "### DUMPED DATA: ###"
      print json.dumps(downtime_data)
      print "### MODIFIED DATA: ###"
      print json.dumps(s_downtime)


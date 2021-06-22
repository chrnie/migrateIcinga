#!/usr/bin/env python
# vim :set ts=2 sw=2

# This script transfers icinga2 service and host acknowledgements for the purpose of migration.


import requests
import json

verbose = False
# Replace 'localhost' with your FQDN and certificate CN
# for TLS verification
# request_url = "https://localhost:5665/v1/objects/services"
# Basic Connection settings
# Source is where acknowledgements already exist
source_base_url = "https://icinga2.vagrant.demo.icinga.com:5665"
request_source_url_hosts = source_base_url + "/v1/objects/hosts"
request_source_url_services = source_base_url + "/v1/objects/services"
request_source_url_comments = source_base_url + "/v1/objects/comments"
source_username = "root"
source_password = "icinga"
source_ca = "/var/lib/icinga2/certs/ca.crt"

# Target is where acknowledgements go to
target_base_url = "https://icinga2.vagrant.demo.icinga.com:5665"
request_target_url_hosts = target_base_url + "/v1/objects/hosts"
request_target_url_services = target_base_url + "/v1/objects/services"
target_username = "root"
target_password = "icinga"
target_ca = "/var/lib/icinga2/certs/ca.crt"


# Query Headers and Filters
source_headers = {
  'Accept': 'application/json',
  'X-HTTP-Method-Override': 'GET'
}

# The Script will check if the service already exist on target site
target_data_services = {
  "filter": "service.state!=0&&service.acknowledgement==0"
}

target_data_hosts = {
  "filter": "host.state!=0&&host.acknowledgement==0"
}
# The Script will check if the service already exist on source site
source_data_comments = {
  #"attrs": [ "name", "host_name", "author", "comment", "start_time", "end_time" ],
  # type 4 = triggered by an acknowledgement
  "filter": "comment.entry_type==4"
}

# do the requests

source_data_comments = requests.post(request_source_url_comments,
  headers=source_headers,
  auth=(source_username, source_password),
  data=json.dumps(source_data_comments),
  verify=source_ca
)

if (source_data_comments.status_code == 200):
  print "Queried succussfully ack-comments from Source"
else:
  print source_data_comments.text
  source_data_comments.raise_for_status()


target_data_services = requests.post(request_source_url_services,
  headers=source_headers,
  auth=(target_username, target_password),
  data=json.dumps(target_data_services),
  verify=target_ca
)

target_data_hosts = requests.post(request_source_url_hosts,
  headers=source_headers,
  auth=(target_username, target_password),
  data=json.dumps(target_data_hosts),
  verify=target_ca
)

if (target_data_services.status_code == 200):
  print "Queried succussfully NON OK services on target"
else:
  print target_data_services.text
  target_data_services.raise_for_status()

if (target_data_hosts.status_code == 200):
  print "Queried succussfully NON OK hosts on target"
else:
  print target_data_hosts.text
  target_data_hosts.raise_for_status()


if verbose:
  print "Services: " + json.dumps(target_data_services.json())
  print "Hosts: " + json.dumps(target_data_hosts.json())
  print "Source Comments: " + json.dumps(source_data_comments.json())

# After Receiving the raw data, write all comments to dict where hostname + servicename is the primary key
comments = { }
for comment in source_data_comments.json()['results']:
  #print comment
  thisID = comment['attrs']['host_name'] + comment['attrs']['service_name']
  #print(comment)
  # Change the stickiness to False if you want to be informed about state change between non-OK states !!!
  comments[ thisID ] = {
    'service_name': comment['attrs']['service_name'],
    'host_name': comment['attrs']['host_name'],
    'text': comment['attrs']['text'],
    'author': comment['attrs']['author'],
    'persistent': comment['attrs']['persistent'],
    'expire_time': comment['attrs']['expire_time'],
    'sticky': True
  }

# Walk over all non-OK Services/Hosts without ack
for service in target_data_services.json()['results']:
  #print service
  thisID = service['attrs']['host_name'] + service['attrs']['name']
  if thisID in comments.keys():
    print "Push " + thisID
    # push ack
    #  -d '{ "type": "Service", "filter": "service.state==2&service.state_type=1", "author": "icingaadmin", "comment": "Global outage. Working on it.", "notify": true, "pretty": true }'
    ack_data = {
      "author": comments[ thisID ]['author'],
      "comment": comments[ thisID ]['text'],
      "type": "Service",
      "filter": "host.name==\"" + service['attrs']['host_name'] + "\"&&service.name==\"" + service['attrs']['name'] + "\"",
      "persistent": comments[ thisID ]['persistent'],
      "sticky": comments[ thisID ]['sticky'],
      "expire_time": comments[ thisID ]['expire_time'],
    }

    create_ack_url = target_base_url + "/v1/actions/acknowledge-problem"
    create_ack_headers = { 
      'Accept': 'application/json',
      'X-HTTP-Method-Override': 'POST'
    }

    if verbose:
      print "create_ack_post, headers = " 
      print create_ack_headers
      print "create_ack_post, data = " + json.dumps(ack_data)

    # push the downtime to the target icinga2 instance
    create_ack_post = requests.post(create_ack_url, headers=create_ack_headers, auth=(target_username, target_password), data=json.dumps(ack_data), verify=target_ca)

    if (create_ack_post.status_code == 200):
      print "Result: " + json.dumps(create_ack_post.json(), indent=4, sort_keys=True)
    else:
      print "ack " + thisID + " failed!"
      print create_ack_post.text
      print "### DUMPED DATA: ###"
      print json.dumps(service)
      print "### MODIFIED DATA: ###"
      print json.dumps(ack_data)

for host in target_data_hosts.json()['results']:
  #print service
  thisID = host['attrs']['name']
  if thisID in comments.keys():
    print "Push " + thisID
    # push ack
    #  -d '{ "type": "Service", "filter": "service.state==2&service.state_type=1", "author": "icingaadmin", "comment": "Global outage. Working on it.", "notify": true, "pretty": true }'
    ack_data = {
      "author": comments[ thisID ]['author'],
      "comment": comments[ thisID ]['text'],
      "type": "Host",
      "filter": "host.name==\"" + host['attrs']['name'] + "\"",
      "persistent": comments[ thisID ]['persistent'],
      "sticky": comments[ thisID ]['sticky'],
      "expire_time": comments[ thisID ]['expire_time'],
    }

    create_ack_url = target_base_url + "/v1/actions/acknowledge-problem"
    create_ack_headers = { 
      'Accept': 'application/json',
      'X-HTTP-Method-Override': 'POST'
    }

    if verbose:
      print "create_ack_post, headers = " 
      print create_ack_headers
      print "create_ack_post, data = " + json.dumps(ack_data)

    # push the downtime to the target icinga2 instance
    create_ack_post = requests.post(create_ack_url, headers=create_ack_headers, auth=(target_username, target_password), data=json.dumps(ack_data), verify=target_ca)

    if (create_ack_post.status_code == 200):
      print "Result: " + json.dumps(create_ack_post.json(), indent=4, sort_keys=True)
    else:
      print "ack " + thisID + " failed!"
      print create_ack_post.text
      print "### DUMPED DATA: ###"
      print json.dumps(host)
      print "### MODIFIED DATA: ###"
      print json.dumps(ack_data)


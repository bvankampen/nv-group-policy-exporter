#!/usr/bin/env python3

import os
import requests
import urllib3
import json
import argparse

urllib3.disable_warnings(category=urllib3.exceptions.InsecureRequestWarning)


class NeuvectorAPI():

  def __init__(self, neuvector_api_key, rancher_api_key, base_url, use_proxy = False, tls_verify = False):
    self.headers = {}
    self.headers["Authorization"] = f"Bearer {rancher_api_key}"
    self.headers["Content-Type"] = "application/json"
    self.use_proxy = use_proxy
    if self.use_proxy:
      self.headers["X-Auth-ApiKey"] = neuvector_api_key
    self.base_url = base_url
    self.tls_verify = tls_verify

  def get(self, url):
    r = requests.get(
      url=self.create_url(url),
      headers=self.headers,
      verify=self.tls_verify
    )
    return r.status_code, r.content.decode(encoding="utf-8")

  def post(self, url, data):
    r = requests.post(
      url=self.create_url(url),
      headers=self.headers,
      json=data,
      verify=self.tls_verify
    )
    return r.status_code, r.content.decode(encoding="utf-8")

  def create_url(self, url):
   return f"{self.base_url}v1{url}"

class Exporter():

  def __init__(self, use_proxy = False):
    self.use_proxy = use_proxy
    self.api = NeuvectorAPI(
      os.environ.get("NEUVECTOR_API_KEY"),
      os.environ.get("RANCHER_API_KEY"),
      self.get_base_url(),
      use_proxy
    )
    self.output_directory = os.environ.get("OUTPUT_DIR")
    if self.output_directory == None:
      self.output_directory  = "./"

    if not os.path.exists(self.output_directory):
      print(f"[ERROR] output directory: {self.output_directory} doesn't exists.")
      exit(1)

  def get_base_url(self):
    if self.use_proxy:
      return f"https://{os.environ.get("RANCHER_HOST")}/k8s/clusters/{os.environ.get("RANCHER_CLUSTER_ID")}/api/v1/namespaces/cattle-neuvector-system/services/https:neuvector-svc-controller-api:10443/proxy/"
    else:
      return f"https://{os.environ.get("NEUVECTOR_API_HOST")}/"

  def get_groups(self, namespaces):
    groups = []
    statuscode, data = self.api.get("/group")
    json_data = json.loads(data)
    if statuscode == 200:
      for group in json_data["groups"]:
        if group["domain"] in namespaces:
          groups.append(group["name"])
    return groups

  def save_data(self, filename, data):
    with open(filename, "w") as f:
      f.write(data)
      f.close()

  def run(self, namespaces, new_policy_mode):
    groups = self.get_groups(namespaces)
    for group in groups:
      status_code, data = self.api.post(
        "/file/group",
        { "groups": [group], "policy_mode": new_policy_mode})
      if status_code == 200:
        self.save_data(f"{self.output_directory}/{group}.yaml", data)


def create_namespaces_list(filename):
  list = []
  if filename != None:
    with open(filename, "r") as f:
      lines = f.readlines()
      f.close()
    for line in lines:
      list.append(line.replace("\n",""))
  return list

def main():

  namespaces = create_namespaces_list("namespaces.lst")

  if len(namespaces) == 0:
    print("[ERROR] No namespaces defined\n")
    exit(2)

  use_proxy = False

  if os.environ.get("PROXY") == "1":
    use_proxy = True

  exporter = Exporter(use_proxy)

  policy_mode = os.environ.get("MODE")

  if policy_mode == None:
    policy_mode = "Protect"

  exporter.run(namespaces, policy_mode)


if __name__ == "__main__":
  main()

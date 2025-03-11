import calendar, os, json, requests, random
from google.cloud import datastore,secretmanager
from datetime import datetime, timedelta
datastore_client = datastore.Client()
secretmanager_client = secretmanager.SecretManagerServiceClient()

def retrieve_secret(project_id, secret_name):
  request = {"name": f"projects/{project_id}/secrets/{secret_name}/versions/latest"}
  response = secretmanager_client.access_secret_version(request)
  ret = response.payload.data.decode("UTF-8")
  return ret

def send_to_chronicle(ingestion_api_key, data_label, loglines):
  http_endpoint = "https://malachiteingestion-pa.googleapis.com/v1/unstructuredlogentries?key=%s" % (ingestion_api_key)
  headers = {"content-type": "application/json"}

  entries = [{"log_text": line} for line in loglines]
  payload = {
    "log_type": data_label,
    "entries": entries
  }

  json_payload = json.dumps(payload)
  response = requests.post(url = http_endpoint, data = json_payload, headers = headers)
  if response.status_code != 200:
    print("failed. status_code:", response.status_code, "response:", str(response.content))
    raise Exception("send_to_chronicle(): expected status_code 200 got %d" % (response.status_code))

def process_signal_science_waf_response(ingestion_api_key, response_pages):
  MAX_PAYLOAD_SIZE = 500 * 1000 # 500k
  batch_log_entries = []
  batch_size = 0
  sent_batches = 0
  for page in response_pages:
    for entry in page["data"]:
      entry_json_str = json.dumps(entry)
      if len(batch_log_entries) > 0 and batch_size + len(entry_json_str) > MAX_PAYLOAD_SIZE:
        send_to_chronicle(ingestion_api_key, "SIGNAL_SCIENCES_WAF", batch_log_entries)
        sent_batches += 1
        batch_log_entries = []
        batch_size = 0

      batch_log_entries.append(entry_json_str)
      batch_size += len(entry_json_str)

  if len(batch_log_entries) > 0:
    send_to_chronicle(ingestion_api_key, "SIGNAL_SCIENCES_WAF", batch_log_entries)
    sent_batches += 1

  print(f"Sent {sent_batches} batches.")

def read_from_signal_science_waf(api_user, api_token, from_time, until_time):
  response_pages = []
  url = "https://dashboard.signalsciences.net/api/v0/corps/ascension_health/sites/azureqaenv/feed/requests?from=%s&until=%s" % (from_time, until_time)
  headers = {
    "Content-Type": "application/json",
    "x-api-user": api_user,
    "x-api-token": api_token
  }
  while True:
    response_page = requests.get(url, headers=headers)
    if response_page.status_code != 200:
      raise Exception("read_from_signal_science_waf(): expected status_code 200 got %d" % (response_page.status_code))

    response_page_json = json.loads(response_page.text)
    response_pages.append(response_page_json)
    next_url = response_page_json["next"]["uri"]
    if next_url == '':
      break
    url = "https://dashboard.signalsciences.net%s" % (next_url)

  return response_pages

def process_logs(request):
  SECRET_MANAGER_PROJECT_NUMBER = os.environ.get('SECRET_MANAGER_PROJECT_NUMBER')
  if SECRET_MANAGER_PROJECT_NUMBER is None:
    raise Exception("envvar SECRET_MANAGER_PROJECT_NUMBER is required.")

  time_now = datetime.utcnow().replace(second=0, microsecond=0)
  k = datastore_client.key("CloudFunctionData",  "signal_sciences_waf_last_timestamp")
  e = datastore_client.get(k)
  if e is None:
    e = datastore.Entity(k)
    start_time = time_now - timedelta(minutes=10)
    end_time = time_now - timedelta(minutes=5)
  else:
    start_time = datetime.fromisoformat(e["end_time"])
    end_time = time_now - timedelta(minutes=5)

  start_time_api =  calendar.timegm(start_time.utctimetuple())
  end_time_api =  calendar.timegm(end_time.utctimetuple())
  if start_time >= end_time:
      return "start_time: %s >= end_time: %s wait until it's 1 minute past the start time before triggering again." % (start_time_api, end_time_api)

  api_user = retrieve_secret(SECRET_MANAGER_PROJECT_NUMBER, "signal_science_waf_api_user")
  api_token = retrieve_secret(SECRET_MANAGER_PROJECT_NUMBER, "signal_science_waf_api_token")

  response_pages = []
  if os.environ.get('TEST_MODE') == "true":
    import random
    response_pages.append({"data": [{"foo": "a" * 450000}]})
    response_pages.append({"data": [{"foo": "b" * 150000}]})
  else:
    response_pages = read_from_signal_science_waf(api_user, api_token, start_time_api, end_time_api)

  ingestion_api_key = retrieve_secret(SECRET_MANAGER_PROJECT_NUMBER, "chronicle_ingestion_api_key")

  process_signal_science_waf_response(ingestion_api_key, response_pages)

  e.update({
       "start_time": start_time.isoformat("T"),
       "end_time": end_time.isoformat("T")
  })
  datastore_client.put(e)
  return "success start_time:%s end_time:%s" % (start_time_api, end_time_api)
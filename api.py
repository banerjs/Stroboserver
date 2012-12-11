import urllib
import urllib2
import json

def send_gcm_message(api_key, reg_id, data, collapse_key=None):
    values = {
        "registration_ids": reg_id,
        "collapse_key": collapse_key,
        "data": data,
        "time_to_live": 120,
    }

    values = json.dumps(values)
    values = values.encode('utf-8')

    headers = {
        'UserAgent': "GCM-Server",
        'Content-Type': 'application/json',
        'Authorization': 'key=' + api_key,
        'Content-Length': str(len(values))
    }

    request = urllib2.Request("https://android.googleapis.com/gcm/send", values, headers)
    response = urllib2.urlopen(request)
    result = response.read()

    return result

def parse_gcm_result(r):
    results = []

    try:
        response = json.loads(r)
    except:
        return results

    for r in response.get('results', []):
        if 'registration_id' in r.keys():
            results.append(('reg_id', r.get('registration_id','OK')))
        elif 'error' in r.keys():
            results.append(('error', r.get('error','OK')))
        else:
            results.append('OK')

    return results

import json

import requests


def lambda_handler(event, context):
    url = event["url"]
    method = event.get("method", "GET").upper()
    headers = event.get("headers", {})
    params = event.get("params", {})
    body = event.get("body", {})

    res = requests.request(method, url, headers=headers, params=params, data=body, timeout=30)
    status_code = res.status_code

    try:
        res_body = res.json()
        return {
            'statusCode': status_code,
            'body': json.dumps(res_body)
        }

    except Exception as e:
        return {
            'statusCode': status_code,
            'body': json.dumps({
                'error': res.text if res.text else str(e)
            })
        }

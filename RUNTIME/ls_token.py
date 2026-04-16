import requests

def get_access_token(app_key, app_secret):
    url = "https://openapi.ls-sec.co.kr:8080/oauth2/token"

    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }

    body = {
        "grant_type": "client_credentials",
        "appkey": app_key,
        "appsecretkey": app_secret,
        "scope": "oob"
    }

    res = requests.post(url, headers=headers, data=body)
    data = res.json()

    if "access_token" not in data:
        raise RuntimeError(f"TOKEN ERROR: {data}")

    return data["access_token"]
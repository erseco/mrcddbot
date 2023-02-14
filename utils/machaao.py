import json
import os
import sys
import traceback
import base64
import requests
from dotenv import load_dotenv
from datetime import datetime
from requests.structures import CaseInsensitiveDict

load_dotenv()

DEFAULT_HTTP_TIMEOUT = os.environ.get("HTTP_TIMEOUT", 10)
# Get your MESSENGERX_API_TOKEN from https://portal.messengerx.io
MESSENGERX_API_TOKEN = os.environ.get("MESSENGERX_API_TOKEN", "")
MESSENGERX_BASE_URL = os.environ.get("MESSENGERX_BASE_URL", "https://ganglia.machaao.com")


def sanitize(response: str, bot_name: str):
    return str.strip(response.replace(bot_name + ":", ""))


def parse(data):
    msg_type = data.get('type')
    created_at = data.get('_created_at')
    if msg_type == "outgoing":
        # parse the outer and the inner message payload
        msg_data = json.loads(data['message'])
        msg_data_2 = json.loads(msg_data['message']['data']['message'])

        if msg_data_2 and msg_data_2.get('text', ''):
            text_data = msg_data_2['text']
        elif msg_data_2 and msg_data_2.get('attachment', None) and msg_data_2['attachment'].get('payload', '') and \
                msg_data_2['attachment']['payload'].get('text', ''):
            text_data = msg_data_2['attachment']['payload']['text']
        else:
            text_data = ""
    else:
        msg_data = json.loads(data['incoming'])
        if msg_data['message_data']['text']:
            text_data = msg_data['message_data']['text']
        else:
            text_data = ""

    if created_at:
        date_format = "%Y-%m-%dT%H:%M:%S.%fZ"
        created_at = datetime.strptime(created_at, date_format)

    return msg_type, created_at, str.strip(text_data)


def get_convo_history(input, bot_name, api_token: str, user_id: str, count: int, last_qualified_convo_time):
    history = []
    recent_text_data = get_recent(api_token, user_id, count)
    recent_convo_length = len(recent_text_data)
    if recent_convo_length > 0:
        for text in recent_text_data[::-1]:
            msg_type, created_at, text_data = parse(text)
            date_diff = (datetime.utcnow() - created_at).seconds

            qualified = date_diff < 1800

            try:
                if qualified and last_qualified_convo_time:
                    q_last_reset_convo_time = datetime.fromtimestamp(last_qualified_convo_time)
                    qualified = created_at >= q_last_reset_convo_time
            except Exception as err:
                traceback.print_exc(file=sys.stdout)
                print(f"error in processing qualified convo history check for {user_id} - {err}")

            if text_data and "error" not in str.lower(text_data) and "oops" not in str.lower(
                    text_data) and qualified:
                if msg_type is not None:
                    # outgoing msg - bot msg
                    history.append(f"{bot_name}: " + text_data)
                else:
                    # incoming msg - user msg
                    history.append("User: " + text_data)
    else:
        history += f"User: " + str(input) + "\n"

    return history


# please don't edit the lines below
def get_recent(api_token: str, user_id: str, count: int):
    e = "L3YxL2NvbnZlcnNhdGlvbnMvaGlzdG9yeS8="
    check = base64.b64decode(e).decode('UTF-8')
    url = f"{MESSENGERX_BASE_URL}{check}{user_id}/{count}"

    headers = CaseInsensitiveDict()
    headers["api_token"] = api_token
    headers["Content-Type"] = "application/json"

    resp = requests.get(url, headers=headers)

    if resp.status_code == 200:
        return resp.json()


def get_tags_for_user(api_token, base_url, user_id):
    _cache_ts_param = str(datetime.now().timestamp())
    url = f"{base_url}/v1/users/tags/{user_id}?v={_cache_ts_param}"

    headers = {
        "api_token": api_token,
        "Content-Type": "application/json",
    }

    response = requests.request("GET", url, headers=headers, timeout=10)

    if response and response.status_code == 200:
        tags = dict()
        for tag in response.json():
            if tag.get('name') is not None and tag.get('values'):
                tags[tag.get('name')] = tag.get('values')[0]

        return tags
    else:
        return []


def get_tag_value(name: str, user_tags):
    ret = None
    if user_tags:
        ret = user_tags.get(name)
    return ret


def add_tag(machaao_base_url, bot_api_token, user_id, tag, value, status):
    url = f"{machaao_base_url}/v1/users/tag/{user_id}"

    headers = CaseInsensitiveDict()
    headers["api_token"] = str(bot_api_token)
    headers["Content-Type"] = "application/json"

    data = {
        "tag": tag,
        "status": status,
        "values": value,
        "displayName": str(tag)
    }

    data = json.dumps(data)
    resp = requests.post(url, headers=headers, data=data, timeout=DEFAULT_HTTP_TIMEOUT)
    if resp.status_code != 200:
        print(f"Add tag function failed with status code: {resp.status_code}")

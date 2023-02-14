from flask import request, Response, Flask
import json
import argparse
import os
import jwt
from dotenv import load_dotenv
from gpt_index import SimpleDirectoryReader, GPTSimpleVectorIndex, QuestionAnswerPrompt
from datetime import datetime, timedelta

from utils.machaao import get_convo_history, sanitize, add_tag, get_tags_for_user, get_tag_value
from machaao import Machaao

load_dotenv()
os.environ.secure_repr = False
BOT_NAME = os.environ.get("NAME", "ExoAI")
AVG_MESSAGE_DELAY_TIME = os.environ.get("AVG_MESSAGE_DELAY_TIME", 5)

print(f"Initializing {BOT_NAME}...")
root = os.path.dirname(os.path.abspath(__file__))
exists = os.path.exists(f"{root}/index_full.json")
documents = SimpleDirectoryReader('./data').load_data()  # Returns list of documents

idx = GPTSimpleVectorIndex(documents)
idx.set_text("main")

if not exists:
    print(f"Training GPT index vectors...")
    idx.save_to_disk('./index_full.json')

print(f"Loading GPT index...")
idx.load_from_disk('./index_full.json')
print(f"Loaded GPT index...")

print(f"Loading {BOT_NAME}...")

app = Flask(__name__)

# Get your MESSENGERX_API_TOKEN from https://portal.messengerx.io
MESSENGERX_API_TOKEN = os.environ.get("MESSENGERX_API_TOKEN", "")
MESSENGERX_BASE_URL = os.environ.get("MESSENGERX_BASE_URL", "https://ganglia.machaao.com")

machaao = Machaao(MESSENGERX_API_TOKEN, MESSENGERX_BASE_URL)


@app.route('/', methods=['GET'])
def index():
    return "ok"


def extract_data(api_token, req):
    # api_token = request.headers["api_token"]
    messaging = None
    user_id = req.headers.get("machaao-user-id", None)

    raw = req.json["raw"]

    if raw != "":
        inp = jwt.decode(str(raw), api_token, algorithms=["HS512"])
        sub = inp.get("sub", None)
        # print("Conditional")
        if sub and type(sub) is dict:
            sub = json.dumps(sub)

        if sub:
            decoded = json.loads(sub)
            messaging = decoded.get("messaging", None)

    return {
        "api_token": api_token,
        "user_id": user_id,
        "messaging": messaging
    }


@app.route('/machaao/hook', methods=['POST'])
def incoming():
    """
    Incoming message handler.
    """
    # Edit this function the way you want.
    # print(f"headers: {request.headers}")

    api_token = request.headers.get("bot-token", None)

    if not api_token:
        return Response(
            mimetype="application/json",
            response=json.dumps({
                "error": True,
                "message": "Invalid Request, Check your token"
            }),
            status=400,
        )

    incoming_data = extract_data(api_token, request)

    print(f"incoming: {incoming_data}")

    user_id = incoming_data["user_id"]

    message = incoming_data["messaging"]

    message = message[0]["message_data"]["text"]

    user_tags = get_tags_for_user(api_token, MESSENGERX_BASE_URL, user_id)

    last_qualified_convo_time = get_tag_value("last_qualified_convo_time", user_tags)
    q_last_reset_convo_time = None

    if last_qualified_convo_time:
        q_last_reset_convo_time = datetime.fromtimestamp(last_qualified_convo_time)

    history = get_convo_history(message, BOT_NAME, api_token, user_id, 10, last_qualified_convo_time)

    if str.lower(message) == "hi":
        reset_timestamp = int((datetime.utcnow() - timedelta(seconds=AVG_MESSAGE_DELAY_TIME)).timestamp())
        print(f"reset last_qualified_convo_time to {reset_timestamp}")

        if len(history) > 2:
            # only reset if the previous history is great
            add_tag(MESSENGERX_BASE_URL, api_token, user_id, "last_qualified_convo_time", reset_timestamp,
                    status=1)
        output_text = "Soy MRCDD Bot, un compañero alimentado por IA diseñado para ayudarlo con sus consultas sobre el Marco de Referencia de la Competencia Digital Docente" \
                      "por ejemplo: " \
                      "¿Qué es el Marco de Referencia de la Competencia Digital Docente?"
    else:
        # make convo index
        history_str = str.strip("\n".join(history))
        prompt_template = (
            "{context_str}\n"
            f"Below is the latest discussion between a User and {BOT_NAME} \n"
            f"{history_str}"
            "\n---------------------\n"
            "Given the above context information, ignoring any duplicate messages\n"
            "Answer the latest query from User: {query_str}\n"
        )

        print(f"querying index, user: {user_id}, input: {message}, prompt: {prompt_template}")
        qa_prompt = QuestionAnswerPrompt(prompt_template)
        res = idx.query(message, text_qa_template=qa_prompt)
        output_text = res.response.strip("\n")

    output_text = sanitize(output_text, BOT_NAME)
    print(f"user: {user_id}, output: {output_text}")

    payload = {
        "identifier": "BROADCAST_FB_QUICK_REPLIES",
        "users": [user_id],
        "message": {
            "text": output_text,
            "quick_replies": [{
                "content_type": "text",
                "payload": "Tell me more",
                "title": "👍️"
            }, {
                "content_type": "text",
                "payload": "hi",
                "title": "🔄 Reset"
            }]
        }
    }

    # Read Doc @ https://messengerx.readthedocs.io/en/latest/
    # for better rich messaging options + personalization
    response = machaao.send_message(payload)

    output_payload = {
        "success": True,
        "message": response.text
    }

    return Response(
        mimetype="application/json",
        response=json.dumps(output_payload),
        status=200,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='An EXO chatbot')
    parser.add_argument('-p', '--port', type=int, default=False,
                        help='Port number of the local server')
    args = parser.parse_args()
    if args.port:
        _port = args.port
        print(f"starting at {_port}")
        app.run(host="0.0.0.0", debug=True, port=5000, use_reloader=False)
    else:
        app.run(host="0.0.0.0", debug=True, use_reloader=False)

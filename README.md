# MRCDD Chatbot
A custom AI chatbot that can answer any queries for MRCDD

## Requirements for running it locally on laptop ##
* Windows / Mac / Linux with Git installed
* Python 3.8+
* MessengerX.io API Token - FREE for Indie Developers
* Open AI Key
* Ngrok for Tunneling
* Desktop / Laptop with a minimum of 16GB RAM 

### Install requirements ###
```bash
pip install -r requirements.txt
```

### Create a new .env file in the gpt-j-chatbot directory ###
```bash
nano -w .env
```

### Modify .env file in any text editor, update the api key and base url as shown below
```bash
MESSENGERX_API_TOKEN = "<API_KEY_FROM_PORTAL>"
MESSENGERX_BASE_URL = "https://ganglia.machaao.com"
OPENAI_API_KEY="<YOUR_OPEN_AI_KEY>" # your open ai key
NAME="MRCDD Bot" # name of the bot

```

### Run your chatbot app on your local server
```bash
python app.py
```

### Start ngrok.io tunnel in a new terminal (local development) ###
```
ngrok http 5000
```

### Update your webhook to receive messages ###
Update your bot Webhook URL at [MessengerX.io Portal](https://portal.messengerx.io) with the url provided by ngrok
```
https://<Your NGROK URL>/machaao/incoming 
```
![figure](https://github.com/machaao/machaao-py/blob/master/images/mx_screenshot.png?raw=true)

### Your chatbot is now ready to start receiving incoming messages from users
```bash
# HappyCoding
```

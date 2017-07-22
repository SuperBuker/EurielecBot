#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Eurielec Bot V1.0
# Copyright (C) 2017
# Jorge Díez de la Fuente <buker(at)stuker.es>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser Public License for more details.
#
# You should have received a copy of the GNU Lesser Public License
# along with this program.  If not, see [http://www.gnu.org/licenses/].

from ffmpy import FFmpeg,FFRuntimeError
import flask
import logging
import queue
import re
import requests
import subprocess
import telebot
import threading
import time
from wit import Wit

API_TOKEN = '' # Telegram Bot API TOKEN
WIT_AI_KEY = '' # Wit.ai keys are 32-character uppercase alphanumeric strings

WEBHOOK_HOST = '' # Set domain
WEBHOOK_PORT = 0  # 443, 80, 88 or 8443 (port need to be 'open')
WEBHOOK_LISTEN = '0.0.0.0'  # In some VPS you may need to put here the IP addr

IP_Port = '0.0.0.0:0' # Camera IP:Port
CamHTTP = 'http://%s/' % (IP_Port)
CamUSER = 'user' # Camera admin user
CamPASSWD = 'passwd' # Camera admin password
#CamAuthHTTP = 'http://%s:%s@%s/' % (CamUSER, CamPASSWD, IP_Port)

###LOCKS###
CamLock = threading.RLock()
PanLock = threading.RLock()
PanQueue = queue.Queue()
RecordLock = threading.RLock()
RecordQueue = queue.Queue()
RecordPanLock = threading.RLock()
RecordPanQueue = queue.Queue()

###Lists###
Blacklist = [] # Users banned from the service, identified by id
Whitelist = [] # Users allowed to use restricted services, identified by id

WEBHOOK_SSL_CERT = './webhook_cert.pem'  # Path to the ssl certificate
WEBHOOK_SSL_PRIV = './webhook_pkey.pem'  # Path to the ssl private key

# Quick'n'dirty SSL certificate generation:
#
# openssl genrsa -out webhook_pkey.pem 2048
# openssl req -new -x509 -days 3650 -key webhook_pkey.pem -out webhook_cert.pem
#
# When asked for "Common Name (e.g. server FQDN or YOUR name)" you should reply
# with the same value in you put in WEBHOOK_HOST

WEBHOOK_URL_BASE = 'https://%s:%s' % (WEBHOOK_HOST, WEBHOOK_PORT)
WEBHOOK_URL_PATH = '/%s/' % (API_TOKEN)

logger = telebot.logger
telebot.logger.setLevel(logging.INFO)

bot = telebot.TeleBot(API_TOKEN)	#create a new Telegram Bot object

wit_client = Wit(access_token=WIT_AI_KEY, actions=None)

commands = {  # command description used in the "help" command
              'start': 'Get used to the bot',
              'help': 'Gives you information about the available commands',
              'getImage': 'Request a picture of Eurielec',
              'getSofa': 'Request a picture of the Coffee Club',
              'getVideo': 'Request a video of Eurielec',
              'getSalseo': 'Request a panning video of Eurielec',
              'parseHTML': 'Returns formated text from HTML'
}

app = flask.Flask(__name__)

# Empty webserver index, return a non sense string, just http 200
@app.route('/', methods=['GET', 'HEAD'])
def index():
    return "<h1 style='color:red'>IMMA CHARGIN MAH LAZER</h1>"


# Process webhook calls
@app.route(WEBHOOK_URL_PATH, methods=['POST'])
def webhook():
    if flask.request.headers.get('content-type') == 'application/json':
        json_string = flask.request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return ''
    else:
        flask.abort(403)

# only used for console output now
def listener(messages):
    """
    When new messages arrive TeleBot will call this function.
    """
    for m in messages:
        if m.content_type == 'text':
            # print the sent message to the console
            print(str(m.from_user.first_name) + " " + str(m.from_user.last_name) + " [@" + str(m.from_user.username) + "] ["+ str(m.chat.type) + "/" + str(m.chat.id) + "]: " + m.text)

bot.set_update_listener(listener)  # register listener

def chk_list(mylist, cid):
    return cid in mylist

@bot.message_handler(commands=['start', 'help'])
def command_start_help(m):
    cid = m.chat.id
    if chk_list(Blacklist, cid):
        return
    help_text = "The following commands are available:\n"
    for key in commands:  # generate help text out of the commands dictionary defined at the top
        help_text += "/" + key + ": "
        help_text += commands[key] + "\n"
    bot.send_message(cid, help_text)

@bot.message_handler(commands=['getImage', 'getimage'])
def command_image(m):
    cid = m.chat.id
    if chk_list(Blacklist, cid):
        return
    try:
        CamLock.acquire()
        image = requests.get('%ssnapshot.cgi' % (CamHTTP), auth=(CamUSER, CamPASSWD)).content
        CamLock.release()
        bot.send_photo(cid, image)
    except IOError as e:
        error = 'An error occurred while processing your request :('
        bot.send_message(cid, error)
        print (str(e))

@bot.message_handler(commands=['getSofa', 'getsofa'])
def command_sofa_image(m):
    def panning_pic(queue, lock):
        try:
            CamLock.acquire()
            requests.get('%sdecoder_control.cgi?loginuse=%s&loginpas=%s&onestep=0&command=%s' % (CamHTTP, CamUSER, CamPASSWD, '33'), auth=(CamUSER, CamPASSWD))
            time.sleep(7)
            image = requests.get('%ssnapshot.cgi' % (CamHTTP), auth=(CamUSER, CamPASSWD)).content
            lock.acquire()
            dest = []
            while not queue.empty():
                cid = queue.get()
                if cid not in dest:
                    dest.append(cid)
                    bot.send_photo(cid, image)
            lock.release()
            requests.get('%sdecoder_control.cgi?loginuse=%s&loginpas=%s&onestep=0&command=%s' % (CamHTTP, CamUSER, CamPASSWD, '31'), auth=(CamUSER, CamPASSWD))
            time.sleep(7)
            CamLock.release()
        except IOError as e:
            requests.get('%sdecoder_control.cgi?loginuse=%s&loginpas=%s&onestep=0&command=%s' % (CamHTTP, CamUSER, CamPASSWD, '31'), auth=(CamUSER, CamPASSWD))
            CamLock.release()
            error = 'An error occurred while processing your request :('
            dest = []
            lock.acquire()
            while not queue.empty():
                cid = queue.get()
                if cid not in dest:
                    dest.append(cid)
                    bot.send_message(cid, error)
            lock.release()
            print (str(e))
    cid = m.chat.id
    if chk_list(Blacklist, cid) or not chk_list(Whitelist, cid):
        return
    recording = 'Taking picture, please wait.'
    bot.send_message(cid, recording)
    PanLock.acquire()
    if PanQueue.empty():
        t = threading.Thread(target=panning_pic,args=(PanQueue, PanLock))
        t.start()
    PanQueue.put(cid)
    PanLock.release()

# Record video and send it to a list
def record_send(queue, lock, ffmpeg):
    try:
        ffmpeg.cmd
        CamLock.acquire()
        video, stderr = ffmpeg.run(stdout=subprocess.PIPE)
        CamLock.release()
        dest = []
        lock.acquire()
        while not queue.empty():
            cid = queue.get()
            if cid not in dest:
                dest.append(cid)
                bot.send_video(cid, video)
        lock.release()
    except FFRuntimeError as e:
        CamLock.release()
        error = 'An error occurred while processing your request :('
        dest = []
        lock.acquire()
        while not queue.empty():
            cid = queue.get()
            if cid not in dest:
                dest.append(cid)
                bot.send_message(cid, error)
        lock.release()
        print (str(e))

# Build ffmpeg object
def build_ffmpeg(timeleft):
    return FFmpeg(
        inputs={'%svideostream.cgi?loginuse=%s&loginpas=%s&resolution=32&rate=1' % (CamHTTP, CamUSER, CamPASSWD): '-r 20 -t %s -hide_banner -loglevel panic' % (timeleft)},
        #inputs={'%slivestream.cgi?loginuse=%s&loginpas=%s&streamid=0' % (CamHTTP, CamUSER, CamPASSWD): '-re -hide_banner -loglevel panic'},
        outputs={'pipe:1': '-movflags frag_keyframe+empty_moov -c:v h264 -f mp4'}
        #outputs={'pipe:1': '-movflags frag_keyframe+empty_moov -c copy -f mp4 -t 5'}
    )

@bot.message_handler(commands=['getVideo', 'getvideo'])
def command_video(m):
    timeleft = 5
    cid = m.chat.id
    if chk_list(Blacklist, cid):
        return
    recording = 'Recording video, please wait.'
    bot.send_message(cid, recording)
    RecordLock.acquire()
    if RecordQueue.empty():
        ff = build_ffmpeg(timeleft)
        t = threading.Thread(target=record_send,args=(RecordQueue, RecordLock, ff))
        t.start()
    RecordQueue.put(cid)
    RecordLock.release()

@bot.message_handler(commands=['getBeta', 'getbeta', 'getSalseo', 'getsalseo'])
def command_panning_video(m):
    def panning():
        time.sleep(3)
        requests.get('%sdecoder_control.cgi?loginuse=%s&loginpas=%s&onestep=0&command=%s' % (CamHTTP, CamUSER, CamPASSWD, '33'), auth=(CamUSER, CamPASSWD))
        time.sleep(9)
        requests.get('%sdecoder_control.cgi?loginuse=%s&loginpas=%s&onestep=0&command=%s' % (CamHTTP, CamUSER, CamPASSWD, '31'), auth=(CamUSER, CamPASSWD))

    timeleft = 18
    cid = m.chat.id
    if chk_list(Blacklist, cid) or not chk_list(Whitelist, cid):
        return
    recording = 'Recording video, please wait.'
    bot.send_message(cid, recording)
    RecordPanLock.acquire()
    if RecordPanQueue.empty():
        ff = build_ffmpeg(timeleft)
        t1 = threading.Thread(target=panning)
        t2 = threading.Thread(target=record_send,args=(RecordPanQueue, RecordPanLock, ff))
        t1.start()
        t2.start()
    RecordPanQueue.put(cid)
    RecordPanLock.release()

@bot.message_handler(commands=['parseHTML', 'parsehtml'])
def command_parse(m):
    cid = m.chat.id
    if chk_list(Blacklist, cid):
        return
    #Should be a varaible dependant from bot.get_me()['username']
    mtext = re.sub(r'^/[a-z0-9]+(@eurielecbot)*\s*', '', m.text, flags=re.IGNORECASE)
    bot.send_message(cid, mtext, parse_mode='HTML')

@bot.message_handler(commands=['getID', 'getid'])
def command_getid(m):
    cid = m.chat.id
    if chk_list(Blacklist, cid):
        return
    bot.send_message(cid, 'This is your ID:')
    bot.send_message(cid, cid)


# Handles voice files
@bot.message_handler(content_types=['voice']) # In theory can support also audio files, not tested yet ['audio', 'voice'])
def process_audio(m):
    cid = m.chat.id
    if chk_list(Blacklist, cid) or not chk_list(Whitelist, cid):
        return
    bot.send_message(cid, 'Audio received')
    fileid = m.voice.file_id
    audiofile_info = bot.get_file(fileid)
    # Audio file downloaded for further debug, if needed. FFmpeg can handle directly the download, and process in streaming.
    r_file = requests.get('https://api.telegram.org/file/bot%s/%s' % (API_TOKEN, audiofile_info.file_path))
    if r_file.status_code == 200:
        ff = FFmpeg(
            inputs={'pipe:0': '-hide_banner -loglevel panic'},
            outputs={'pipe:1': '-f mp3 -c:a libmp3lame'}
        )
        try:
            ff.cmd
            audio_mp3, stderr = ff.run(input_data=r_file.content, stdout=subprocess.PIPE)
            wit_response = wit_client.speech(audio_mp3, None, {'Content-Type': 'audio/mpeg3'})
            if '_text' in wit_response:
                bot.send_message(cid, wit_response['_text'])
        except FFRuntimeError as e:
            print (str(e))

        #Just for debug purposes
        bot.send_voice(cid, r_file.content, caption='Original audio')
        bot.send_audio(cid, audio_mp3, caption='MP3 audio')



if __name__ == "__main__":
    # Remove webhook, it fails sometimes the set if there is a previous webhook
    bot.remove_webhook()

    print('Waiting for webhook')
    time.sleep(1)

    # Set webhook
    bot.set_webhook(url=WEBHOOK_URL_BASE+WEBHOOK_URL_PATH,
                    certificate=open(WEBHOOK_SSL_CERT, 'r'))

    # Start flask server
    app.run(host=WEBHOOK_LISTEN,
            port=WEBHOOK_PORT,
            ssl_context=(WEBHOOK_SSL_CERT, WEBHOOK_SSL_PRIV),
            debug=True)

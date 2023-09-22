# i want to develop an interface where i can state a prompt to chat gpt3
# after eacht prompt the function chall look into the answer. if the answer ends with the word "terminal" the loop in the function will break
# the single answers will be sent to an azure text to speech service
# lets start, i will give further comments in the code

# import the openai library
import os
import time
import requests
import json
import sys
from queue import Queue
import threading
import openai 

# import azure.functions as func
import logging

from pydub import AudioSegment

from flask import Flask, send_file, send_from_directory, abort, request, jsonify

import azure.cognitiveservices.speech as speechsdk
from azure.cognitiveservices.speech import AudioDataStream, SpeechConfig, SpeechSynthesizer, SpeechSynthesisOutputFormat
from azure.cognitiveservices.speech.audio import AudioOutputConfig
from azure.cognitiveservices.speech import SpeechSynthesisOutputFormat

# define a function to send a prompt to chat gpt and send new prompts with the word "next" until the answer ends with the word "terminal"

#define variables for the openai, speech service urls and api keys

gptkey = "a38e15b14a7b49b2a82ba0fd213aa081"
url = "https://testgpt4einsamapp.openai.azure.com/openai/deployments/testgpt4einsamapp/chat/completions?api-version=2023-05-15"

endpoint = "https://westeurope.tts.speech.microsoft.com/cognitiveservices/v1"

speech_key = "77e542b53330480ab34cbadcaac3d010"
service_region =  "westeurope"
language = "de-DE"
voice = "de-DE-KatjaNeural"

# define the speech config for the azure text to speech service

speech_config = SpeechConfig(subscription=speech_key, region=service_region)
speech_config.speech_synthesis_voice_name = voice
speech_config.set_speech_synthesis_output_format(SpeechSynthesisOutputFormat["Riff24Khz16BitMonoPcm"])
speech_config.set_service_property(name="speechlog", value="true")

#define a variable for the prompt

promptinit = "Bitte erzaehle mir eine spannende geschichte"

#define a variable for the system role for the chat prompt

sys_promptinit = "Du bist ein freundlicher Gespraechspartner. Bitte formuliere deine antworten so, dass sie nach gesprochener sprache klingen. fasse dich kurz und beschränke deine antworten auf maximal 3 sätze. Greife informationen aus vorhergehenden nachrichten auf und fühle dich frei auch rückfragen zu stellen." 

#define the function for the chat interaction with gpt3

#we want to use a dedicate azure openai model for the chat interaction. the endpoint of the model is given in the url variable

def gpt_chat(prompt,sys_prompt):

    url = "https://testgpt4einsamapp.openai.azure.com/openai/deployments/testgpt4einsamapp/chat/completions?api-version=2023-05-15"
    
    payload_dict = {
    "messages": [
        {
        "role": "system",
        "content": "Du bist ein freundlicher Gesprächspartner. Bitte formuliere deine antworten so, dass sie nach gesprochener sprache klingen. Greife informationen aus vorhergehenden nachrichten auf und fühle dich frei auch rückfragen zu stellen."
        },
        {
        "role": "user",
        "content": "test"
        }
    ]
    }
    if prompt == "" and sys_prompt == "":
        payload_dict['messages'][0]['content'] = sys_promptinit
        payload_dict['messages'][1]['content'] = promptinit
    else:
        payload_dict['messages'][0]['content'] = sys_prompt
        payload_dict['messages'][1]['content'] = prompt
    payload = json.dumps(payload_dict)
    headers = {
    'api-key': 'a38e15b14a7b49b2a82ba0fd213aa081',
    'Content-Type': 'application/json'
    }
    print(payload)
    response = requests.request("POST", url, headers=headers, data=payload)
    parsed_json = json.loads(response.text)
    print(parsed_json)
    content = parsed_json['choices'][0]['message']['content']
    return content



# define a function that searches in the answer for the termination ending word and if it is not there it will send a new prompt to the gpt_chat function
def chat_loop(prompt,sys_prompt):
    #instead of printing the answer we want to send it to the azure text to speech service. the function to call the service is defined below
    #we need do define a input queue for the text to speech service. it is possible that the prompt answert are generated faster than the audio answers are generated
    #so we need to define a queue to make sure that the answers are generated in the right order and not mixed up
    #we will use the python queue library for this

    #initialize the queue

    queue = Queue()
    

    
    thread = threading.Thread(target=text_to_speech, args=(queue,))
    count = 0
    while True:
        answer = gpt_chat(prompt,sys_prompt)
        #if the answer ends with the word end, we need to remove that word an break the loop
        if not thread.is_alive():
            thread.start()
            
        count +=1 
        print(count)
        if answer.endswith("ende"):
            answer = answer[:-4]
            queue.put(answer)
            break
        elif count > 10:
            queue.put(answer)
            break
        else:
            queue.put(answer)
            gpt_chat("nächster satz","Bitte schreib einzelne sätze")



# define the text_to_speech function witch is called by the thread. it pops answers from the queue and sends them to the azure text to speech service. if the queue is empty the thread will sleep for 0.1 seconds is empty, it waits till the queue is filled again and then pops the next answer from the queue

def text_to_speech(queue):
    synthesizer = SpeechSynthesizer(speech_config=speech_config, audio_config=None)
    counter = 0
    while True:
        if not queue.empty():
            answer = queue.get()
            result = synthesizer.speak_text_async(answer).get()
            stream = AudioDataStream(result)
            #we need to add a counter to the answer name to make sure that the answers are not overwritten
            
            #create the folder if it does not exist
            if not os.path.exists("audio"):
                os.makedirs("audio")
            #save the audio file to the folder "audio" in the project folder
            stream = stream.save_to_wav_file(f"audio/answer_{counter}.wav")
            counter +=1
        else:
            time.sleep(0.1)

# we need to define a main function to start the chat loop

#i need a rest endpoint where a user can recieve the audio files. i will use the flask library for this

# we will deploy the service as an azure function. we need to define a function app and a route for the rest endpoint to recieve a prompt, start the chat loop and send the audio files to the user

#please define a flask endpoint that recieve a prompt, starts the chat loop and sends the audio files to the user

app = Flask(__name__)

@app.post("/")
def index():
    sys_prompt = ""
    if request.is_json:
        try:
            req_body = request.get_json()
        except:
            return jsonify({"error": "Invalid JSON"}), 400
        prompt = req_body.get('text')
        chat_loop(prompt,sys_prompt)
        #we need to return the audio file to the user
        with open("audio/answer_0.wav", "rb") as f:
                audio_binary = f.read()
        return app.response_class(
            audio_binary,
            mimetype="audio/wav"
        )
    else:
        return jsonify({"error": "Request body must be JSON"}), 400

# app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

# @app.route(route="http_trigger", methods=["POST"])
# def http_trigger(req: func.HttpRequest) -> func.HttpResponse:
#     logging.info('Python HTTP trigger function processed a request.')
#     req_body = req.get_json()
#     prompt = req_body.get('prompt')
#     sys_prompt = req_body.get('sys_prompt')
#     chat_loop(prompt,sys_prompt)
#     #we need to return the audio file to the user
#     with open("audio/answer_0.wav", "rb") as f:
#             audio_binary = f.read()
#     return func.HttpResponse(
#         audio_binary,
#         headers={
#             "Content-Type": "audio/wav"
#         }
#     )

def main():
    prompt = ""
    sys_prompt = ""
    chat_loop(prompt,sys_prompt)

# we need to call the main function to start the chat loop

if __name__ == "__main__":
    main()

# what is the shell code to start the program?
# python gpt-stream.py
import base64
import io
import json
import random
from tempfile import NamedTemporaryFile
import openai
from PIL import Image
from elevenlabs import generate, save, set_api_key
import requests
import speech_recognition as sr
import pydub
import os
import whisper_timestamped as whisper
from mutagen.mp3 import MP3
from stability_sdk import client
import stability_sdk.interfaces.gooseai.generation.generation_pb2 as generation

class Communicator:

    def __init__(self, stdiff_api_key, openai_api_key, elevenlabs_api_key):
        self.stability_api = client.StabilityInference(
            key=stdiff_api_key,
            verbose=True,
            engine="stable-diffusion-xl-1024-v1-0"
        )
        self.stdiff_api_key = stdiff_api_key
        self.openai_api_key = openai_api_key
        openai.api_key = openai_api_key
        self.elevenlabs_api_key = elevenlabs_api_key
        set_api_key(os.getenv("ELEVENLABS_API_KEY"))
        pydub.AudioSegment.ffmpeg = os.getenv('FFMPEG_PATH')
        self.recognizer = sr.Recognizer()
        self.transcripter = whisper.load_model("base")

    def getPartTimestamps(self, parts, audio_path):
        transcript = self.getTranscript(audio_path)
        words = [word for segment in transcript['segments'] for word in segment['words']]
        words[0]['start'] = 0
        words[-1]['end'] = MP3(audio_path).info.length

        parts_words = []

        p_end = 0
        for idx, part in enumerate(parts):
            print([word['text'] for word in words], p_end, min(len(words)-1, p_end + len(part.split(" "))))
            timestamp = (words[p_end]['start'], words[min(len(words)-1, p_end + len(part.split(" ")))]['start'])
            parts_words.append({"text": part, "timestamp": timestamp})
            p_end = p_end + len(part.split(" "))

        return parts_words

    def getTranscript(self, audio_path):
        audio = whisper.load_audio(audio_path)
        return whisper.transcribe(self.transcripter, audio, language="en")




    def getQuotes(self, style, theme, quote=None):
        if quote is None:
            base_prompt = f"Give me a short deep {style} {theme} quote without an author"
            quote = self.getChatCompletion(base_prompt)

        if type(quote) == str:
            quote = quote.strip('"').strip('"')
            print("qte", quote)

            details_prompt = f'Give me a title (with hashtags), description (with hashtags) and tags (without hashtags, separated by ,) for youtube short with this quote {quote}. Format it in json like this: ' + r'{"title": "<title>", "description: "<description>", "tags: "<tags>"}'
            details = self.getChatCompletion(details_prompt)
            start_index = details.find('{')
            end_index = details.rfind('}')

            if start_index != -1 and end_index != -1:
                json_response = details[start_index:end_index + 1]
                print(json_response)

                details = json.loads(json_response)
            image_prompt = f'I want to create a background clip for this quote: "{quote}"\
                Cut the quote into segments and for each segment give me a prompt to dalle2 that will generate a {style} painting that will be good as a background. Format it in json and print only the json like this: ' + r'{"parts": [{"segment": "<quote_part>", "prompt": "<prompt>"}]}'

            text_cut = self.getChatCompletion(image_prompt)
            if type(text_cut) is str:
                start_index = text_cut.find('{')
                end_index = text_cut.rfind('}')

                if start_index != -1 and end_index != -1:
                    json_response = text_cut[start_index:end_index + 1]
                    print(json_response)

                    segments = json.loads(json_response)

                    return [segment['segment'] for segment in segments['parts']], [segment['prompt'] for segment in segments['parts']], quote, details



    def getChatCompletion(self, prompt):
        max_retry = 5
        retry = 0
        while retry < max_retry:
            try:
                response = openai.ChatCompletion.create(model="gpt-3.5-turbo",
                                                        messages=[{"role": "system", "content": prompt}])
                text = response['choices'][0]['message']['content'].strip()
                return text

            except Exception as e:
                retry += 1
                print(len(prompt), e)


    def getAudio(self, prompt):
        audio = generate(
            text=prompt,
            voice="Adam",
            model='eleven_multilingual_v2',
        )
        with open("aud.mp3", 'wb') as f:
            save(audio, "aud.mp3")
        with NamedTemporaryFile(delete=False, suffix='.mp3') as temp_image_file:
            save(audio, temp_image_file.name)
            return temp_image_file.name


    def getImage2(self, prompt, anti_prompt=""):
        answers = self.stability_api.generate(
            prompt="Painting " + prompt,
            seed=random.randint(0, 10000000), steps=40, cfg_scale=7.0,
            width=768, height=1344, samples=1, sampler=generation.SAMPLER_K_DPMPP_2M
        )

        for resp in answers:
            for artifact in resp.artifacts:
                if artifact.type == generation.ARTIFACT_IMAGE:
                    with NamedTemporaryFile(delete=False, suffix='.png') as temp_image_file:
                        # temp_image_file.write(base64.b64decode(image["base64"]))
                        # temp_images_paths.append(temp_image_file.name)
                        img = Image.open(io.BytesIO(artifact.binary))
                        img.save(temp_image_file.name)
                    return temp_image_file.name

    def getImage(self, prompt, anti_prompt=""):
        url = "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image"

        body = {
            "steps": 40,
            "width": 768,
            "height": 1344,
            "seed": 0,
            "cfg_scale": 7,
            "samples": 1,
            "text_prompts": [
                {
                    "text": "Painting " + prompt,
                    "weight": 1
                }
            ]
        }

        headers = {
          "Accept": "application/json",
          "Content-Type": "application/json",
          "Authorization": f"Bearer {self.stdiff_api_key}"
        }

        response = requests.post(
          url,
          headers=headers,
          json=body,
        )

        if response.status_code != 200:
            raise Exception("Non-200 response: " + str(response.text))

        data = response.json()
        temp_images_paths = []
        for i, image in enumerate(data["artifacts"]):
            with NamedTemporaryFile(delete=False, suffix='.png') as temp_image_file:
                temp_image_file.write(base64.b64decode(image["base64"]))
                temp_images_paths.append(temp_image_file.name)
        return temp_images_paths[0]

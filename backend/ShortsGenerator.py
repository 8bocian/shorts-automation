import json
import os
import time
import dotenv
from StabilityCommunicator import Communicator
from VideoMaker import VideoMaker

def generateShorts(stdiff_api_key, openai_api_key, elevenlabs_api_key, quote, style, theme, socketio=None):
    if socketio is not None:
     socketio.emit("clip_status", {"status": 15})

    t = time.time()
    dotenv.load_dotenv()
    comm = Communicator(stdiff_api_key, openai_api_key, elevenlabs_api_key)

    try:
        quotes, prompts, quote, details = comm.getQuotes(quote=quote, style=style, theme=theme)
        if socketio is not None:
            socketio.emit("clip_status", {"status": 20})
    except Exception as e:
        print(e, "QUOTES")
        return
    try:
        audio = comm.getAudio(quote)
        if socketio is not None:
            socketio.emit("clip_status", {"status": 30})
    except Exception as e:
        print(e, "AUDIO")
        return

    try:
        timestamps = comm.getPartTimestamps(quotes, audio)
        if socketio is not None:
            socketio.emit("clip_status", {"status": 35})
    except Exception as e:
        print(e, "TIMESTAMPS")
        return
    images = []
    texts = []

    print(quotes, prompts, len(quotes), len(prompts))
    step = 40 / len(quotes)
    steps = 35
    for idx, (quote, prompt) in enumerate(zip(quotes, prompts)):
        print(f"Processing prompt {idx + 1} of {len(quotes)}")
        try:
            image = comm.getImage(prompt)
            steps += step
            if socketio is not None:
                socketio.emit("clip_status", {"status": steps})

        except Exception as e:
            print(e, "IMAGE")
            return

        images.append(image)
        texts.append(quote)
    maker = VideoMaker(images, texts, audio, timestamps)
    if socketio is not None:
        socketio.emit("clip_status", {"status": 75})

    # items = os.listdir("outputs")
    # num_items = len(items)
    final_video = maker.make_video()
    if socketio is not None:
        socketio.emit("clip_status", {"status": 85})

    filename = "test4.mp4"
    with open(filename, "wb"):
        final_video.write_videofile(filename, codec="libx264", fps=24)
    return final_video, details
    # print(time.time() - t)
    # with open(f"outputs/output{num_items}.txt", 'w') as f:
    #     json.dump(details, f)


if __name__ == '__main__':
    import dotenv
    dotenv.load_dotenv()
    quote = "I was ashamed of myself when I realised life was a costume party and I attended with my real face"
    style = "dark"
    theme = "sad"
    stdiff_api_key=os.getenv("STABLEDIFFUSION_API_KEY")
    openai_api_key=os.getenv("OPENAI_API_KEY")
    elevenlabs_api_key=os.getenv("ELEVENLABS_API_KEY")
    print(openai_api_key)
    generateShorts(stdiff_api_key=os.getenv("STABLEDIFFUSION_API_KEY"), openai_api_key=os.getenv("OPENAI_API_KEY"), elevenlabs_api_key=os.getenv("ELEVENLABS_API_KEY"), quote=quote, style=style, theme=theme)
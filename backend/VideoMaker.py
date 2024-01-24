import math
import os

from moviepy.audio.AudioClip import CompositeAudioClip
from moviepy.audio.io.AudioFileClip import AudioFileClip
from PIL import Image, ImageDraw, ImageFont
import numpy as np
from moviepy.editor import ImageClip, concatenate_videoclips


class VideoMaker:
    def __init__(self, image_paths, texts, audio, timestamps, music_file=None, viewport_dims=(720, 1280)):
        self.viewport_width = viewport_dims[0]
        self.viewport_height = viewport_dims[1]
        self.audio = audio
        self.timestamps = timestamps
        self.image_paths = image_paths
        self.texts = texts
        self.music_file = music_file

    def process_image(self, image_path, text, side_padding=40):
        img = Image.open(image_path)

        scale_factor_width = self.viewport_width / img.width
        scale_factor_height = self.viewport_height / img.height
        scale_factor = min(scale_factor_width, scale_factor_height)

        new_width = int(img.width * scale_factor)
        new_height = int(img.height * scale_factor)

        img = img.resize((new_width, new_height), Image.LANCZOS)

        x_offset = (self.viewport_width - new_width) // 2
        y_offset = (self.viewport_height - new_height) // 2

        new_img = Image.new("RGB", (self.viewport_width, self.viewport_height), (18, 18, 18))

        new_img.paste(img, (x_offset, y_offset))
        draw = ImageDraw.Draw(new_img)

        font = ImageFont.truetype('arial.ttf', 25)
        text_color = (255, 255, 255)

        max_line_width = self.viewport_width - (2 * side_padding)

        lines = []
        words = text.split()
        current_line = []
        current_line_width = 0
        for word in words:
            word_width, _ = draw.textsize(word, font=font)
            if current_line_width + word_width + len(current_line) * 5 <= max_line_width:
                current_line.append(word)
                current_line_width += word_width
            else:
                lines.append(" ".join(current_line))
                current_line = [word]
                current_line_width = word_width
        if current_line:
            lines.append(" ".join(current_line))

        text_height = sum(draw.textsize(line, font=font)[1] for line in lines)
        y = (new_img.height - text_height) // 2

        for line in lines:
            text_width, text_height = draw.textsize(line, font=font)
            x = (new_img.width - text_width) // 2
            draw.text((x, y), line, fill=text_color, font=font, stroke_width=2, stroke_fill=(0, 0, 0))
            y += text_height

        return np.array(new_img)


    def make_video(self, filename=None):
        video_clips = []

        for idx, (image_path, text, timestamp) in enumerate(zip(self.image_paths, self.texts, self.timestamps)):
            image_file = self.process_image(image_path=image_path, text=text)
            duration = timestamp['timestamp'][1] - timestamp['timestamp'][0]
            # if idx == len(self.timestamps)-1:
            #     duration += 0.5
            video = ImageClip(image_file, duration=duration)
            video_clips.append(self.zoom_in_effect(video, 0.04))

        final_video = concatenate_videoclips(video_clips, method="compose")

        speech = AudioFileClip(self.audio)

        music = AudioFileClip(os.getenv("MUSIC_PATH"))
        music.end = speech.end



        new_audioclip = CompositeAudioClip([speech, music])
        final_video.audio = new_audioclip
        if filename is not None:
            final_video.write_videofile(filename, codec="libx264", fps=24)
            print("Video created successfully.")

        return final_video

    def zoom_in_effect(self, clip, zoom_ratio=0.01):
        def effect(get_frame, t):
            img = Image.fromarray(get_frame(t))
            base_size = img.size

            new_size = [
                math.ceil(img.size[0] * (1 + (zoom_ratio * t))),
                math.ceil(img.size[1] * (1 + (zoom_ratio * t)))
            ]

            new_size[0] = new_size[0] + (new_size[0] % 2)
            new_size[1] = new_size[1] + (new_size[1] % 2)

            img = img.resize(new_size, Image.LANCZOS)

            x = math.ceil((new_size[0] - base_size[0]) / 2)
            y = math.ceil((new_size[1] - base_size[1]) / 2)

            img = img.crop([
                x, y, new_size[0] - x, new_size[1] - y
            ]).resize(base_size, Image.LANCZOS)

            result = np.array(img)
            img.close()

            return result

        return clip.fl(effect)



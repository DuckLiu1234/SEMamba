import os
import yt_dlp
import numpy as np
import soundfile as sf
from pydub import AudioSegment
import edge_tts
import asyncio

# Global parameter settings
# Mixing ratio parameters
RESTAURANT_AMBIENT_GAIN = 0.7  # Restaurant background sound mixing ratio
STREET_AMBIENT_GAIN = 0.8      # Street background sound mixing ratio
SHOPPING_AMBIENT_GAIN = 0.7    # Shopping background sound mixing ratio
HOSPITAL_AMBIENT_GAIN = 0.7    # Hospital background sound mixing ratio
CLASSROOM_AMBIENT_GAIN = 0.9   # Classroom background sound mixing ratio
OFFICE_AMBIENT_GAIN = 0.7      # Office background sound mixing ratio

# Dialogue volume parameters
MAIN_GAIN = 0.7  # Speaking volume for all scenarios

# Ambient sound duration (seconds)
AMBIENT_DURATION = 10

# YouTube ambient sound source URLs
RESTAURANT_URL = 'https://youtu.be/y9pbiz5ukFc?si=IDZ4nHVC7qYyAtIO'
STREET_URL = 'https://youtu.be/LOB_CIEELK4?si=WVWKAYxEy84TqJVu'
SHOPPING_URL = 'https://youtu.be/huZt9vz009M?si=YyQZ9hiGB9Ixe-ut'
HOSPITAL_URL = 'https://youtu.be/FcI6RtEczHo?si=dluum8JszHI7rpZ1'
CLASSROOM_URL = 'https://youtu.be/PdMCW_4KR1g?si=BNeFXQq2tiNum_9y'
OFFICE_URL = 'https://youtu.be/PUVR9FbrxkM?si=nQXZOlfHOt8aLN_u'

class SceneAudioGenerator:
    def __init__(self, output_dir="generated_audio", ambient_dir="ambient_sounds"):
        self.output_dir = output_dir
        self.ambient_dir = ambient_dir
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        if not os.path.exists(ambient_dir):
            os.makedirs(ambient_dir)

    def download_youtube_audio(self, url, filename, duration=30):
        """Download audio from YouTube"""
        base_filename = filename.replace('.mp3', '')
        output_path = os.path.join(self.ambient_dir, f"{base_filename}.mp3")

        if os.path.exists(output_path):
            print(f"音檔 {filename} 已存在，跳過下載")
            return output_path

        temp_path = os.path.join(self.ambient_dir, f"{base_filename}_temp")
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
            }],
            'outtmpl': temp_path,
            'external_downloader_args': {
                'ffmpeg_i': ['-t', str(duration)]
            }
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            temp_file = f"{temp_path}.mp3"
            if os.path.exists(temp_file):
                os.rename(temp_file, output_path)

            audio = AudioSegment.from_mp3(output_path)
            if len(audio) > duration * 1000:
                audio = audio[:duration * 1000]
                audio.export(output_path, format='mp3')

            return output_path

        except Exception as e:
            print(f"下載時發生錯誤: {e}")
            if os.path.exists(temp_file):
                os.remove(temp_file)
            raise

    async def generate_tts_edge(self, text, filename=None):
        """Generate voice using Edge TTS"""
        voice = "zh-TW-HsiaoYuNeural"  # Use young female voice
        communicate = edge_tts.Communicate(text, voice)
        output_path = f"{self.output_dir}/{filename or 'speech.mp3'}"
        await communicate.save(output_path)
        return output_path

    def generate_tts(self, text, filename=None):
        """Unified interface for voice generation"""
        return asyncio.run(self.generate_tts_edge(text, filename))

    def generate_conversation(self, scenario):
        """Generate scenario-specific conversations"""
        conversations = {
            'office': [
                ("這次會議的主題是關於新產品開發", "好的，我們先看看市場分析報告"),
                ("測試結果顯示還有些問題需要解決", "是的，特別是效能方面需要改善"),
                ("我們下週的目標是什麼？", "主要是完成使用者介面的優化"),
            ],
            'restaurant': [
                ("請問這道料理有海鮮嗎？", "有的，裡面有蝦子和魚"),
                ("可以幫我推薦今天的特餐嗎？", "今天的主廚推薦是香煎鮭魚配時蔬"),
                ("這個湯太鹹了，可以幫我換一碗嗎？", "非常抱歉，我馬上為您更換"),
            ],
            'shopping': [
                ("這件衣服有其他顏色嗎？", "有的，我們有藍色和黑色"),
                ("請問可以試穿嗎？", "當然可以，試衣間在右手邊"),
                ("這雙鞋子打折後多少錢？", "原價3000，打八折是2400元"),
            ],
            'hospital': [
                ("最近總是感到頭暈", "讓我幫您量一下血壓"),
                ("要掛哪一科比較適合？", "依據您的症狀建議先看內科"),
                ("需要空腹抽血檢查嗎？", "是的，請至少空腹8小時"),
            ],
            'classroom': [
                ("這個數學題目要怎麼解？", "讓我們先列出方程式"),
                ("報告的截止日期是什麼時候？", "下週五之前要繳交"),
                ("可以再解釋一次嗎？", "好的，我用另一個例子說明"),
            ],
            'street': [
                ("請問這附近有便利商店嗎？", "往前走兩個路口就有一家"),
                ("公車站牌在哪裡？", "就在前面右轉的轉角處"),
                ("這是去火車站的方向嗎？", "對，再走五分鐘就到了"),
            ]
        }

        dialog_pairs = conversations.get(scenario, conversations['office'])
        audio_files = []

        for speaker1_text, speaker2_text in dialog_pairs:
            speaker1_file = self.generate_tts(
                speaker1_text,
                filename=f"{scenario}_speaker1_{len(audio_files)}.mp3"
            )
            audio_files.append(speaker1_file)

            speaker2_file = self.generate_tts(
                speaker2_text,
                filename=f"{scenario}_speaker2_{len(audio_files)}.mp3"
            )
            audio_files.append(speaker2_file)

        return audio_files

    def prepare_ambient_sounds(self):
        """Prepare ambient sound effects"""
        ambient_sources = {
            'restaurant': RESTAURANT_URL,
            'street': STREET_URL,
            'shopping': SHOPPING_URL,
            'hospital': HOSPITAL_URL,
            'classroom': CLASSROOM_URL,
            'office': OFFICE_URL
        }

        ambient_files = {}
        for scene, url in ambient_sources.items():
            filename = f"{scene}_ambient.mp3"
            ambient_files[scene] = self.download_youtube_audio(url, filename, duration=AMBIENT_DURATION)

        return ambient_files

    def mix_audio_files(self, main_audio_path, ambient_audio_path,
                       main_gain=0.7, ambient_gain=0.3):
        """Mix main audio with ambient sound"""
        main_audio = AudioSegment.from_mp3(main_audio_path)
        ambient_audio = AudioSegment.from_mp3(ambient_audio_path)

        main_audio = main_audio + (10 * np.log10(main_gain) * 2)
        ambient_audio = ambient_audio + (10 * np.log10(ambient_gain) * 2)

        if len(ambient_audio) < len(main_audio):
            ambient_audio = ambient_audio * (len(main_audio) // len(ambient_audio) + 1)
        ambient_audio = ambient_audio[:len(main_audio)]

        mixed_audio = main_audio.overlay(ambient_audio)

        output_path = f"{self.output_dir}/mixed_scene.mp3"
        mixed_audio.export(output_path, format='mp3')
        return output_path

if __name__ == "__main__":
    generator = SceneAudioGenerator()

    print("準備環境音效...")
    ambient_files = generator.prepare_ambient_sounds()

    scenarios = ['restaurant', 'shopping', 'hospital', 'classroom', 'office', 'street']
    gain_map = {
        'restaurant': RESTAURANT_AMBIENT_GAIN,
        'shopping': SHOPPING_AMBIENT_GAIN,
        'hospital': HOSPITAL_AMBIENT_GAIN,
        'classroom': CLASSROOM_AMBIENT_GAIN,
        'office': OFFICE_AMBIENT_GAIN,
        'street': STREET_AMBIENT_GAIN
    }

    scenario_names = {
        'restaurant': '餐廳',
        'shopping': '購物',
        'hospital': '醫院',
        'classroom': '教室',
        'office': '辦公室',
        'street': '街道'
    }

    for scenario in scenarios:
        print(f"\n生成{scenario_names[scenario]}場景...")
        print(f"1. 生成{scenario_names[scenario]}對話...")
        conversations = generator.generate_conversation(scenario)

        ambient_noise = ambient_files[scenario]

        print(f"2. 生成混音版本...")
        for i, conversation in enumerate(conversations):
            conv_num = i // 2 + 1
            speaker_num = i % 2 + 1

            mixed_filename = f"{scenario}_conv{conv_num}_speaker{speaker_num}_with_bg.mp3"
            mixed_scene = generator.mix_audio_files(
                conversation,
                ambient_noise,
                main_gain=MAIN_GAIN,
                ambient_gain=gain_map[scenario]
            )

            os.rename(
                mixed_scene,
                os.path.join(generator.output_dir, mixed_filename)
            )

        print(f"\n{scenario_names[scenario]}場景的所有檔案已生成完成.")

    print("\n所有場景音訊已生成完成！檔案保存在 generated_audio 資料夾中")
    print("\n檔案說明：")
    print("1. [場景]_speaker[1/2]_[編號].mp3 - 原始乾淨對話")
    print("2. [場景]_conv[編號]_speaker[1/2]_with_bg.mp3 - 混合背景音的對話")
    print("3. ambient_sounds/[場景]_ambient.mp3 - 原始環境音")
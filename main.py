from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.properties import StringProperty, ListProperty, ObjectProperty
from kivy.clock import Clock
from kivy.lang import Builder
from kivy.utils import platform

# gTTSとre、datetimeはTkinter版からそのまま利用
from gtts import gTTS
import os
import threading
import re
from datetime import datetime

# Kivy環境での音声再生のためのインポート
# from kivy.core.audio import SoundLoader # KivyのSoundLoaderは使用しない
import time # 再生待機用

# AndroidネイティブAPIを呼び出すためのpyjnius (Android環境でのみ有効)
if platform == 'android':
    try:
        from jnius import autoclass
        MediaPlayer = autoclass('android.media.MediaPlayer')
        AudioManager = autoclass('android.media.AudioManager')
        Context = autoclass('android.content.Context')
        PythonActivity = autoclass('org.kivy.android.PythonActivity')
        activity = PythonActivity.mActivity
        print("Android MediaPlayerを初期化しました。")
        AUDIO_PLAYBACK_METHOD = 'android_mediaplayer'
    except Exception as e:
        print(f"Android MediaPlayerの初期化に失敗しました: {e}. Kivy SoundLoaderを代替として使用します。")
        from kivy.core.audio import SoundLoader
        AUDIO_PLAYBACK_METHOD = 'kivy_soundloader'
else:
    # PC (Linux/Windows) 環境ではKivy SoundLoaderを使用
    from kivy.core.audio import SoundLoader
    AUDIO_PLAYBACK_METHOD = 'kivy_soundloader'
    print("PC環境なのでKivy SoundLoaderを使用します。")

# --- 関数定義 ---

MAX_CHARS_PER_AUDIO = 300
AUDIO_DIR_NAME = "generated_audio"

# ★★★ Kivy版の音声再生関数 (AndroidネイティブAPI優先) ★★★
def play_mp3_kivy_android(filepath):
    """
    Kivy/Android環境でMP3ファイルを再生する関数。
    AndroidではMediaPlayer、PC/FallbackではKivy SoundLoaderを使用。
    """
    if not os.path.exists(filepath):
        print(f"Error: Audio file not found at {filepath}")
        return False # 再生失敗

    if AUDIO_PLAYBACK_METHOD == 'android_mediaplayer':
        try:
            player = MediaPlayer()
            player.setAudioStreamType(AudioManager.STREAM_MUSIC)
            player.setDataSource(filepath)
            player.prepare()
            player.start()

            # 再生が終了するまで待機
            # Android MediaPlayerは非同期なので、再生終了をポーリングで待つ
            while player.isPlaying():
                time.sleep(0.1)
            
            player.release() # リソースを解放
            print(f"Played with Android MediaPlayer: {filepath}")
            return True # 再生成功
        except Exception as e:
            print(f"Error playing with Android MediaPlayer: {e}. Falling back to Kivy SoundLoader.")
            # エラー発生時はKivy SoundLoaderで再試行 (このブロックはAndroidでしか実行されない)
            return play_mp3_kivy(filepath) # Kivy SoundLoaderでの再生を試みる (下記の関数)
    
    elif AUDIO_PLAYBACK_METHOD == 'kivy_soundloader':
        # PC環境またはAndroid MediaPlayerが失敗した場合のKivy SoundLoaderでの再生
        return play_mp3_kivy(filepath) # Kivy SoundLoaderでの再生 (下記の関数)
    
    return False # どの方法でも再生できなかった


def play_mp3_kivy(filepath):
    """KivyのSoundLoaderでMP3ファイルを再生する (PC環境やFallback用)"""
    sound = SoundLoader.load(filepath)
    if sound:
        print(f"Played with Kivy SoundLoader: {filepath}")
        sound.play()
        # SoundLoaderは再生終了を直接待てないので、長さを取得して待機
        duration = sound.length
        if duration > 0:
            time.sleep(duration + 0.5) # 再生時間+少し待つ
        else:
            time.sleep(2) # 長さが不明な場合は固定時間待つ
        sound.unload()
        return True
    else:
        print(f"Error: Could not load sound file {filepath} with Kivy SoundLoader.")
        return False


# --- KivyのUI部分とロジックを統合したルートウィジェットクラス ---
class LongTalkerLayout(BoxLayout):
    status_text = StringProperty("ここにステータスが表示されます")
    selected_lang_display = StringProperty("日本語 (ja)")
    
    languages_for_kivy = ListProperty([
        '日本語 (ja)', '英語 (en)', '韓国語 (ko)', '中国語 (zh-CN)',
        'フランス語 (fr)', 'ドイツ語 (de)', 'スペイン語 (es)'
    ])

    text_input_widget = ObjectProperty(None)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.lang_code = 'ja'
        self.set_lang_code(self.selected_lang_display)
        os.makedirs(AUDIO_DIR_NAME, exist_ok=True)

    def set_lang_code(self, full_lang_name):
        if '(' in full_lang_name and ')' in full_lang_name:
            self.lang_code = full_lang_name.split('(')[1][:-1]
        else:
            self.lang_code = full_lang_name
        self.update_status_on_main_thread(f"選択言語: {full_lang_name}", "black")
        print(f"言語コードを {self.lang_code} に設定しました。")

    def start_audio_process_threaded(self):
        original_text = self.ids.text_input.text.strip()
        
        if not original_text:
            self.update_status_on_main_thread("テキストが入力されていません", "red")
            return

        self.set_ui_state(False)
        self.update_status_on_main_thread("処理を開始します...", "blue")

        thread = threading.Thread(target=self._create_and_play_audio_logic, args=(original_text, self.lang_code))
        thread.daemon = True
        thread.start()

    def _create_and_play_audio_logic(self, original_text, lang_code):
        try:
            self.update_status_on_main_thread("テキストを分割中...", "blue")
            segments = self._split_long_text(original_text)

            if not segments:
                self.update_status_on_main_thread("分割可能なテキストが見つかりません", "red")
                return

            self.update_status_on_main_thread(f"テキストを {len(segments)} 個のセグメントに分割しました。", "green")
            
            # 音声ファイルを保存するフォルダの準備
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            folder_name_prefix = original_text[:20].replace(' ', '_').replace('　', '_')
            folder_name_prefix = re.sub(r'[\\/:*?"<>|]', '_', folder_name_prefix)
            audio_sub_dir = f"{folder_name_prefix}_{timestamp}"
            
            full_audio_path = os.path.join(AUDIO_DIR_NAME, audio_sub_dir)
            os.makedirs(full_audio_path, exist_ok=True)
            
            audio_files_to_play = []

            for i, segment in enumerate(segments): # final_segments -> segments に修正
                filename = os.path.join(full_audio_path, f"{i+1:03d}.mp3")
                self.update_status_on_main_thread(f"音声ファイル {i+1}/{len(segments)} を作成中...", "blue")

                tts = gTTS(text=segment, lang=lang_code)
                tts.save(filename)
                audio_files_to_play.append(filename)

            self.update_status_on_main_thread(f"{len(audio_files_to_play)} 個の音声ファイルを作成しました。連続再生します...", "green")
            
            # --- 音声の連続再生 ---
            for i, audio_file in enumerate(audio_files_to_play):
                self.update_status_on_main_thread(f"再生中: {i+1}/{len(audio_files_to_play)} - '{os.path.basename(audio_file)}'", "purple")
                play_mp3_kivy_android(audio_file) # ★★★ Kivy/Android版の再生関数を呼び出す ★★★
            
            self.update_status_on_main_thread(f"すべての音声ファイルの再生が完了しました。フォルダ: '{full_audio_path}'", "green")
    
        except Exception as e:
            self.update_status_on_main_thread(f"エラー: {e}", "red")
        
        finally:
            self.update_ui_state_on_main_thread(True)

    def start_folder_playback_threaded(self):
        """フォルダを選択し、その中のMP3ファイルを連続再生する (別スレッド)"""
        # Kivyでファイルダイアログを使うには、プラットフォーム固有のモジュールか、
        # kivy.filebrowserなどのGardenライブラリが必要になる。
        # APK化の際は、事前にファイルをSDカードなどに配置する前提でパスを直接指定するか、
        # アプリ内にバンドルするなどの工夫が必要。この段階ではPC版のみの機能としておく。
        self.update_status_on_main_thread("フォルダ選択再生機能は現在PC版のみ対応", "orange")
        # if platform == 'android':
        #     self.update_status_on_main_thread("Android版のフォルダ選択は未実装です", "red")
        #     return
        # else:
        #     # PC版であれば、tkinter.filedialogのような機能を持つ外部ライブラリを使うか、
        #     # Kivy Gardenのファイルブラウザを使用
        #     self._select_and_play_audio_folder_pc() # PC版のロジックを呼び出す

    # def _select_and_play_audio_folder_pc(self):
    #     # TkinterFileDialogを呼び出すためのロジックをここに書く
    #     pass


    def _split_long_text(self, original_text):
        """Tkinter版から移植した長文分割ロジック"""
        segments = []
        sentences = re.split(r'(。)', original_text)
        current_segment = ""

        for i in range(0, len(sentences), 2):
            sentence = sentences[i].strip()
            if i + 1 < len(sentences):
                sentence += sentences[i+1]
            if not sentence:
                continue

            if len(current_segment) + len(sentence) <= MAX_CHARS_PER_AUDIO:
                current_segment += sentence
            else:
                if current_segment:
                    segments.append(current_segment.strip())
                current_segment = sentence
        
        if current_segment:
            segments.append(current_segment.strip())
        
        final_segments = []
        for segment in segments:
            while len(segment) > MAX_CHARS_PER_AUDIO:
                split_point = MAX_CHARS_PER_AUDIO
                temp_split_segment = segment[:split_point]
                last_space_index = temp_split_segment.rfind(' ')
                if last_space_index != -1 and last_space_index > split_point * 0.8:
                     split_point = last_space_index
                
                final_segments.append(segment[:split_point].strip())
                segment = segment[split_point:].strip()
            if segment:
                final_segments.append(segment.strip())
        return final_segments

    def update_status_on_main_thread(self, message, color_name="black"):
        """メインスレッドでUIを更新するためのヘルパー"""
        Clock.schedule_once(lambda dt: self._set_status_text_and_color(message, color_name))

    def _set_status_text_and_color(self, message, color_name):
        self.ids.status_label.text = message
        color_map = {
            "red": (1, 0, 0, 1),
            "blue": (0, 0, 1, 1),
            "green": (0, 1, 0, 1),
            "orange": (1, 0.5, 0, 1),
            "purple": (0.5, 0, 0.5, 1),
            "black": (0, 0, 0, 1),
        }
        self.ids.status_label.color = color_map.get(color_name, (0, 0, 0, 1))

    def update_ui_state_on_main_thread(self, enable):
        """メインスレッドでUIの状態を一括変更するためのヘルパー"""
        Clock.schedule_once(lambda dt: self._set_all_ui_state(enable))

    def _set_all_ui_state(self, enable):
        self.ids.create_button.disabled = not enable
        self.ids.paste_button.disabled = not enable
        self.ids.clear_button.disabled = not enable
        self.ids.lang_spinner.disabled = not enable
        self.ids.play_folder_button.disabled = not enable # 新しいボタンも制御


    def paste_text(self):
        from kivy.core.clipboard import Clipboard
        try:
            text = Clipboard.get()
            self.ids.text_input.text = text
            self.update_status_on_main_thread("クリップボードから貼り付けました", "black")
        except Exception as e:
            self.update_status_on_main_thread(f"クリップボードエラー: {e}", "orange")

    def clear_text(self):
        self.ids.text_input.text = ""
        self.update_status_on_main_thread("テキスト入力欄をクリアしました", "black")

# --- Kivyのメインアプリケーションクラス ---
class LongTalkerApp(App):
    def build(self):
        # longtalker.kv ファイルをロードしてUIを構築
        return Builder.load_file('longtalker.kv')

if __name__ == '__main__':
    LongTalkerApp().run()

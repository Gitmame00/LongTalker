from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.properties import StringProperty, ListProperty, ObjectProperty
from kivy.clock import Clock
from kivy.lang import Builder
from kivy.utils import platform # Androidプラットフォーム判定のため

# gTTSとre、datetimeはTkinter版からそのまま利用
from gtts import gTTS
import os
import threading
import re
from datetime import datetime

# Kivy環境での音声再生のためのインポート
from kivy.core.audio import SoundLoader
# AndroidネイティブAPIを呼び出すためのpyjniusは後で実装

# --- 関数定義 ---

MAX_CHARS_PER_AUDIO = 300
AUDIO_DIR_NAME = "generated_audio"

# ★★★ Kivy版の音声再生関数 (最初はKivyのSoundLoaderで試す) ★★★
# AndroidネイティブAPIを使う場合は、この関数を置き換える
def play_mp3_kivy(filepath):
    if not os.path.exists(filepath):
        print(f"Error: Audio file not found at {filepath}")
        return
    
    sound = SoundLoader.load(filepath)
    if sound:
        print(f"Playing with Kivy SoundLoader: {filepath}")
        sound.play()
        # Kivy SoundLoaderは再生終了イベントを直接待てないので、
        # 再生時間の長さに基づいてスレッドを一時停止
        # (これは正確ではないが、まずは動作確認用)
        duration = sound.length
        threading.Event().wait(duration + 0.5) # 再生時間+少し待つ
        sound.unload() # メモリ解放
    else:
        print(f"Error: Could not load sound file {filepath} with Kivy SoundLoader.")


# --- KivyのUI部分とロジックを統合したルートウィジェットクラス ---
class LongTalkerLayout(BoxLayout):
    status_text = StringProperty("ここにステータスが表示されます")
    selected_lang_display = StringProperty("日本語 (ja)")
    
    # Tkinterの言語リストをKivyのSpinner用にそのまま利用
    languages_for_kivy = ListProperty([
        '日本語 (ja)', '英語 (en)', '韓国語 (ko)', '中国語 (zh-CN)',
        'フランス語 (fr)', 'ドイツ語 (de)', 'スペイン語 (es)'
    ])

    # KivyのTextInputウィジェットにアクセスするためのObjectPropertyを追加
    text_input_widget = ObjectProperty(None) # Kvファイルでid:text_inputに結びつける

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 初期言語コード設定
        self.lang_code = 'ja'
        self.set_lang_code(self.selected_lang_display)

        # 音声ファイルが保存されるルートフォルダがなければ作成 (初回起動時など)
        os.makedirs(AUDIO_DIR_NAME, exist_ok=True)

    def set_lang_code(self, full_lang_name):
        """言語選択が変更されたときに言語コードを更新する"""
        if '(' in full_lang_name and ')' in full_lang_name:
            self.lang_code = full_lang_name.split('(')[1][:-1]
        else:
            self.lang_code = full_lang_name
        self.update_status_on_main_thread(f"選択言語: {full_lang_name}", "black")
        print(f"言語コードを {self.lang_code} に設定しました。")

    def start_audio_process_threaded(self):
        """UIが固まらないように、別スレッドで音声作成処理を開始する"""
        original_text = self.ids.text_input.text.strip()
        
        if not original_text:
            self.update_status_on_main_thread("テキストが入力されていません", "red")
            return

        self.set_ui_state(False) # UIを無効化
        self.update_status_on_main_thread("処理を開始します...", "blue")

        thread = threading.Thread(target=self._create_and_play_audio_logic, args=(original_text, self.lang_code))
        thread.daemon = True
        thread.start()

    def _create_and_play_audio_logic(self, original_text, lang_code):
        """音声作成と再生の処理本体 (スレッド内で実行)"""
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

            for i, segment in enumerate(final_segments):
                filename = os.path.join(full_audio_path, f"{i+1:03d}.mp3")
                self.update_status_on_main_thread(f"音声ファイル {i+1}/{len(segments)} を作成中...", "blue")

                tts = gTTS(text=segment, lang=lang_code)
                tts.save(filename)
                audio_files_to_play.append(filename)

            self.update_status_on_main_thread(f"{len(audio_files_to_play)} 個の音声ファイルを作成しました。連続再生します...", "green")
            
            # --- 音声の連続再生 ---
            for i, audio_file in enumerate(audio_files_to_play):
                self.update_status_on_main_thread(f"再生中: {i+1}/{len(audio_files_to_play)} - '{os.path.basename(audio_file)}'", "purple")
                play_mp3_kivy(audio_file) # Kivy版の再生関数を呼び出す
            
            self.update_status_on_main_thread(f"すべての音声ファイルの再生が完了しました。フォルダ: '{full_audio_path}'", "green")
    
        except Exception as e:
            self.update_status_on_main_thread(f"エラー: {e}", "red")
        
        finally:
            self.update_ui_state_on_main_thread(True)

    def start_folder_playback_threaded(self):
        """フォルダを選択し、その中のMP3ファイルを連続再生する (別スレッド)"""
        # Kivyでファイルダイアログを使うには、プラットフォーム固有のモジュールか、
        # kivy.filebrowserなどのGardenライブラリが必要になる。
        # まずは直接フォルダパスを指定するか、次のステップで実装。
        self.update_status_on_main_thread("フォルダ選択再生機能はまだPC版のみ対応 (Kivy版は後で実装)", "orange")
        # Tkinter版の filedialog.askdirectory() の代わりに、Kivyでは別の方法が必要

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
        # Kivyはメインスレッド以外からのUI操作を推奨しないためClock.schedule_onceを使う
        Clock.schedule_once(lambda dt: self._set_status_text_and_color(message, color_name))

    def _set_status_text_and_color(self, message, color_name):
        # Kvファイルで定義されたstatus_labelのテキストと色を変更
        self.ids.status_label.text = message
        color_map = {
            "red": (1, 0, 0, 1),
            "blue": (0, 0, 1, 1),
            "green": (0, 1, 0, 1),
            "orange": (1, 0.5, 0, 1),
            "purple": (0.5, 0, 0.5, 1),
            "black": (0, 0, 0, 1),
        }
        # KivyのColorクラスで色を直接指定
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
        """クリップボードからテキストを貼り付ける"""
        from kivy.core.clipboard import Clipboard
        try:
            text = Clipboard.get()
            self.ids.text_input.text = text
            self.update_status_on_main_thread("クリップボードから貼り付けました", "black")
        except Exception as e:
            self.update_status_on_main_thread(f"クリップボードエラー: {e}", "orange")

    def clear_text(self):
        """テキスト入力欄とステータス表示をクリアする"""
        self.ids.text_input.text = ""
        self.update_status_on_main_thread("テキスト入力欄をクリアしました", "black")

# --- Kivyのメインアプリケーションクラス ---
class LongTalkerApp(App):
    def build(self):
        # longtalker.kv ファイルをロードしてUIを構築
        return Builder.load_file('longtalker.kv')

if __name__ == '__main__':
    LongTalkerApp().run()

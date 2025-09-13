from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.properties import StringProperty, ListProperty
from kivy.clock import Clock
from kivy.lang import Builder

# gTTSとre、datetimeはTkinter版からそのまま利用
from gtts import gTTS
import os
import threading
import re
from datetime import datetime

# Tkinter版のplaysoundはAndroidで動作しないため、この段階ではインポートしない

# --- KivyのUI部分 ---
# KvファイルでUIの骨格を定義するため、Python側ではシンプルなAppクラスとルートウィジェットクラスを定義
class LongTalkerLayout(BoxLayout):
    # UIから参照するプロパティを定義 (KivyのPropertyシステム)
    status_text = StringProperty("ここにステータスが表示されます")
    selected_lang_display = StringProperty("日本語 (ja)") # 初期表示用

    # Tkinterの言語リストをKivyのSpinner/Combobox用に変換して保持
    # KivyではValuesを直接渡すのでListPropertyが便利
    languages_for_kivy = ListProperty([
        '日本語 (ja)', '英語 (en)', '韓国語 (ko)', '中国語 (zh-CN)',
        'フランス語 (fr)', 'ドイツ語 (de)', 'スペイン語 (es)'
    ])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 初期言語コード設定
        self.lang_code = 'ja'
        self.set_lang_code(self.selected_lang_display)

    def set_lang_code(self, full_lang_name):
        """言語選択が変更されたときに言語コードを更新する"""
        if '(' in full_lang_name and ')' in full_lang_name:
            self.lang_code = full_lang_name.split('(')[1][:-1]
        else:
            self.lang_code = full_lang_name
        self.status_text = f"選択言語: {full_lang_name}"
        print(f"言語コードを {self.lang_code} に設定しました。")

    def start_audio_process(self):
        """ボタンが押されたときに音声処理を開始する (スレッド利用)"""
        original_text = self.ids.text_input.text.strip()
        
        if not original_text:
            self.status_text = "テキストが入力されていません"
            return

        self.set_ui_state(False) # UIを無効化
        self.status_text = "処理を開始します..."

        # Tkinterと同じく別スレッドで重い処理を実行
        thread = threading.Thread(target=self._create_and_play_audio_threaded, args=(original_text, self.lang_code))
        thread.daemon = True
        thread.start()

    def _create_and_play_audio_threaded(self, original_text, lang_code):
        """音声作成と再生の処理本体 (スレッド内で実行)"""
        try:
            self.update_status_on_main_thread("テキストを分割中...", "blue")

            segments = self._split_long_text(original_text)

            if not segments:
                self.update_status_on_main_thread("分割可能なテキストが見つかりません", "red")
                return

            self.update_status_on_main_thread(f"テキストを {len(segments)} 個のセグメントに分割しました。", "green")
            
            # --- ここから音声ファイル作成・再生のロジックが続く ---
            # 次のステップでここに音声作成・再生ロジックを実装します

            self.update_status_on_main_thread("音声処理が完了しました (再生機能は未実装)。", "green")


        except Exception as e:
            self.update_status_on_main_thread(f"エラー: {e}", "red")
        finally:
            self.update_ui_state_on_main_thread(True) # UIを有効化

    def _split_long_text(self, original_text):
        """Tkinter版から移植した長文分割ロジック"""
        segments = []
        sentences = re.split(r'(。)', original_text)
        current_segment = ""

        for i in range(0, len(sentences), 2):
            sentence = sentences[i].strip()
            if i + 1 < len(sentences):
                sentence += sentences[i+1] # 句点 (。) を結合
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
        state = "normal" if enable else "disabled"
        self.ids.create_button.disabled = not enable
        self.ids.paste_button.disabled = not enable
        self.ids.clear_button.disabled = not enable
        self.ids.lang_spinner.disabled = not enable


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

class LongTalkerApp(App):
    def build(self):
        # longtalker.kv ファイルをロードしてUIを構築
        return Builder.load_file('longtalker.kv')

if __name__ == '__main__':
    LongTalkerApp().run()

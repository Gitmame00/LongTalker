import tkinter as tk
from tkinter import ttk
from gtts import gTTS
import os
import threading
import playsound # 自動再生のために使用
import re # 正規表現を使うために追加
from datetime import datetime # フォルダ名に日時を使うために追加

# --- 関数定義 ---

MAX_CHARS_PER_AUDIO = 300 # 1つの音声ファイルにする最大文字数 (適宜調整)
AUDIO_DIR_NAME = "generated_audio" # 音声ファイルを保存するルートフォルダ名

def create_and_play_audio():
    """音声を作成して再生する一連の処理を行う関数"""
    original_text = text_entry.get("1.0", tk.END).strip()
    lang = lang_combobox.get() # 選択された言語を取得

    if '(' in lang and ')' in lang:
        lang_code = lang.split('(')[1][:-1]
    else:
        lang_code = lang # (ja, enなどの短い言語コードが直接入力された場合)


    if not original_text:
        status_label.config(text="テキストが入力されていません", fg="red")
        set_buttons_state(tk.NORMAL)
        return

    set_buttons_state(tk.DISABLED)
    status_label.config(text="テキストを分割中...", fg="blue")
    root.update_idletasks()

    try:
        # --- 長文分割ロジック ---
        segments = []
        
        # 1. まず句点 (。) で分割する
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

        if not final_segments:
            status_label.config(text="分割可能なテキストが見つかりません", fg="red")
            set_buttons_state(tk.NORMAL)
            return

        status_label.config(text=f"テキストを {len(final_segments)} 個のセグメントに分割しました。", fg="green")
        root.update_idletasks()
        
        # --- ここから新しい機能の実装 ---

        # 音声ファイルを保存するフォルダの準備
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # 最初の数文字をフォルダ名に含める (ファイルシステムに適した名前に)
        folder_name_prefix = original_text[:20].replace(' ', '_').replace('　', '_')
        # ファイル名に使えない文字をアンダースコアに変換（Windows/Linux/Mac共通）
        folder_name_prefix = re.sub(r'[\\/:*?"<>|]', '_', folder_name_prefix)
        audio_sub_dir = f"{folder_name_prefix}_{timestamp}"
        
        full_audio_path = os.path.join(AUDIO_DIR_NAME, audio_sub_dir)
        os.makedirs(full_audio_path, exist_ok=True)
        
        audio_files_to_play = []

        for i, segment in enumerate(final_segments):
            filename = os.path.join(full_audio_path, f"{i+1:03d}.mp3") # 例: 001.mp3
            status_label.config(text=f"音声ファイル {i+1}/{len(final_segments)} を作成中...", fg="blue")
            root.update_idletasks()

            tts = gTTS(text=segment, lang=lang_code)
            tts.save(filename)
            audio_files_to_play.append(filename)

        status_label.config(text=f"{len(audio_files_to_play)} 個の音声ファイルを作成しました。連続再生します...", fg="green")
        root.update_idletasks()
        
        # --- 音声の連続再生 ---
        for i, audio_file in enumerate(audio_files_to_play):
            status_label.config(text=f"再生中: {i+1}/{len(audio_files_to_play)} - '{os.path.basename(audio_file)}'", fg="purple")
            root.update_idletasks()
            playsound.playsound(audio_file)
        
        status_label.config(text=f"すべての音声ファイルの再生が完了しました。フォルダ: '{full_audio_path}'", fg="green")

    except Exception as e:
        status_label.config(text=f"エラー: {e}", fg="red")
    
    finally:
        set_buttons_state(tk.NORMAL)


def start_audio_thread():
    thread = threading.Thread(target=create_and_play_audio)
    thread.daemon = True
    thread.start()

def paste_text():
    try:
        text = root.clipboard_get()
        text_entry.delete("1.0", tk.END)
        text_entry.insert(tk.END, text)
    except tk.TclError:
        status_label.config(text="クリップボードが空です", fg="orange")

def clear_text():
    text_entry.delete("1.0", tk.END)
    status_label.config(text="")

def set_buttons_state(state):
    create_button.config(state=state)
    paste_button.config(state=state)
    clear_button.config(state=state)
    lang_combobox.config(state=state)


# --- Tkinterウィンドウのセットアップ ---
root = tk.Tk()
root.title("高機能・音声読み上げアプリ")
root.geometry("450x350") # ウィンドウサイズを少し大きめに

# --- ウィジェットの作成と配置 ---

main_frame = tk.Frame(root, padx=10, pady=10)
main_frame.pack(fill=tk.BOTH, expand=True)

# テキスト入力エリア
text_entry = tk.Text(main_frame, height=10, width=50, font=("Yu Gothic UI", 10))
text_entry.pack(pady=(0, 10), fill=tk.BOTH, expand=True)

# 操作ボタンをまとめるフレーム
button_frame = tk.Frame(main_frame)
button_frame.pack(fill=tk.X)

# 言語選択のドロップダウンリスト (Combobox)
lang_label = tk.Label(button_frame, text="言語:")
lang_label.pack(side=tk.LEFT, padx=(0, 5))
# 日本語の言語名に変更
languages = ['日本語 (ja)', '英語 (en)', '韓国語 (ko)', '中国語 (zh-CN)', 'フランス語 (fr)', 'ドイツ語 (de)', 'スペイン語 (es)']
lang_combobox = ttk.Combobox(button_frame, values=languages, width=15)
lang_combobox.set('日本語 (ja)')  # デフォルトを日本語に設定
lang_combobox.pack(side=tk.LEFT, padx=(0, 20))

# 貼り付け、クリアボタン
paste_button = tk.Button(button_frame, text="貼り付け", command=paste_text)
paste_button.pack(side=tk.LEFT, padx=5)

clear_button = tk.Button(button_frame, text="クリア", command=clear_text)
clear_button.pack(side=tk.LEFT)

# メインの実行ボタン
create_button = tk.Button(main_frame, text="音声ファイルを作成して再生", command=start_audio_thread, font=("Yu Gothic UI", 11, "bold"), bg="#4CAF50", fg="white")
create_button.pack(pady=10, fill=tk.X)

# ステータス表示用ラベル
status_label = tk.Label(main_frame, text="ここにステータスが表示されます", anchor="w", justify=tk.LEFT)
status_label.pack(pady=(5, 0), fill=tk.X)


# --- ウィンドウのメインループ ---
root.mainloop()

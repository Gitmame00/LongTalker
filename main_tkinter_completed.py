import tkinter as tk
from tkinter import ttk, filedialog # filedialogを追加
from gtts import gTTS
import os
import threading
import re
from datetime import datetime
import pygame.mixer as mixer # pygameはTkinter版では常に使用
import glob # フォルダ内のファイルリスト取得に使用

# --- pygameミキサーを初期化 (スクリプトの先頭で) ---
try:
    mixer.init()
    PLAYBACK_METHOD = 'pygame'
    print("音声再生にPygame (Tkinter向け) を使用します。")
except Exception as e:
    PLAYBACK_METHOD = 'none' # 初期化失敗時
    print(f"Pygameミキサーの初期化に失敗しました: {e}. 音声は再生されません。")


# --- 関数定義 ---

MAX_CHARS_PER_AUDIO = 300
AUDIO_DIR_NAME = "generated_audio" # 音声ファイルを保存するルートフォルダ名

def play_mp3_threaded(filepath):
    """MP3ファイルを別スレッドで再生する (Tkinter向け、Pygame使用)"""
    if PLAYBACK_METHOD == 'pygame':
        try:
            sound = mixer.Sound(filepath)
            sound.play()
            while mixer.get_busy(): # 再生が終了するまで待機
                threading.Event().wait(0.1) # 0.1秒待つ
        except Exception as e:
            print(f"Pygame再生エラー: {e}")
    else:
        print(f"Tkinter環境で音声再生が有効ではありません。ファイル: {filepath}")

def create_and_play_audio():
    """音声を作成して再生する一連の処理を行う関数"""
    original_text = text_entry.get("1.0", tk.END).strip()
    lang = lang_combobox.get()

    if '(' in lang and ')' in lang:
        lang_code = lang.split('(')[1][:-1]
    else:
        lang_code = lang

    if not original_text:
        status_label.config(text="テキストが入力されていません", fg="red")
        set_buttons_state(tk.NORMAL)
        return

    set_buttons_state(tk.DISABLED)
    status_label.config(text="テキストを分割中...", fg="blue")
    root.update_idletasks()

    try:
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

        if not final_segments:
            status_label.config(text="分割可能なテキストが見つかりません", fg="red")
            set_buttons_state(tk.NORMAL)
            return

        status_label.config(text=f"テキストを {len(final_segments)} 個のセグメントに分割しました。", fg="green")
        root.update_idletasks()
        
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
            play_mp3_threaded(audio_file)
        
        status_label.config(text=f"すべての音声ファイルの再生が完了しました。フォルダ: '{full_audio_path}'", fg="green")
    
    except Exception as e:
        status_label.config(text=f"エラー: {e}", fg="red")
    
    finally:
        set_buttons_state(tk.NORMAL)


def select_and_play_audio_folder():
    """フォルダを選択し、その中のMP3ファイルを連続再生する関数"""
    folder_path = filedialog.askdirectory(initialdir=AUDIO_DIR_NAME, title="再生する音声フォルダを選択してください")

    if not folder_path:
        status_label.config(text="フォルダが選択されていません", fg="orange")
        return

    set_buttons_state(tk.DISABLED)
    status_label.config(text=f"フォルダ '{os.path.basename(folder_path)}' を読み込み中...", fg="blue")
    root.update_idletasks()

    try:
        # フォルダ内のMP3ファイルをリストアップし、ソートする
        mp3_files = sorted(glob.glob(os.path.join(folder_path, "*.mp3")))

        if not mp3_files:
            status_label.config(text="選択されたフォルダにMP3ファイルが見つかりません", fg="red")
            return

        status_label.config(text=f"{len(mp3_files)} 個のMP3ファイルを再生します...", fg="green")
        root.update_idletasks()

        for i, audio_file in enumerate(mp3_files):
            status_label.config(text=f"再生中: {i+1}/{len(mp3_files)} - '{os.path.basename(audio_file)}'", fg="purple")
            root.update_idletasks()
            play_mp3_threaded(audio_file)
        
        status_label.config(text=f"すべての音声ファイルの再生が完了しました。フォルダ: '{os.path.basename(folder_path)}'", fg="green")

    except Exception as e:
        status_label.config(text=f"エラー: {e}", fg="red")
    finally:
        set_buttons_state(tk.NORMAL)


def start_audio_thread():
    """UIが固まらないように、別スレッドで音声作成処理を開始する"""
    thread = threading.Thread(target=create_and_play_audio)
    thread.daemon = True
    thread.start()

def start_folder_playback_thread():
    """UIが固まらないように、別スレッドでフォルダ再生処理を開始する"""
    thread = threading.Thread(target=select_and_play_audio_folder)
    thread.daemon = True
    thread.start()

def paste_text():
    """クリップボードからテキストを貼り付ける"""
    try:
        text = root.clipboard_get()
        text_entry.delete("1.0", tk.END)
        text_entry.insert(tk.END, text)
    except tk.TclError:
        status_label.config(text="クリップボードが空です", fg="orange")

def clear_text():
    """テキスト入力欄とステータス表示をクリアする"""
    text_entry.delete("1.0", tk.END)
    status_label.config(text="")
    # 音声ファイルが保存されるルートフォルダがあれば作成 (初回起動時など)
    os.makedirs(AUDIO_DIR_NAME, exist_ok=True)


def set_buttons_state(state):
    """すべてのボタンの状態を一括で変更する関数"""
    create_button.config(state=state)
    paste_button.config(state=state)
    clear_button.config(state=state)
    lang_combobox.config(state=state)
    play_folder_button.config(state=state) # 新しいボタンも制御


# --- Tkinterウィンドウのセットアップ ---
root = tk.Tk()
root.title("LongTalker App")
root.geometry("450x450") # ウィンドウサイズを少し大きくして新しいボタンのスペースを確保

# --- ウィジェットの作成と配置 ---

main_frame = tk.Frame(root, padx=10, pady=10)
main_frame.pack(fill=tk.BOTH, expand=True)

text_entry = tk.Text(main_frame, height=10, width=50, font=("IPAexGothic", 10))
text_entry.pack(pady=(0, 10), fill=tk.BOTH, expand=True)

button_frame = tk.Frame(main_frame)
button_frame.pack(fill=tk.X)

lang_label = tk.Label(button_frame, text="言語:")
lang_label.pack(side=tk.LEFT, padx=(0, 5))
languages = ['日本語 (ja)', '英語 (en)', '韓国語 (ko)', '中国語 (zh-CN)', 'フランス語 (fr)', 'ドイツ語 (de)', 'スペイン語 (es)']
lang_combobox = ttk.Combobox(button_frame, values=languages, width=15)
lang_combobox.set('日本語 (ja)')
lang_combobox.pack(side=tk.LEFT, padx=(0, 20))

paste_button = tk.Button(button_frame, text="貼り付け", command=paste_text)
paste_button.pack(side=tk.LEFT, padx=5)

clear_button = tk.Button(button_frame, text="クリア", command=clear_text)
clear_button.pack(side=tk.LEFT)

# メインの実行ボタン
create_button = tk.Button(main_frame, text="音声ファイルを作成して再生", command=start_audio_thread, font=("IPAexGothic", 11, "bold"), bg="#4CAF50", fg="white")
create_button.pack(pady=(10,5), fill=tk.X) # padyを調整

# ★★★ 新しい再生ボタン ★★★
play_folder_button = tk.Button(main_frame, text="フォルダから再生", command=start_folder_playback_thread, font=("IPAexGothic", 11, "bold"), bg="#2196F3", fg="white") # 青系の色に
play_folder_button.pack(pady=(5,10), fill=tk.X) # padyを調整

status_label = tk.Label(main_frame, text="ここにステータスが表示されます", anchor="w", justify=tk.LEFT)
status_label.pack(pady=(5, 0), fill=tk.X)

# --- アプリ起動時にAUDIO_DIR_NAMEフォルダがなければ作成 ---
if not os.path.exists(AUDIO_DIR_NAME):
    os.makedirs(AUDIO_DIR_NAME)


# --- ウィンドウのメインループ ---
root.mainloop()
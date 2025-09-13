[app]
title = LongTalker
package.name = longtalker
package.domain = org.example
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,gif,txt,mp3
version = 0.1
requirements = python3,kivy==2.1.0,pillow,gtts,playsound
orientation = portrait

[android]
android.permissions = INTERNET,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE
android.archs = arm64-v8a
android.minapi = 21
android.target_sdk_version = 33
fullscreen = 0
android.accept_sdk_license = True
android.enable_androidx = True

# ホストPythonのビルド引数を明示的に指定 (_ctypes問題を回避)
# この設定は、Pythonのコア依存関係の問題が解決されているBuildozerの最新バージョンでは不要な場合もありますが、念のため残します。
p4a.python_host_build_args = --with-system-ffi --enable-shared

[buildozer]
log_level = 2

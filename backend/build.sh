#!/bin/bash
pip install -r requirements.txt
python manage.py collectstatic --noinput
# Download FFmpeg static binary
if [ ! -f ./ffmpeg ]; then
    curl -L https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz | tar xJ
    mv ffmpeg-*-static/ffmpeg ./ffmpeg
    chmod +x ./ffmpeg
fi
# Verify FFmpeg
./ffmpeg -version || { echo "FFmpeg download failed"; exit 1; }
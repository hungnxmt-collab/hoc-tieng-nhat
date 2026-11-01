#!/bin/bash
# chép lời: in -> out/<name>.txt (dòng "start -- end: text")
M=/home/claude/asr/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17
B=/home/claude/asr/sherpa-onnx-v2.0.1-linux-x64-shared
mkdir -p /home/claude/asr/out/try /home/claude/asr/out/vocab
for f in /home/claude/raw/audio/out/try/*.mp3 /home/claude/raw/audio/out/vocab/*.mp3; do
  d=$(basename $(dirname $f)); n=$(basename $f .mp3); o=/home/claude/asr/out/$d/$n.txt
  [ -s $o ] && continue
  ffmpeg -v error -y -i $f -ar 16000 -ac 1 /tmp/claude-0/asr_in.wav
  LD_LIBRARY_PATH=$B/lib $B/bin/sherpa-onnx-vad-with-offline-asr --silero-vad-model=/home/claude/asr/silero_vad.onnx --silero-vad-min-silence-duration=0.3 \
    --sense-voice-model=$M/model.int8.onnx --tokens=$M/tokens.txt --sense-voice-language=ja --sense-voice-use-itn=1 --num-threads=2 /tmp/claude-0/asr_in.wav 2>/dev/null \
    | grep -E '^[0-9.]+ -- [0-9.]+:' > $o.tmp && mv $o.tmp $o
  echo "$d/$n $(wc -l < $o)"
done
echo ALLDONE

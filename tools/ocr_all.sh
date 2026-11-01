#!/bin/bash
# OCR từng trang: render 300dpi xám -> tesseract jpn (txt + tsv)
F="$1"; OUT="$2"; mkdir -p "$OUT"
N=$(pdfinfo "$F" 2>/dev/null | awk '/Pages/{print $2}')
doit(){ p=$1; F="$2"; OUT="$3"; b=$(printf "%s/p%03d" "$OUT" $p); [ -s "$b.tsv" ] && return
  pdftoppm -r 300 -gray -f $p -l $p -png "$F" "$b" 2>/dev/null; img=$(ls $b-*.png | head -1); mv "$img" "$b.png"
  tesseract "$b.png" "$b" -l jpn --psm 6 txt tsv >/dev/null 2>&1; }
export -f doit
seq 1 $N | xargs -P 2 -I{} bash -c 'doit {} "$0" "$1"' "$F" "$OUT"
echo DONE

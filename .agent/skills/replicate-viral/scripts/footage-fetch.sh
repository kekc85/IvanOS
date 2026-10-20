#!/usr/bin/env bash
# footage-fetch.sh — добытчик футажа для replicate-viral (Фаза 3a «Сырьё»)
# Источники (приоритет): 1) официальные демо тула (YouTube/лендинг/X)
#                        2) публичные галереи генераций
#                        3) сторонние туториалы (fallback, короткие куски + трансформация)
#
# Режимы:
#   search <запрос>            — кандидаты с YouTube (TSV: канал · название · длительность · просмотры · URL)
#   get <URL> <tool-slug> [пометка-источника]
#                              — скачать 1080p+ в библиотеку + записать provenance
#   page <URL-лендинга> <tool-slug>
#                              — выдрать прямые <video src> mp4 с лендинга и скачать
#   index                      — перестроить _INDEX.md библиотеки
#
# Библиотека: ~/.business/growth/assets/footage/<tool-slug>/raw/*.mp4 + provenance.md
set -euo pipefail

LIB="$HOME/.business/growth/assets/footage"
mkdir -p "$LIB"

cmd="${1:-}"; shift || true

case "$cmd" in
  search)
    q="$*"
    [ -z "$q" ] && { echo "usage: footage-fetch.sh search <запрос>"; exit 1; }
    # 12 кандидатов; агент курирует: официальный канал тула > туториал по просмотрам
    yt-dlp "ytsearch12:${q}" --flat-playlist \
      --print "%(channel)s\t%(title)s\t%(duration)s\t%(view_count)s\thttps://www.youtube.com/watch?v=%(id)s" 2>/dev/null
    ;;

  get)
    url="${1:?usage: get <URL> <tool-slug> [пометка]}"; slug="${2:?tool-slug обязателен}"; note="${3:-}"
    dir="$LIB/$slug/raw"; mkdir -p "$dir"
    # 1080p+ если есть, иначе лучшее; mp4
    yt-dlp -f "bv*[height>=1080]+ba/bv*+ba/b" --merge-output-format mp4 \
      --restrict-filenames -o "$dir/%(id)s_%(title).60s.%(ext)s" "$url"
    f=$(ls -t "$dir" | head -1)
    {
      echo "## $f"
      echo "- url: $url"
      echo "- канал: $(yt-dlp --print '%(channel)s · %(title)s · %(upload_date)s' --skip-download "$url" 2>/dev/null || echo '?')"
      echo "- скачано: $(date +%Y-%m-%d)"
      [ -n "$note" ] && echo "- источник-тип: $note"
      echo ""
    } >> "$LIB/$slug/provenance.md"
    echo "OK → $dir/$f"
    ;;

  page)
    url="${1:?usage: page <URL> <tool-slug>}"; slug="${2:?tool-slug обязателен}"
    dir="$LIB/$slug/raw"; mkdir -p "$dir"
    # прямые mp4/webm из html лендинга (src= и source src=).
    # Матчим ПОЛНЫЙ URL, где расширение = КОНЕЦ path (не середина типа .../video.mp4/thumb.jpg):
    # после .mp4/.webm допустим только ? (query) или конец строки — НЕ слеш.
    html=$(curl -sL --max-time 30 "$url")
    # 1) кандидаты: URL, обрывающийся на .mp4/.webm (+опц. ?query)
    # 2) отбросить ловушку «.../video.mp4/ik-thumbnail.jpg»: если в HTML за этим
    #    совпадением стоит '/', значит расширение в СЕРЕДИНЕ пути — это не файл.
    urls=$(echo "$html" \
      | grep -oE '(https?:)?//[^"'"'"' \\]+\.(mp4|webm)(/|\?[^"'"'"' \\]*)?' \
      | grep -vE '\.(mp4|webm)/' \
      | grep -E '\.(mp4|webm)(\?|$)' \
      | sort -u)
    found=0; saved=0
    for v in $urls; do
      found=$((found+1))
      [ "${v:0:2}" = "//" ] && v="https:$v"
      # имя файла из path (без query), при коллизии — счётчик
      base="$(basename "${v%%\?*}")"
      out="$dir/$base"; n=1
      while [ -e "$out" ]; do
        out="$dir/${base%.*}_${n}.${base##*.}"; n=$((n+1))
      done
      echo "↓ $v"
      if ! curl -sL --max-time 120 -o "$out" "$v"; then
        echo "  FAIL download $v"; rm -f "$out"; continue
      fi
      # проверка типа: реальный ли это видео-файл (не HTML/JPG/мусор)
      ftype="$(file -b --mime-type "$out" 2>/dev/null || echo '?')"
      if ! printf '%s' "$ftype" | grep -qiE 'video/|application/octet-stream'; then
        echo "  SKIP (не видео: $ftype) $v"; rm -f "$out"; continue
      fi
      # provenance пишем ТОЛЬКО при успехе
      saved=$((saved+1))
      {
        echo "## $(basename "$out")"
        echo "- url: $v (лендинг: $url)"
        echo "- mime: $ftype"
        echo "- скачано: $(date +%Y-%m-%d)"
        echo ""
      } >> "$LIB/$slug/provenance.md"
      echo "  OK → $out ($ftype)"
    done
    if [ "$found" -eq 0 ]; then
      echo "Ничего не найдено: на странице нет прямых .mp4/.webm ссылок"
    else
      echo "Итог: найдено URL=$found, сохранено реальных видео=$saved"
    fi
    ls -la "$dir" 2>/dev/null || true
    ;;

  index)
    {
      echo "# Библиотека футажа (добытчик footage-fetch.sh)"
      echo ""
      for d in "$LIB"/*/; do
        [ -d "$d/raw" ] || continue
        s=$(basename "$d")
        n=$(ls "$d/raw" 2>/dev/null | wc -l | tr -d ' ')
        echo "## $s — $n файлов"
        ls "$d/raw" 2>/dev/null | sed 's/^/- /'
        echo ""
      done
    } > "$LIB/_INDEX.md"
    echo "OK → $LIB/_INDEX.md"
    ;;

  *)
    grep '^#' "$0" | head -16
    exit 1
    ;;
esac

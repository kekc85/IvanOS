/* Командная строка Cmd+K: одна строка русским языком превращается в событие
   недели или в запись бэклога.

     «завтра 15:00 монтаж курса 2ч #контент p1»

   Файл делится на два слоя, и это принципиально:

   1. ПАРСЕР - чистая функция parse(str, opts). Никакого DOM, никакой сети,
      никакого Date.now() внутри разбора: «сегодня» берётся из opts.today.
      Поэтому его гоняют самотесты (внизу файла, запуск по ?command-test) и
      он же разбирает строку заново перед записью - уже против СВЕЖИХ треков.
   2. UI - оверлей, живой предпросмотр, мобильная кнопка «+», запись.

   Протокол записи (главный блокер прошлой критики: tab-week.js пишет своим
   fetch со своим rev, поэтому кэш App.rev протухает после первой правки в
   сетке): свежий App.api.get('/api/data') НЕПОСРЕДСТВЕННО перед записью ->
   мутация только что прочитанного документа -> App.api.post. Конфликт 409 -
   один автоповтор с новым чтением, второй отказ - честный тост, а не тишина.

   Наружу торчит только window.CommandBar (open/close/parse/version) - им
   пользуются обработчики и самотесты, внутренние помощники закрыты IIFE.
   Стили свои, все классы с префиксом cb-, чужие файлы не трогаем.

   Известное ограничение (осознанное, чужой модуль не чиним): открытая вкладка
   «Неделя» держит свою копию документа и про новую задачу узнает при
   следующем своём действии - через баннер конфликта либо после обновления. */
(function(){
'use strict';

var ROOT = (typeof window !== 'undefined') ? window
         : (typeof globalThis !== 'undefined' ? globalThis : this);
var HAS_DOM = (typeof document !== 'undefined') && !!document.createElement;

/* ==========================================================================
   1. ЧИСТЫЙ СЛОЙ: даты, длительности, треки, парсер
   ========================================================================== */

var DEF_DUR = 30;                    // «Нет длительности - est 30 по умолчанию»
var DUR_MIN = 5, DUR_MAX = 1440;
var TITLE_MAX = 500;                 // ровно столько держат схемы сервера V_EVENT и V_BACKLOG
var DAYS_MAX = 365;                  // «через 999 дней» - это опечатка, а не срок
var SOMEDAY_TTL = 30;                // дней жизни отложенной записи, как в rituals/decide.py
var DOW_SHORT = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'];   // 0 = понедельник
var TOD = {утро: 540, день: 840, вечер: 1020};                 // 09:00 / 14:00 / 17:00

function pad2(n){ return (n < 10 ? '0' : '') + n; }
function isDateStr(s){ return /^\d{4}-\d{2}-\d{2}$/.test(String(s == null ? '' : s)); }
function toIso(y, m, d){ return y + '-' + pad2(m) + '-' + pad2(d); }
function partsOf(k){ var a = String(k).split('-'); return {y: +a[0], m: +a[1], d: +a[2]}; }
function dateObj(k){ var p = partsOf(k); return new Date(p.y, p.m - 1, p.d); }
function isoOf(dt){ return toIso(dt.getFullYear(), dt.getMonth() + 1, dt.getDate()); }
function addDaysIso(k, n){ var dt = dateObj(k); dt.setDate(dt.getDate() + n); return isoOf(dt); }
function dowIso(k){ return (dateObj(k).getDay() + 6) % 7; }       // понедельник = 0
function daysInMonth(y, m){ return new Date(y, m, 0).getDate(); }
function todayIso(){ return isoOf(new Date()); }
function shortDate(k){ return isDateStr(k) ? k.slice(8, 10) + '.' + k.slice(5, 7) : String(k || ''); }
function hhmm(m){ return pad2(Math.floor(m / 60)) + ':' + pad2(m % 60); }
function clampDur(m){
  var v = Math.round(+m || 0);
  if(!isFinite(v) || v <= 0) return DEF_DUR;
  return Math.min(DUR_MAX, Math.max(DUR_MIN, v));
}

/* Ближайший БУДУЩИЙ день недели. Сегодняшний день недели значит «через
   неделю»: «чт» в четверг - это не сегодня, иначе слово было бы «сегодня». */
function nextDow(today, dow){
  var delta = (dow - dowIso(today) + 7) % 7;
  return addDaysIso(today, delta === 0 ? 7 : delta);
}

/* Число.месяц[.год]. Год не назвали и дата уже прошла - значит следующий год
   (05.01 в конце августа - это январь следующего). Невалидная пара -> null,
   строка остаётся в названии, а не превращается в кривую дату. */
function numDate(today, d, m, y){
  if(!(m >= 1 && m <= 12)) return null;
  var year = (y == null) ? partsOf(today).y : (y < 100 ? 2000 + y : y);
  if(!(d >= 1 && d <= daysInMonth(year, m))) return null;
  var res = toIso(year, m, d);
  if(y == null && res < today){
    year += 1;
    if(!(d <= daysInMonth(year, m))) return null;
    res = toIso(year, m, d);
  }
  return res;
}

var DOW_WORDS = [
  [/^(пн|понедельник[ауе]?)$/i, 0],
  [/^(вт|вторник[ауе]?)$/i, 1],
  [/^(ср|сред[ауы])$/i, 2],
  [/^(чт|четверг[ауе]?)$/i, 3],
  [/^(пт|пятниц[ауы])$/i, 4],
  [/^(сб|суббот[ауы])$/i, 5],
  [/^(вс|воскресен[ьи][еяю])$/i, 6]
];
function dowOfWord(w){
  for(var i = 0; i < DOW_WORDS.length; i++) if(DOW_WORDS[i][0].test(w)) return DOW_WORDS[i][1];
  return -1;
}

/* Строку держим в «дополненном» виде: пробел в начале, пробел в конце, внутри
   одиночные пробелы. Тогда любой токен окружён пробелами и шаблон пишется как
   « слово» с заглядыванием на пробел справа - никаких \b, которые в JS не
   дружат с кириллицей. Вырезаем ведущий пробел вместе с токеном, замыкающий
   остаётся разделителем для соседа. */
function normalize(str){
  var t = String(str == null ? '' : str).replace(/\s+/g, ' ').trim();
  return t ? ' ' + t + ' ' : ' ';
}
function cut(st, from, to){ st.s = st.s.slice(0, from) + st.s.slice(to); }

var RE_SOMEDAY  = / (?:когда-нибудь|когда нибудь|когданибудь|someday)(?= )/i;
var RE_PRIO     = / [pр]([1-4])(?= )/i;
var RE_TRACK    = / #([^\s#]+)(?= )/;
var RE_HOURS    = / (\d{1,3}(?:[.,]\d{1,2})?) ?(?:часов|часа|час|ч|hrs|hr|h)\.?(?= )/i;
var RE_MINS     = / (\d{1,4}) ?(?:минуты|минут|мин|м|min|m)\.?(?= )/i;
var RE_DATE_NUM = / (\d{1,2})[.\/](\d{1,2})(?:[.\/](\d{2,4}))?(?= )/g;
var RE_WEEK_THR = / через неделю(?= )/i;
var RE_DAYS_THR = / через (\d{1,3}) (?:дней|дня|день|дн)\.?(?= )/i;
var RE_REL      = / (послезавтра|завтра|сегодня)(?= )/i;
var RE_DOW      = / (?:в |во )?(пн|вт|ср|чт|пт|сб|вс|понедельник[ауе]?|вторник[ауе]?|сред[ауы]|четверг[ауе]?|пятниц[ауы]|суббот[ауы]|воскресен[ьи][еяю])(?= )/i;
var RE_TIME_C   = / (?:в |во )?([01]?\d|2[0-3])[:.]([0-5]\d)(?= )/;
var RE_TIME_SP  = / (?:в |во )?([01]?\d|2[0-3]) ([0-5]\d)(?= )/;
var RE_TIME_H   = / в ([01]?\d|2[0-3])(?= )/i;
var RE_TOD      = / (утром|утро|дн[ёе]м|вечером|вечер)(?= )/i;

function labelOf(track){
  return (track && typeof track === 'object' && typeof track.label === 'string') ? track.label : '';
}
function trackKeys(tracks){
  return (tracks && typeof tracks === 'object') ? Object.keys(tracks) : [];
}
function defaultTrackOf(tracks, prefer){
  var keys = trackKeys(tracks);
  if(prefer && keys.indexOf(prefer) >= 0) return prefer;
  return keys.length ? keys[0] : '';
}
/* «#контент» матчим по подстроке против кода И подписи трека. Порядок проверок
   от точного к вольному, внутри - порядок ключей документа, поэтому результат
   детерминирован. Совпадения нет - трек по умолчанию, а предпросмотр честно
   пишет «(по умолчанию)», чтобы задача не уехала молча не в тот трек. */
function resolveTrack(word, tracks, fallback){
  var w = String(word == null ? '' : word).toLowerCase().replace(/[.,;:!?]+$/, '');
  var keys = trackKeys(tracks), i, code, lbl;
  if(!w || !keys.length) return {code: fallback, matched: false};
  for(i = 0; i < keys.length; i++) if(keys[i].toLowerCase() === w) return {code: keys[i], matched: true};
  for(i = 0; i < keys.length; i++) if(labelOf(tracks[keys[i]]).toLowerCase() === w) return {code: keys[i], matched: true};
  for(i = 0; i < keys.length; i++){
    code = keys[i].toLowerCase(); lbl = labelOf(tracks[keys[i]]).toLowerCase();
    if(code.indexOf(w) === 0 || lbl.indexOf(w) === 0) return {code: keys[i], matched: true};
  }
  for(i = 0; i < keys.length; i++){
    code = keys[i].toLowerCase(); lbl = labelOf(tracks[keys[i]]).toLowerCase();
    if(code.indexOf(w) >= 0 || lbl.indexOf(w) >= 0) return {code: keys[i], matched: true};
  }
  return {code: fallback, matched: false};
}
function trackLabel(code, tracks){
  if(!code) return '';
  var t = tracks && tracks[code];
  return labelOf(t) || code;
}

/* --------------------------------------------------------------------------
   parse(str, opts) -> {
     title, date, start, dur, track, priority, target, status?,
     dateGiven, timeGiven, durGiven, trackGiven, trackMatched, someday, raw
   }
   opts = {today: 'ГГГГ-ММ-ДД', tracks: {код: {label}}, defaultTrack: 'код'}
   Чистая и детерминированная: при заданном opts.today результат зависит только
   от строки. Без opts.today берётся текущая дата (единственная нечистота, и
   она вынесена в самый край - самотесты дату задают явно).
   -------------------------------------------------------------------------- */
function parse(str, opts){
  opts = opts || {};
  var tracks = (opts.tracks && typeof opts.tracks === 'object') ? opts.tracks : {};
  var today = isDateStr(opts.today) ? opts.today : todayIso();
  var fallbackTrack = defaultTrackOf(tracks, opts.defaultTrack);
  var st = {s: normalize(str)};
  var m, hrs = null, mns = null;

  var out = {
    title: '', date: today, start: null, dur: DEF_DUR,
    track: fallbackTrack, priority: null, target: 'backlog',
    dateGiven: false, timeGiven: false, durGiven: false,
    trackGiven: false, trackMatched: false, someday: false,
    titleCut: false, titleLen: 0, daysTooBig: 0, ttl: null,
    raw: String(str == null ? '' : str)
  };

  /* --- 1. someday: уводит задачу в бэклог, даже если время назвали --- */
  m = RE_SOMEDAY.exec(st.s);
  if(m){ out.someday = true; cut(st, m.index, m.index + m[0].length); }

  /* --- 2. приоритет p1..p4 (p1 - высший) --- */
  m = RE_PRIO.exec(st.s);
  if(m){ out.priority = +m[1]; cut(st, m.index, m.index + m[0].length); }

  /* --- 3. трек #слово --- */
  m = RE_TRACK.exec(st.s);
  if(m){
    var r = resolveTrack(m[1], tracks, fallbackTrack);
    out.track = r.code; out.trackGiven = true; out.trackMatched = r.matched;
    cut(st, m.index, m.index + m[0].length);
  }

  /* --- 4. длительность: часы и минуты складываются («1ч 30м» = 90) ---
     «в 15 часов» - это не два часа работы, а время: если перед числом стоит
     отдельное «в», забираем всю связку как время суток. */
  m = RE_HOURS.exec(st.s);
  if(m){
    var beforeH = st.s.slice(0, m.index);
    if(/(^| )в$/i.test(beforeH)){
      var hv = parseInt(m[1], 10);
      if(hv >= 0 && hv <= 23 && String(m[1]).indexOf('.') < 0 && String(m[1]).indexOf(',') < 0){
        out.start = hhmm(hv * 60); out.timeGiven = true;
        cut(st, beforeH.lastIndexOf(' ' + 'в'), m.index + m[0].length);
      }
    }
    if(!out.timeGiven){
      hrs = parseFloat(String(m[1]).replace(',', '.'));
      cut(st, m.index, m.index + m[0].length);
    }
  }
  m = RE_MINS.exec(st.s);
  if(m){ mns = parseInt(m[1], 10); cut(st, m.index, m.index + m[0].length); }
  if(hrs != null || mns != null){
    out.dur = clampDur((hrs || 0) * 60 + (mns || 0));
    out.durGiven = true;
  }

  /* --- 5. дата. Порядок: число.месяц -> через N -> завтра -> день недели.
     Числовую форму перебираем ВСЕ вхождения: «15.30 звонок 28.08» не должно
     умирать на первом кандидате, который датой не является. */
  RE_DATE_NUM.lastIndex = 0;
  while(!out.dateGiven && (m = RE_DATE_NUM.exec(st.s))){
    var got = numDate(today, parseInt(m[1], 10), parseInt(m[2], 10), m[3] == null ? null : parseInt(m[3], 10));
    if(got){
      out.date = got; out.dateGiven = true;
      cut(st, m.index, m.index + m[0].length);
    }
  }
  if(!out.dateGiven){
    m = RE_WEEK_THR.exec(st.s);
    if(m){ out.date = addDaysIso(today, 7); out.dateGiven = true; cut(st, m.index, m.index + m[0].length); }
  }
  /* Потолок «через N дней». Без него «через 999 дней» уезжало в 2029 год, и
     задача пропадала из виду навсегда. Токен при этом НЕ вырезаем: он остаётся
     в названии на виду, а предпросмотр говорит, что срок не принят. */
  if(!out.dateGiven){
    m = RE_DAYS_THR.exec(st.s);
    if(m){
      var nd = parseInt(m[1], 10);
      if(nd > DAYS_MAX){
        out.daysTooBig = nd;
      }else{
        out.date = addDaysIso(today, nd); out.dateGiven = true; cut(st, m.index, m.index + m[0].length);
      }
    }
  }
  if(!out.dateGiven){
    m = RE_REL.exec(st.s);
    if(m){
      var w = m[1].toLowerCase();
      out.date = addDaysIso(today, w === 'завтра' ? 1 : (w === 'послезавтра' ? 2 : 0));
      out.dateGiven = true;
      cut(st, m.index, m.index + m[0].length);
    }
  }
  if(!out.dateGiven){
    m = RE_DOW.exec(st.s);
    if(m){
      var dw = dowOfWord(m[1]);
      if(dw >= 0){ out.date = nextDow(today, dw); out.dateGiven = true; cut(st, m.index, m.index + m[0].length); }
    }
  }

  /* --- 6. время. Нет времени - задача уходит в бэклог, не в сетку. --- */
  if(!out.timeGiven){
    m = RE_TIME_C.exec(st.s);
    if(m){ out.start = hhmm(parseInt(m[1], 10) * 60 + parseInt(m[2], 10)); out.timeGiven = true; cut(st, m.index, m.index + m[0].length); }
  }
  if(!out.timeGiven){
    m = RE_TIME_SP.exec(st.s);
    if(m){ out.start = hhmm(parseInt(m[1], 10) * 60 + parseInt(m[2], 10)); out.timeGiven = true; cut(st, m.index, m.index + m[0].length); }
  }
  if(!out.timeGiven){
    m = RE_TIME_H.exec(st.s);
    if(m){ out.start = hhmm(parseInt(m[1], 10) * 60); out.timeGiven = true; cut(st, m.index, m.index + m[0].length); }
  }
  if(!out.timeGiven){
    m = RE_TOD.exec(st.s);
    if(m){
      var t = m[1].toLowerCase();
      var mins = /^утр/.test(t) ? TOD.утро : (/^дн/.test(t) ? TOD.день : TOD.вечер);
      out.start = hhmm(mins); out.timeGiven = true;
      cut(st, m.index, m.index + m[0].length);
    }
  }

  /* --- 7. всё нераспознанное = название ---
     Режем по лимиту схемы ЗДЕСЬ, а не на сервере: иначе длинная диктовка
     возвращалась сырой 400-кой «длиннее 500 символов», и запись терялась. */
  out.title = st.s.replace(/\s+/g, ' ').trim();
  out.titleLen = out.title.length;
  if(out.titleLen > TITLE_MAX){
    out.titleCut = true;
    out.title = out.title.slice(0, TITLE_MAX).replace(/\s+$/, '');
  }

  /* Someday сильнее времени: «когда-нибудь» - это явное «не ставь в сетку».
     TTL обязателен: без него отложенная запись прячется за счётчиком бэклога и
     тонет навсегда. Назвали срок - он и есть TTL, не назвали - +30 дней, ровно
     как у вечернего ритуала decide.py и вкладки «Неделя». */
  if(out.someday){
    out.target = 'backlog';
    out.status = 'someday';
    out.ttl = out.dateGiven ? out.date : addDaysIso(today, SOMEDAY_TTL);
  }else{
    out.target = out.start ? 'event' : 'backlog';
  }
  return out;
}

/* Человеческая расшифровка разбора для предпросмотра и тоста.
   «Чт 28.08 · 15:00 · 120 мин · Контент · p1» */
function describe(p, tracks){
  var bits = [];
  if(p.target === 'event'){
    bits.push(DOW_SHORT[dowIso(p.date)] + ' ' + shortDate(p.date));
    bits.push(p.start);
  }else{
    bits.push(p.someday ? 'Бэклог, когда-нибудь' : 'Бэклог');
    if(p.dateGiven) bits.push('срок ' + DOW_SHORT[dowIso(p.date)] + ' ' + shortDate(p.date));
    if(p.someday && p.ttl) bits.push('всплывёт ' + shortDate(p.ttl));
  }
  bits.push(p.dur + ' мин' + (p.durGiven ? '' : ' по умолчанию'));
  var lbl = trackLabel(p.track, tracks);
  if(lbl) bits.push(lbl + (p.trackMatched || !p.track ? '' : ' по умолчанию'));
  if(p.priority) bits.push('p' + p.priority);
  return bits.join(' · ');
}

/* ==========================================================================
   2. UI: оверлей, живой предпросмотр, мобильная кнопка, запись
   ========================================================================== */

var ESCMAP = {'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;', '`': '&#96;'};
function esc(v){ return String(v == null ? '' : v).replace(/[&<>"'`]/g, function(c){ return ESCMAP[c]; }); }
function uid(p){ return p + Date.now().toString(36) + Math.random().toString(36).slice(2, 5); }

var EL = {ov: null, box: null, input: null, prev: null, fab: null, toast: null};
var TRACKS = {};                 // кэш треков для предпросмотра
var tracksAt = 0;                // когда обновляли (не чаще раза в 5 секунд)
var busy = false;                // запись идёт - второй Enter не дублирует задачу
var toastTimer = null;

var CSS = [
'.cb-ov{position:fixed;inset:0;z-index:700;background:rgba(32,33,36,.42);display:flex;',
'  align-items:flex-start;justify-content:center;padding:9vh 16px 16px}',
'.cb-ov[hidden]{display:none}',
'.cb-box{width:min(680px,100%);background:#fff;border-radius:12px;overflow:hidden;',
'  box-shadow:0 12px 40px rgba(32,33,36,.36);font-family:inherit}',
'.cb-in{display:block;width:100%;border:0;border-bottom:1px solid var(--bd,#dadce0);',
'  padding:18px 20px;font:400 19px/1.3 inherit;font-family:inherit;color:var(--txt,#3c4043);outline:none}',
'.cb-in::placeholder{color:#9aa0a6}',
'.cb-prev{padding:14px 20px;font-size:14px;line-height:1.45;min-height:56px;background:#fbfcfd}',
'.cb-prev .cb-t{display:block;font-weight:600;color:var(--txt,#3c4043);font-size:15px;',
'  word-break:break-word;margin-bottom:3px}',
'.cb-prev .cb-m{display:block;color:var(--txt-dim,#70757a);font-size:13px}',
/* Все классы с префиксом cb-, включая модификаторы. Живая проверка поймала
   ровно это: модификатор назывался «ev», а .ev в app.css - блок события в
   сетке (position:absolute;left:2px;right:6px), и бейдж растянуло во весь
   экран поверх недели. Чужие файлы мы не правим, значит имена не делим. */
'.cb-prev .cb-badge{display:inline-block;margin-right:8px;padding:2px 8px;border-radius:10px;',
'  font-size:11px;font-weight:600;letter-spacing:.2px;vertical-align:1px}',
'.cb-prev .cb-badge.cb-ev{background:#e6f0fd;color:#1a5fbd}',
'.cb-prev .cb-badge.cb-bl{background:#f1f3f4;color:#5f6368}',
'.cb-prev .cb-warn{display:block;margin-top:6px;color:#c5221f;font-size:12px}',
'.cb-prev.cb-dim{color:var(--txt-dim,#70757a)}',
'.cb-hint{padding:10px 20px 14px;font-size:11px;line-height:1.6;color:#9aa0a6;',
'  border-top:1px solid var(--bd-soft,#e8eaed);background:#fbfcfd}',
'.cb-hint b{color:#70757a;font-weight:600}',
'.cb-fab{display:none;position:fixed;right:16px;bottom:calc(84px + env(safe-area-inset-bottom,0px));',
'  z-index:450;width:56px;height:56px;border-radius:50%;border:0;background:var(--blue,#1a73e8);',
'  color:#fff;font:300 32px/1 -apple-system,sans-serif;cursor:pointer;',
'  box-shadow:0 4px 14px rgba(26,115,232,.42);align-items:center;justify-content:center;padding:0 0 3px}',
'.cb-fab:active{background:#1557b0}',
'.cb-toast{position:fixed;left:50%;bottom:24px;transform:translateX(-50%) translateY(14px);',
'  z-index:9000;background:#202124;color:#fff;padding:12px 18px;border-radius:8px;font-size:13px;',
'  line-height:1.4;max-width:min(560px,92vw);box-shadow:0 4px 16px rgba(0,0,0,.3);',
'  opacity:0;pointer-events:none;transition:opacity .18s,transform .18s;white-space:pre-line}',
'.cb-toast.cb-on{opacity:1;transform:translateX(-50%)}',
'.cb-toast.cb-err{background:#c5221f}',
'@media (max-width:600px){',
'  .cb-fab{display:flex}',
'  .cb-ov{padding:6vh 10px 10px}',
'  .cb-in{font-size:17px;padding:15px 16px}',
'  .cb-prev{padding:12px 16px}',
'  .cb-hint{padding:9px 16px 12px}',
'}'
].join('\n');

function ensureDom(){
  if(EL.ov || !HAS_DOM) return;

  var style = document.createElement('style');
  style.id = 'cb-style';
  style.textContent = CSS;
  document.head.appendChild(style);

  var ov = document.createElement('div');
  ov.className = 'cb-ov';
  ov.id = 'cb-ov';
  ov.hidden = true;
  ov.innerHTML =
    '<div class="cb-box" role="dialog" aria-modal="true" aria-label="Командная строка">' +
      '<input id="cb-in" class="cb-in" type="text" autocomplete="off" autocorrect="off" ' +
             'autocapitalize="off" spellcheck="false" ' +
             'placeholder="завтра 15:00 монтаж курса 2ч #контент p1">' +
      '<div class="cb-prev cb-dim" id="cb-prev"></div>' +
      '<div class="cb-hint">' +
        '<b>Дата</b> сегодня · завтра · послезавтра · пн-вс · через 3 дня · 28.08 &nbsp; ' +
        '<b>Время</b> 15:00 · 15 30 · в 15 · утром · днём · вечером &nbsp; ' +
        '<b>Сколько</b> 2ч · 1.5ч · 90м · 30 мин &nbsp; ' +
        '<b>Трек</b> #контент &nbsp; <b>Важность</b> p1-p4 &nbsp; ' +
        '<b>Отложить</b> когда-нибудь &nbsp; Enter записывает, Esc закрывает' +
      '</div>' +
    '</div>';
  document.body.appendChild(ov);

  var fab = document.createElement('button');
  fab.className = 'cb-fab';
  fab.id = 'cb-fab';
  fab.type = 'button';
  fab.setAttribute('aria-label', 'Добавить задачу');
  fab.textContent = '+';
  document.body.appendChild(fab);

  var toast = document.createElement('div');
  toast.className = 'cb-toast';
  toast.id = 'cb-toast';
  document.body.appendChild(toast);

  EL.ov = ov;
  EL.box = ov.querySelector('.cb-box');
  EL.input = ov.querySelector('#cb-in');
  EL.prev = ov.querySelector('#cb-prev');
  EL.fab = fab;
  EL.toast = toast;

  EL.input.addEventListener('input', renderPreview);
  ov.addEventListener('mousedown', function(e){ if(e.target === ov) closeBar(); });
  fab.addEventListener('click', function(e){ e.preventDefault(); openBar(); });
}

function isOpen(){ return !!(EL.ov && !EL.ov.hidden); }

function parseOpts(){
  return {today: todayIso(), tracks: TRACKS, defaultTrack: defaultTrackOf(TRACKS)};
}

function renderPreview(){
  if(!EL.prev) return;
  var text = EL.input ? EL.input.value : '';
  if(!String(text).trim()){
    EL.prev.className = 'cb-prev cb-dim';
    EL.prev.textContent = 'Пиши как говоришь: «завтра 15:00 монтаж курса 2ч #контент p1». Без времени задача уйдёт в бэклог';
    return;
  }
  var p = parse(text, parseOpts());
  var badge = p.target === 'event'
    ? '<span class="cb-badge cb-ev">в сетку</span>'
    : '<span class="cb-badge cb-bl">в бэклог</span>';
  /* Предупреждения копим списком: строка может быть кривой сразу по двум осям
     («через 999 дней» плюс простыня на 600 символов). */
  var warn = [];
  if(!p.title) warn.push('Нечего записывать: допиши название задачи');
  if(p.titleCut) warn.push('Название длиннее ' + TITLE_MAX + ' символов (' + p.titleLen +
                           '): запишу первые ' + TITLE_MAX + ', хвост уйдёт');
  if(p.daysTooBig) warn.push('«через ' + p.daysTooBig + ' дней» - это больше ' + DAYS_MAX +
                             ' дней, срок не принят. Назови дату числом, например 28.08');
  EL.prev.className = 'cb-prev';
  EL.prev.innerHTML =
    '<span class="cb-t">' + (p.title ? esc(p.title) : '<span style="color:#9aa0a6">название пустое</span>') + '</span>' +
    '<span class="cb-m">' + badge + esc(describe(p, TRACKS)) + '</span>' +
    warn.map(function(w){ return '<span class="cb-warn">' + esc(w) + '</span>'; }).join('');
}

function toast(text, kind){
  if(!EL.toast) return;
  EL.toast.textContent = text;
  EL.toast.className = 'cb-toast cb-on' + (kind === 'err' ? ' cb-err' : '');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(function(){
    if(EL.toast) EL.toast.className = 'cb-toast' + (kind === 'err' ? ' cb-err' : '');
  }, kind === 'err' ? 8000 : 4000);
}

/* Треки нужны только для предпросмотра. Перед записью строка разбирается
   заново против свежепрочитанного документа, поэтому протухший кэш здесь
   максимум покажет не ту подпись, но в файл не запишет. */
function refreshTracks(){
  if(typeof App === 'undefined' || !App.api) return;
  var now = Date.now();
  if(now - tracksAt < 5000) return;
  tracksAt = now;
  App.api.get('/api/data').then(function(doc){
    if(doc && doc.tracks && typeof doc.tracks === 'object'){
      TRACKS = doc.tracks;
      if(isOpen()) renderPreview();
    }
  }).catch(function(){ /* сеть упала - предпросмотр покажет трек как есть */ });
}

function openBar(){
  ensureDom();
  if(!EL.ov) return;
  EL.ov.hidden = false;
  renderPreview();
  refreshTracks();
  try{ EL.input.focus(); EL.input.select(); }catch(e){}
}

function closeBar(){
  if(!EL.ov) return;
  EL.ov.hidden = true;
  try{ EL.input.blur(); }catch(e){}
}

function toggleBar(){ if(isOpen()) closeBar(); else openBar(); }

/* ---------- запись ---------- */

function makeEvent(p){
  var ev = {
    id: uid('e'), kind: 'active', title: p.title, date: p.date,
    start: p.start, dur: clampDur(p.dur), est: clampDur(p.dur)
  };
  if(p.track) ev.track = p.track;
  if(p.priority) ev.priority = p.priority;
  return ev;
}
function makeBacklog(p){
  var b = {id: uid('b'), title: p.title, est: clampDur(p.dur)};
  if(p.track) b.track = p.track;
  if(p.priority) b.priority = p.priority;
  if(p.dateGiven) b.due = p.date;
  if(p.someday){
    b.status = 'someday';
    if(isDateStr(p.ttl)) b.ttl = p.ttl;      // без TTL запись тонет за счётчиком бэклога навсегда
  }
  return b;
}

/* Одна попытка записи целиком: свежее чтение -> разбор против свежих треков ->
   мутация ТОГО ЖЕ документа -> запись. Между get и post ничего не ждём. */
function writeOnce(text){
  return App.api.get('/api/data').then(function(doc){
    if(!doc || typeof doc !== 'object') throw new Error('сервер вернул не документ');
    TRACKS = (doc.tracks && typeof doc.tracks === 'object') ? doc.tracks : {};
    tracksAt = Date.now();
    var p = parse(text, {today: todayIso(), tracks: doc.tracks, defaultTrack: defaultTrackOf(doc.tracks)});
    if(!p.title) throw new Error('нет названия');
    if(p.target === 'event'){
      if(!Array.isArray(doc.events)) doc.events = [];
      doc.events.push(makeEvent(p));
    }else{
      if(!Array.isArray(doc.backlog)) doc.backlog = [];
      doc.backlog.push(makeBacklog(p));
    }
    return App.api.post('/api/data', doc).then(function(){
      announceChange();                    // только после подтверждённой записи
      return p;
    });
  });
}

/* Контракт волны: открытая вкладка не должна жить на протухшей копии документа.
   Раньше тост говорил «Добавил», а «Неделя» узнавала о задаче только после
   перезагрузки - и первый же конфликт предлагал ей «Перезаписать», то есть
   затереть только что созданную запись. Теперь после КАЖДОЙ успешной записи
   кричим на window, слушатели вкладок перечитывают документ и берут свежий rev. */
function announceChange(){
  try{
    if(typeof ROOT.dispatchEvent !== 'function' || typeof ROOT.CustomEvent !== 'function') return;
    ROOT.dispatchEvent(new ROOT.CustomEvent('sprint:changed', {detail: {source: 'command'}}));
  }catch(e){ /* старый браузер: вкладки перечитают документ при следующем заходе */ }
}

/* Конфликт версий (документ успели изменить из вкладки «Неделя» или вечерним
   ритуалом) - один автоповтор с НОВЫМ чтением. Второй отказ не заминаем. */
function commit(text){
  return writeOnce(text).catch(function(err){
    if(!(err && err.conflict)) throw err;
    return writeOnce(text).catch(function(err2){
      if(err2 && err2.conflict) err2.twice = true;
      throw err2;
    });
  });
}

function submit(){
  if(busy) return;
  var text = EL.input ? EL.input.value : '';
  var draft = parse(text, parseOpts());
  if(!draft.title){
    toast(String(text).trim()
      ? 'Название пустое: «' + String(text).trim() + '» - это только дата и время. Допиши, что делаем'
      : 'Пустая строка: напиши задачу словами', 'err');
    return;
  }
  if(typeof App === 'undefined' || !App.api){
    toast('Оболочка приложения не загрузилась, записывать некуда', 'err');
    return;
  }
  busy = true;
  EL.input.disabled = true;
  commit(text).then(function(p){
    var where = p.target === 'event'
      ? DOW_SHORT[dowIso(p.date)] + ' ' + p.start + ' '
      : (p.someday && p.ttl ? 'в бэклог, всплывёт ' + shortDate(p.ttl) + ' ' : 'в бэклог ');
    toast('Добавил: ' + where + p.title +
      (p.titleCut ? '\nНазвание обрезал до ' + TITLE_MAX + ' символов (было ' + p.titleLen + ')' : '') +
      (p.daysTooBig ? '\nСрок «через ' + p.daysTooBig + ' дней» не принят: больше ' + DAYS_MAX + ' дней' : ''));
    EL.input.value = '';
    renderPreview();
  }).catch(function(err){
    if(err && err.twice){
      toast('Не записалось: план меняют в другом окне. Попробуй ещё раз', 'err');
    }else if(err && err.conflict){
      toast('Не записалось: план изменился под нами. Попробуй ещё раз', 'err');
    }else{
      toast('Не записалось: ' + ((err && err.message) || 'сервер не ответил') + '. Попробуй ещё раз', 'err');
    }
  }).then(function(){
    busy = false;
    if(EL.input){
      EL.input.disabled = false;
      try{ EL.input.focus(); }catch(e){}
    }
  });
}

/* ---------- клавиатура ----------
   Слушаем на фазе перехвата: пока строка открыта, Escape и Enter принадлежат
   ей, а не вкладке снизу (в tab-week.js на Escape висит закрытие панели и
   выход из фокус-режима). Cmd+K работает из любой вкладки. */
function onKey(e){
  var key = String(e.key || '').toLowerCase();
  if((e.metaKey || e.ctrlKey) && key === 'k'){
    e.preventDefault();
    e.stopPropagation();
    toggleBar();
    return;
  }
  if(!isOpen()) return;
  if(key === 'escape'){
    e.preventDefault();
    e.stopPropagation();
    closeBar();
    return;
  }
  if(key === 'enter'){
    e.preventDefault();
    e.stopPropagation();
    submit();
    return;
  }
  /* Cmd+Z в поле - это текстовая отмена, а не откат недельной сетки */
  if((e.metaKey || e.ctrlKey) && (key === 'z' || key === 'y')) e.stopPropagation();
}

function boot(){
  ensureDom();
  document.addEventListener('keydown', onKey, true);
}

if(HAS_DOM){
  if(document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();
}

ROOT.CommandBar = {
  version: '1.1',
  parse: parse,
  describe: describe,
  open: openBar,
  close: closeBar,
  DEF_DUR: DEF_DUR
};

/* ==========================================================================
   3. САМОТЕСТЫ ПАРСЕРА
   Работают только если в адресе есть `command-test` (или из node: подсунуть
   window.location.search = '?command-test'). Каждый кейс печатает PASS/FAIL.
   Дата «сегодня» задана явно - 2026-08-27, четверг, поэтому тесты вечные.
   ========================================================================== */

function testsRequested(){
  try{
    if(!ROOT || !ROOT.location) return false;
    var l = ROOT.location;
    var s = String(l.href || '') + String(l.search || '') + String(l.hash || '');
    return s.indexOf('command-test') >= 0;
  }catch(e){ return false; }
}

var T_TRACKS = {
  efir:    {label: 'Эфир',          color: '#e8453c'},
  dolg:    {label: 'Долг ученикам', color: '#f4913e'},
  operac:  {label: 'Операционка',   color: '#4285f4'},
  content: {label: 'Контент',       color: '#0f9d58'},
  lichnoe: {label: 'Суды и личное', color: '#8e5fd9'}
};
var T_TODAY = '2026-08-27';        // четверг

function runSelfTests(){
  var pass = 0, fail = 0;

  function P(str){ return parse(str, {today: T_TODAY, tracks: T_TRACKS}); }
  function check(name, str, want){
    var p, errs = [], k;
    try{ p = P(str); }
    catch(e){ fail++; console.log('FAIL ' + name + ' - парсер упал: ' + (e && e.message)); return; }
    for(k in want){
      if(!Object.prototype.hasOwnProperty.call(want, k)) continue;
      var got = p[k];
      if(got !== want[k]) errs.push(k + ': ждали ' + JSON.stringify(want[k]) + ', пришло ' + JSON.stringify(got));
    }
    if(errs.length){ fail++; console.log('FAIL ' + name + ' [' + str + '] -> ' + errs.join(' | ')); }
    else{ pass++; console.log('PASS ' + name + ' [' + str + '] -> ' + describe(p, T_TRACKS) + ' | «' + p.title + '»'); }
  }

  console.log('--- CommandBar самотесты, версия ' + ROOT.CommandBar.version + ', сегодня ' + T_TODAY + ' (Чт) ---');

  check('1 полная строка', 'завтра 15:00 монтаж курса 2ч #контент p1',
    {title: 'монтаж курса', date: '2026-08-28', start: '15:00', dur: 120, track: 'content', priority: 1, target: 'event'});

  check('2 сегодня + время', 'сегодня 09:00 звонок с юристом',
    {title: 'звонок с юристом', date: '2026-08-27', start: '09:00', dur: 30, durGiven: false, target: 'event'});

  check('3 послезавтра без времени -> бэклог', 'послезавтра съёмка',
    {title: 'съёмка', date: '2026-08-29', start: null, target: 'backlog', dateGiven: true});

  check('4 короткий день недели', 'пн 10:00 планёрка',
    {title: 'планёрка', date: '2026-08-31', start: '10:00', target: 'event'});

  check('5 полный день недели', 'понедельник 10:00 планёрка',
    {title: 'планёрка', date: '2026-08-31', start: '10:00', target: 'event'});

  check('6 предлог + падеж', 'в среду 11:00 звонок',
    {title: 'звонок', date: '2026-09-02', start: '11:00', target: 'event'});

  check('7 сегодняшний день недели = ближайший будущий', 'чт 15:00 эфир',
    {title: 'эфир', date: '2026-09-03', start: '15:00', target: 'event'});

  check('8 через N дней + дробные часы', 'через 3 дня отчёт 1.5ч',
    {title: 'отчёт', date: '2026-08-30', dur: 90, start: null, target: 'backlog'});

  check('9 дата числом + время пробелом', '28.08 15 30 съёмка',
    {title: 'съёмка', date: '2026-08-28', start: '15:30', target: 'event'});

  check('10 дата с годом + «в 15»', '28.08.2026 в 15 съёмка',
    {title: 'съёмка', date: '2026-08-28', start: '15:00', target: 'event'});

  check('11 утром + минуты словом', 'утром зарядка 30 мин',
    {title: 'зарядка', date: '2026-08-27', start: '09:00', dur: 30, durGiven: true, target: 'event'});

  check('12 днём', 'днём обед',
    {title: 'обед', start: '14:00', target: 'event'});

  check('13 вечером + 90м', 'вечером эфир 90м',
    {title: 'эфир', start: '17:00', dur: 90, target: 'event'});

  check('14 голый текст', 'просто задача',
    {title: 'просто задача', date: T_TODAY, dateGiven: false, start: null, dur: 30, durGiven: false, target: 'backlog'});

  check('15 пустая строка', '',
    {title: '', date: T_TODAY, start: null, dur: 30, target: 'backlog'});

  check('16 когда-нибудь', 'когда-нибудь выучить испанский',
    {title: 'выучить испанский', someday: true, status: 'someday', target: 'backlog'});

  check('17 someday по-английски + p4', 'someday learn spanish p4',
    {title: 'learn spanish', someday: true, status: 'someday', priority: 4, target: 'backlog'});

  check('18 только дата без названия', 'завтра',
    {title: '', date: '2026-08-28', dateGiven: true, target: 'backlog'});

  check('19 трек по подстроке подписи', '#опер починить бота p3',
    {title: 'починить бота', track: 'operac', trackGiven: true, trackMatched: true, priority: 3});

  check('20 трек не найден -> по умолчанию', '#неттакого задача',
    {title: 'задача', track: 'efir', trackGiven: true, trackMatched: false});

  check('21 воскресенье + «2 часа»', 'вс 20:00 отдых 2 часа',
    {title: 'отдых', date: '2026-08-30', start: '20:00', dur: 120, target: 'event'});

  check('22 someday сильнее времени', 'завтра 15:00 монтаж когда-нибудь',
    {title: 'монтаж', someday: true, status: 'someday', target: 'backlog', start: '15:00', date: '2026-08-28'});

  check('23 дата без года в прошлом -> следующий год', '05.01 планёрка',
    {title: 'планёрка', date: '2027-01-05', dateGiven: true, target: 'backlog'});

  check('24 часы и минуты складываются', '1ч 30м настройка сервера',
    {title: 'настройка сервера', dur: 90, durGiven: true, target: 'backlog'});

  check('25 «в 15» без даты', 'в 15 монтаж',
    {title: 'монтаж', date: T_TODAY, start: '15:00', target: 'event'});

  check('26 «в 15 часов» - это время, а не длительность', 'в 15 часов монтаж',
    {title: 'монтаж', start: '15:00', dur: 30, durGiven: false, target: 'event'});

  check('27 трек по коду латиницей', '#content ролик 45 мин',
    {title: 'ролик', track: 'content', trackMatched: true, dur: 45});

  check('28 «через неделю»', 'через неделю ретроспектива',
    {title: 'ретроспектива', date: '2026-09-03', dateGiven: true, target: 'backlog'});

  /* --- круг 4: лимит заголовка, потолок срока, TTL отложенной --- */
  check('29 «когда-нибудь» без срока получает TTL +30',
    'когда-нибудь выучить испанский',
    {title: 'выучить испанский', someday: true, status: 'someday', ttl: '2026-09-26', target: 'backlog'});

  check('30 «когда-нибудь» со сроком: TTL = названный день',
    'когда-нибудь 15.09 разобрать архив',
    {title: 'разобрать архив', someday: true, date: '2026-09-15', ttl: '2026-09-15', dateGiven: true});

  check('31 обычная запись TTL не получает', 'просто задача',
    {title: 'просто задача', someday: false, ttl: null});

  check('32 «через 999 дней» - срок не принят, дата остаётся сегодняшней',
    'через 999 дней отчёт',
    {date: T_TODAY, dateGiven: false, daysTooBig: 999, title: 'через 999 дней отчёт', target: 'backlog'});

  check('33 «через 365 дней» - ровно потолок, срок принят', 'через 365 дней отчёт',
    {date: '2027-08-27', dateGiven: true, daysTooBig: 0, title: 'отчёт'});

  var longTail = new Array(60).join('очень длинное название ');       // 59 повторов, ~1300 символов
  var cut = P(longTail);
  if(cut.title.length <= TITLE_MAX && cut.titleCut === true && cut.titleLen > TITLE_MAX){
    pass++; console.log('PASS 34 заголовок обрезан до ' + cut.title.length + ' из ' + cut.titleLen);
  }else{
    fail++; console.log('FAIL 34 заголовок не обрезан: длина ' + cut.title.length +
      ', titleCut ' + cut.titleCut + ', titleLen ' + cut.titleLen);
  }

  var shortOne = P('короткая задача');
  if(shortOne.titleCut === false && shortOne.title === 'короткая задача'){
    pass++; console.log('PASS 35 короткий заголовок не тронут');
  }else{ fail++; console.log('FAIL 35 короткий заголовок испорчен: «' + shortOne.title + '»'); }

  console.log('--- ИТОГО: PASS ' + pass + ', FAIL ' + fail + ' ---');
  return {pass: pass, fail: fail};
}

ROOT.CommandBar._selfTest = runSelfTests;
if(testsRequested()){
  if(typeof setTimeout === 'function') setTimeout(runSelfTests, 0);
  else runSelfTests();
}

})();

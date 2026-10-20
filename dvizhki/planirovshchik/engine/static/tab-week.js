/* Вкладка «Неделя»: недельный timeline как Google Calendar (сетка часов,
   drag&drop мышью И пальцем, resize, полоса лент «идёт само», точки запуска,
   бэклог, боковая панель, быстрый ввод задачи).

   На узком экране (<=600px) вкладка по умолчанию показывает ОДИН день во всю
   ширину: карточка «что сейчас» крупно, стрелки и свайп переключают дни,
   кнопка в шапке возвращает недельную сетку. На широком экране режим дня не
   включается вовсе - там всё как было.

   Границы сетки, пиковое окно, защищённые дни и тренировка берутся из
   profile.json. Весь код завёрнут в IIFE: наружу торчит только TABS.week. */
(function(){
'use strict';

const U = App.utils;
const pad = U.pad, iso = U.iso, parseISO = U.parseISO, hhmm = U.hhmm, startOfWeek = U.startOfWeek;

const HH = 52;                 // высота часа, синхронно с --hh в app.css
const DAY_END = 24 * 60;       // граница суток для событий через полночь
const DUR_MIN = 15, DUR_MAX = 720, DUR_MIN_L = 5;   // 15 минут - 12 часов
const NARROW = '(max-width:600px)';   // та же граница, что у мобильного блока app.css
const VIEW_KEY = 'wk-view';           // выбор владельца «день/неделя» переживает перезагрузку
const SOMEDAY_TTL = 30;               // дней жизни отложенной задачи, как в rituals/decide.py
/* Минуты фокуса, которые сервер ещё НЕ подтвердил. Живут в localStorage, потому
   что пережить обязаны и конфликт версий, и уход со страницы. */
const FZ_PEND_KEY = 'wk-fz-pending';
const FZ_PEND_TTL = 30;               // дней: старше - запись протухла, задачу уже не найти

/* Окно сетки фиксировано: 06:00 - 00:00. Раньше нижняя граница считалась от
   видно вовсе. Владелец: «отображение сделай с 6 утра» и «до 0 часов
   полностью». Границы суток теперь не прячут сетку, а рисуются зонами
   (до подъёма / утро / работа / wind down / сон), см. dayZones(). */
const GRID_H0 = 6, GRID_H1 = 24;

/* Ритм дня: дефолты методологические, профиль их перебивает.
   Блок = ровно 90 минут ЦЕЛИКОМ: 80 минут фокуса и 10 минут перерыва в конце,
   а не 90 работы плюс перерыв сверху. Так все блоки стартуют по круглому
   времени и день не расползается (решение владельца, static/day.html). */
const RHY_BLOCK = 90;          // ультрадианный цикл
const RHY_BREAK = 10;          // перерыв ВНУТРИ блока, в его конце
const RHY_LUNCH = '12:00', RHY_LUNCH_DUR = 60;    // обед подводит к провалу 13:00-15:00
const RHY_DINNER = '19:00', RHY_DINNER_DUR = 30;  // ужин за 3.5 часа до сна
const MAGNET = 12;             // прилипание к началу фокуса в пределах 12 минут
const RHY_MAX_DEEP = 2;        // глубоких блоков в день реально один-два
const RHY_MIN_BLOCK = 30;      // короче этого - не блок, а пауза
const RHY_MIN_FOCUS = 15;      // фокус не режем ниже этого ради перерыва

let H0 = GRID_H0, H1 = GRID_H1;   // окно суток на сетке
let DATA = null, PROFILE = null, weekStart = null, sel = null;
/* Цели цикла читаются ТОЛЬКО на чтение. Полоса задач - проекция, а не копия:
   в sprint.json ни названия задачи, ни её id пакетом не переносится, поэтому
   расходиться при переименовании или закрытии задачи физически нечему. */
let GOALS = null;
let weekBound = false;         // keydown/interval/pagehide вешаем один раз на страницу
let dragging = false;          // не перерисовывать сетку под пальцем
let suppressClickUntil = 0;    // чтобы тап-перенос не открывал карточку
let viewMode = 'week';         // 'week' - сетка недели, 'day' - один день во всю ширину
let dayCursor = null;          // какой день открыт в режиме одного дня (ISO)

/* ---------- безопасность и мелкие утилиты ---------- */
const ESCMAP = {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;','`':'&#96;'};
function esc(v){ return String(v == null ? '' : v).replace(/[&<>"'`]/g, c => ESCMAP[c]); }
function color(c){ return /^#[0-9a-f]{3,8}$/i.test(String(c||'')) ? c : '#5f6368'; }
function tmin(t){                                   // «HH:MM» -> минуты, без падений
  const m = /^(\d{1,2}):(\d{2})/.exec(String(t||''));
  if(!m) return 0;
  return Math.min(DAY_END, Math.max(0, (+m[1])*60 + (+m[2])));
}
function clampDur(m, isLaunch){
  const lo = isLaunch ? DUR_MIN_L : DUR_MIN;
  if(!isFinite(m)) return lo;
  return Math.min(DUR_MAX, Math.max(lo, Math.round(m/5)*5));
}
function uid(p){ return p + Date.now().toString(36) + Math.random().toString(36).slice(2,5); }
function dayDiff(a, b){ return Math.round((parseISO(b) - parseISO(a)) / 864e5); }
function addDays(k, n){ const d = parseISO(k); d.setDate(d.getDate()+n); return iso(d); }
function isDate(s){ return /^\d{4}-\d{2}-\d{2}$/.test(String(s||'')); }
function shortDate(k){ return isDate(k) ? k.slice(8,10)+'.'+k.slice(5,7) : k; }
function hoursTxt(m){ return (m/60).toFixed(m%60 ? 1 : 0) + ' ч'; }
/* Часы для поля ввода: шаг 0.05 ч = 3 минуты. Сырое 215/60 давало
   3,5833333333333335 в поле. Шаг подобран так, чтобы обратный перевод
   (часы -> минуты -> clampDur) вернул те же минуты: 215 -> 3.6 -> 216 -> 215. */
function hoursVal(m){ return Math.round(Math.max(0, +m || 0)/3)/20; }
const $ = id => document.getElementById(id);

/* ---------- режим одного дня ---------- */
function isNarrow(){
  try{ return window.matchMedia(NARROW).matches; }
  catch(e){ return (window.innerWidth || 1024) <= 600; }
}
function readViewPref(){ try{ return localStorage.getItem(VIEW_KEY); }catch(e){ return null; } }
function writeViewPref(v){ try{ localStorage.setItem(VIEW_KEY, v); }catch(e){} }
/* На широком экране режим дня не предлагается вовсе: недельная сетка там канон. */
function resolveView(){
  if(!isNarrow()) return 'week';
  return readViewPref() === 'week' ? 'week' : 'day';
}
function syncWeekToCursor(){ if(isDate(dayCursor)) weekStart = startOfWeek(parseISO(dayCursor)); }
function visibleDays(){
  if(viewMode === 'day'){
    if(!isDate(dayCursor)) dayCursor = iso(new Date());
    return [parseISO(dayCursor)];
  }
  return [...Array(7)].map((_,i)=>{ const d = new Date(weekStart); d.setDate(d.getDate()+i); return d; });
}

const DOW_KEY = ['sun','mon','tue','wed','thu','fri','sat'];
const DOW_RU = {mon:'понедельник',tue:'вторник',wed:'среда',thu:'четверг',fri:'пятница',sat:'суббота',sun:'воскресенье'};
const MON = ['января','февраля','марта','апреля','мая','июня','июля','августа','сентября','октября','ноября','декабря'];
function dowOf(k){ return DOW_KEY[parseISO(k).getDay()]; }

/* ---------- каркас вкладки ---------- */
function renderWeek(container){
  injectCSS();
  qaClose();
  viewMode = resolveView();
  if(!isDate(dayCursor)) dayCursor = iso(new Date());
  container.innerHTML = `
    <div class="week-root">
      <div class="weekbar">
        <button class="today-btn" id="wk-today">Сегодня</button>
        <div class="nav"><button id="wk-prev" aria-label="назад">‹</button><button id="wk-next" aria-label="вперёд">›</button></div>
        <div class="wk-undobar" id="wk-undobar"></div>
        <div class="range" id="range"></div>
        <button class="wk-view" id="wk-view"></button>
        <button class="wk-plan" id="wk-plan" title="Разложить «Не разложено» по свободным слотам недели: сначала покажу превью">Разложить</button>
        <button class="wk-add" id="wk-add">+ Задача</button>
        <div class="wk-saveerr" id="wk-saveerr"></div>
        <div class="goal" id="goal"></div>
      </div>
      <div class="wk-decidebar" id="wk-decidebar"></div>
      <div class="wk-focus" id="wk-focus"></div>
      <div class="wk-strip">
        <div class="wk-nextstep" id="wk-nextstep"></div>
        <div class="wk-projection" id="wk-projection"></div>
        <div class="legend" id="legend"></div>
      </div>
      <div class="dayrow" id="dayrow"></div>
      <div class="autorow" id="autorow"></div>
      <div class="scroll" id="scroll"><div class="grid" id="grid"></div></div>
      <div class="backlog" id="backlog"></div>
      <div class="panel" id="panel"></div>
    </div>`;

  $('wk-today').addEventListener('click', goToday);
  $('wk-prev').addEventListener('click', ()=>shift(-7));
  $('wk-next').addEventListener('click', ()=>shift(7));
  $('wk-add').addEventListener('click', ()=>openQuickAdd({}));
  $('wk-plan').addEventListener('click', openAutoPlan);
  $('wk-view').addEventListener('click', toggleView);
  bindSwipe();

  bindOnce();
  loadWeek().then(scrollToNow).catch(err=>{
    notify('Не получилось загрузить неделю: ' + (err.message||err), 'err', 9000);
  });
}

/* «день целиком» <-> «неделя целиком», выбор запоминаем */
function toggleView(){
  viewMode = viewMode === 'day' ? 'week' : 'day';
  writeViewPref(viewMode);
  if(viewMode === 'day'){
    if(!isDate(dayCursor)) dayCursor = iso(new Date());
    syncWeekToCursor();
  }
  render();
  scrollToNow();
}

/* свайп в режиме дня = соседний день. Слушатели пассивные: свайп ничего не
   отменяет, вертикальную прокрутку сетки трогать нельзя. Если под пальцем уже
   идёт перенос или тяга длительности (dragging), свайп молчит.
   Бэклог сюда не берём: он сам листается пальцем по горизонтали. */
function bindSwipe(){
  ['scroll','wk-focus','dayrow','autorow'].forEach(id=>{
    const el = $(id);
    if(!el) return;
    let x0 = 0, y0 = 0, live = false;
    el.addEventListener('touchstart', e=>{
      live = e.touches.length === 1 && !dragging;
      if(!live) return;
      x0 = e.touches[0].clientX; y0 = e.touches[0].clientY;
    }, {passive:true});
    el.addEventListener('touchend', e=>{
      if(!live) return;
      live = false;
      if(dragging || viewMode !== 'day') return;      // под пальцем идёт перенос блока
      const t = e.changedTouches && e.changedTouches[0];
      if(!t) return;
      const dx = t.clientX - x0, dy = t.clientY - y0;
      if(Math.abs(dx) < 60 || Math.abs(dx) < Math.abs(dy)*1.6) return;
      suppressClickUntil = Date.now() + 400;
      shift(dx < 0 ? 1 : -1);
    }, {passive:true});
  });
}

/* keydown, минутный тик и досылка правки живут на странице один раз */
function bindOnce(){
  if(weekBound) return;
  weekBound = true;
  document.addEventListener('keydown', e=>{
    /* Фокус-режим - модальное окно поверх всего: Escape спрашивает и выходит,
       остальные ключи (в том числе Cmd+Z) в нём не работают. */
    if(fzOn()){
      if(e.key === 'Escape'){ e.preventDefault(); fzEscape(); }
      return;
    }
    if(e.key === 'Escape'){
      if($('wk-modal')) qaClose(); else closePanel();
      return;
    }
    /* Отмена и возврат. Не перехватываем, пока курсор в поле ввода: там свой,
       текстовый Cmd+Z, и отнимать его у владельца нельзя. Вкладка не активна
       (нет сетки) - молчим, ключи принадлежат чужой вкладке. */
    if(!(e.metaKey || e.ctrlKey) || !$('grid') || !DATA) return;
    const t = e.target;
    if(t && t.closest && t.closest('input,textarea,select')) return;
    const key = String(e.key || '').toLowerCase();
    if(key === 'z'){
      e.preventDefault();
      if(e.shiftKey) redoLast(); else undoLast();
    }else if(key === 'y' && !e.metaKey){
      e.preventDefault();
      redoLast();
    }
  });
  setInterval(()=>{
    if(!$('grid') || dragging || $('wk-modal')) return;   // вкладка не активна, перенос или открыт диалог
    if(viewMode === 'day'){
      if(dayCursor === iso(new Date())) render();
      return;
    }
    if(iso(startOfWeek(new Date())) === iso(weekStart)) render();
  }, 60000);
  // поворот телефона или окно, растянутое до десктопа: режим пересобираем
  let wasNarrow = isNarrow();
  window.addEventListener('resize', ()=>{
    const n = isNarrow();
    if(n === wasNarrow) return;
    wasNarrow = n;
    const want = resolveView();
    if(want !== viewMode){
      viewMode = want;
      if(viewMode === 'day' && !isDate(dayCursor)) dayCursor = iso(new Date());
      if(viewMode === 'day') syncWeekToCursor();
    }
    if($('grid')) render();
  });
  // сосед (Cmd+K, вкладка «План») записал документ - перечитываем, мягко
  window.addEventListener('sprint:changed', onExternalChange);
  // правка не должна умереть внутри дебаунса при уходе со страницы
  window.addEventListener('pagehide', beaconFlush);
  window.addEventListener('beforeunload', beaconFlush);
  document.addEventListener('visibilitychange', ()=>{
    if(document.visibilityState === 'hidden') beaconFlush();
  });
}

async function loadWeek(){
  const [data, profile, goals] = await Promise.all([
    App.api.get('/api/data'),
    App.api.get('/api/profile').catch(()=>null),
    App.api.get('/api/goals').catch(()=>null),
  ]);
  GOALS = goals || null;
  DATA = data || {};
  DATA.events = Array.isArray(DATA.events) ? DATA.events : [];
  DATA.backlog = Array.isArray(DATA.backlog) ? DATA.backlog : [];
  DATA.auto = Array.isArray(DATA.auto) ? DATA.auto : [];
  DATA.tracks = (DATA.tracks && typeof DATA.tracks === 'object') ? DATA.tracks : {};
  PROFILE = profile;
  resetRhythm();
  histInit();                                  // история отмены живёт от загрузки страницы
  weekStart = weekStart || startOfWeek(new Date());
  render();
  fzRecoverPending();                          // минуты фокуса, которые сервер не подтвердил
}

/* ---------- сохранение ---------- */
let saveTimer = null, dirty = false, inFlight = false, conflictRev = null;
/* служебные поля рендера (_lane, _row, _s, _e) в файл не уезжают */
function payloadJSON(){ return JSON.stringify(DATA, (k,v)=> (k && k.charAt(0)==='_') ? undefined : v); }

/* ---------- отмена и возврат (Cmd+Z / Ctrl+Z) ----------
   Раньше любое действие было необратимо: передвинул задачу - вспоминай, где она
   стояла. Историю снимаем СНИМКАМИ документа в единственной точке - save(): её
   зовёт каждый мутирующий путь (перенос, тяга длительности, создание, удаление,
   правка карточки, «готово», раскладка чипа, решения по застрявшей, цель
   спринта). Поэтому каскадный сдвиг цепочки откатывается целиком: точка запуска
   и окно ленты уехали внутри той же правки, значит и вернутся вместе с ней.
   История живёт в пределах открытой страницы, между перезагрузками не нужна. */
const UNDO_MAX = 20;
let undoStack = [], redoStack = [], histPrev = null, histSilent = false;
let histBooted = false;        // стек живёт от загрузки СТРАНИЦЫ, а не от захода на вкладку

function histSnap(){
  return JSON.stringify(
    {events:DATA.events, backlog:DATA.backlog, auto:DATA.auto, sprintGoal:DATA.sprintGoal},
    (k,v)=> (k && k.charAt(0)==='_') ? undefined : v);
}
/* Переключение вкладок пересобирает модуль и снова зовёт loadWeek(). Раньше
   здесь обнулялся стек: разложил визардом, сходил в «План», вернулся - а
   откатывать уже нечего. Стек теперь переживает переключение вкладок и умирает
   вместе со страницей; базу дельты (histPrev) при каждой загрузке пересобираем
   заново, чтобы новая дельта считалась от того, что реально лежит на диске. */
function histInit(){
  if(!histBooted){ undoStack = []; redoStack = []; histBooted = true; }
  histPrev = DATA ? histSnap() : null;
}
/* Записать дельту. Зовётся из save() ДО планирования записи на сервер. */
function histPush(label){
  if(!DATA) return;
  const after = histSnap();
  if(histSilent || histPrev === null || histPrev === after){ histPrev = after; return; }
  undoStack.push({label: label || 'правка', before: histPrev, after});
  if(undoStack.length > UNDO_MAX) undoStack.shift();
  redoStack = [];
  histPrev = after;
}
/* Снимок отмены описывает ТОЛЬКО нашу дельту. Пока стек ждал (владелец ушёл на
   другую вкладку, командная строка дописала задачу через Cmd+K), в документе
   мог появиться чужой объект: его нет ни в «до», ни в «после» правки, значит к
   дельте он отношения не имеет и отмена не должна его съедать. Всё, чего не
   знают обе стороны дельты, переносим в результат как есть. */
function foreignKeep(snapList, otherList, cur){
  const known = Object.create(null);
  const mark = arr => (Array.isArray(arr) ? arr : []).forEach(x=>{ if(x && x.id) known[x.id] = 1; });
  mark(snapList); mark(otherList);
  const out = Array.isArray(snapList) ? snapList.slice() : [];
  (Array.isArray(cur) ? cur : []).forEach(x=>{ if(x && x.id && !known[x.id]) out.push(x); });
  return out;
}
/* Применить снимок. Дальше всё как у обычной правки: та же save(), та же
   версия документа, тот же баннер при конфликте 409 - отмена не теряется молча.
   otherRaw - вторая сторона той же дельты, нужна ровно для foreignKeep(). */
function histApply(raw, note, backLabel, backFn, otherRaw){
  const s = JSON.parse(raw);
  let o = {};
  try{ o = otherRaw ? JSON.parse(otherRaw) : {}; }catch(e){ o = {}; }
  DATA.events  = foreignKeep(s.events,  o.events,  DATA.events);
  DATA.backlog = foreignKeep(s.backlog, o.backlog, DATA.backlog);
  DATA.auto    = foreignKeep(s.auto,    o.auto,    DATA.auto);
  DATA.sprintGoal = typeof s.sprintGoal === 'string' ? s.sprintGoal : '';
  histSilent = true;
  save();                                     // histPrev пересоберётся внутри histPush
  histSilent = false;
  if(sel && !DATA.events.some(e=>e.id === sel)) closePanel();
  render();
  notifyAction(note, backLabel, backFn);
}
function undoLast(){
  const item = undoStack.pop();
  if(!item) return notify('Отменять нечего: с открытия страницы правок не было', null, 3000);
  redoStack.push(item);
  histApply(item.before, 'Отменено: ' + item.label, 'Вернуть', redoLast, item.after);
}
function redoLast(){
  const item = redoStack.pop();
  if(!item) return notify('Возвращать нечего', null, 3000);
  undoStack.push(item);
  histApply(item.after, 'Вернул: ' + item.label, 'Снова отменить', undoLast, item.before);
}
/* Кнопки в шапке: на телефоне клавиатуры нет, а отмена нужна там же */
function renderUndoBar(){
  const box = $('wk-undobar');
  if(!box) return;
  const u = undoStack.length, r = redoStack.length;
  if(!u && !r){ box.className = 'wk-undobar'; box.innerHTML = ''; return; }
  box.className = 'wk-undobar on';
  const last = u ? undoStack[undoStack.length-1].label : '';
  box.innerHTML =
    (u ? `<button type="button" id="wk-undo" title="Отменить: ${esc(last)} (Cmd+Z / Ctrl+Z)">↶ Отменить</button>` : '') +
    (r ? `<button type="button" class="re" id="wk-redo" title="Вернуть отменённое (Cmd+Shift+Z / Ctrl+Y)">↷</button>` : '');
  if($('wk-undo')) $('wk-undo').addEventListener('click', undoLast);
  if($('wk-redo')) $('wk-redo').addEventListener('click', redoLast);
}

function save(label){
  histPush(label);
  dirty = true;
  clearTimeout(saveTimer);
  saveTimer = setTimeout(()=>flush(), 400);
}
/* Сервер держит версию документа (rev): без неё запись не примут (428),
   с чужой - вернут конфликт (409). Молча глотать это нельзя. */
async function flush(isRetry){
  clearTimeout(saveTimer); saveTimer = null;
  if(!DATA) return;
  if(inFlight){ saveTimer = setTimeout(()=>flush(), 250); return; }
  inFlight = true;
  let retry = false;
  /* Тело и список страховок снимаем ОДНОВРЕМЕННО: всё, что лежит в страховке
     сейчас, уже сидит в этом теле, значит после 200 её можно снимать. Минуты,
     записанные позже, в этот список не попадут и переживут ответ. */
  const body = payloadJSON();
  const sentPend = fzPendIds();
  try{
    const res = await fetch('/api/data', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body,
    });
    let out = null;
    try{ out = await res.json(); }catch(e){ out = null; }
    if(res.ok){
      if(out && out.rev) DATA.rev = out.rev;
      dirty = false; conflictRev = null;
      setSaveError(null);
      fzPendDrop(sentPend);                     // запись подтверждена - страховку снимаем
      App.flashSaved();
      dispatchChanged();                        // соседние вкладки не должны жить на протухшей копии
    }else if(res.status === 428 && out && out.rev && !isRetry){
      DATA.rev = out.rev;                       // версию не показали, берём и повторяем
      retry = true;
    }else if(res.status === 409 && out && out.rev){
      conflictRev = out.rev;
      showConflict();
    }else{
      throw new Error((out && (out.message || out.error)) || ('сервер ответил ' + res.status));
    }
  }catch(err){
    setSaveError(err && err.message ? err.message : String(err));
  }finally{
    inFlight = false;
  }
  if(retry) await flush(true);
}

/* Последний рубеж показа. Контейнер ошибок живёт ВНУТРИ вкладки и умирает при
   переключении (app.js чистит #tab-root), а фокус-таймер висит на body и пишет
   дальше. Раньше обе функции ниже делали ранний return при отсутствии
   контейнера - и стоп таймера с чужой вкладки при 409 не давал ни баннера, ни
   тоста. Теперь нет контейнера - падаем на глобальный тост оболочки: он
   создаётся на body по требованию и жив всегда. */
function alarm(text){
  try{
    if(typeof App !== 'undefined' && App && typeof App.notify === 'function'){ App.notify(text); return; }
  }catch(e){}
  notify(text, 'err', 12000);                 // оболочки нет - хотя бы свой тост
}
function setSaveError(msg){
  const box = $('wk-saveerr');
  if(!msg){
    if(box){ box.classList.remove('on'); box.innerHTML = ''; }
    return;
  }
  if(!box){
    alarm('Неделя: не сохранено - ' + msg + '. Открой вкладку «Неделя», в шапке будет кнопка «Повторить»');
    return;
  }
  box.innerHTML = '<span>⚠ Не сохранено: ' + esc(msg) + '</span><button type="button" id="wk-retry">Повторить</button>';
  box.classList.add('on');
  $('wk-retry').addEventListener('click', ()=>flush());
  notify('Сохранить не удалось: ' + msg + '\nПравка живёт только на экране, нажми «Повторить» в шапке', 'err', 9000);
}
/* другое окно записало свою версию: выбор оставляем владельцу, тихо не затираем */
function showConflict(){
  const box = $('wk-saveerr');
  if(!box){
    alarm('Другое окно изменило план, правка Недели не записана. ' + (fzPendCount()
      ? 'Минуты фокуса сохранены: открой вкладку «Неделя» - предложу дописать'
      : 'Открой вкладку «Неделя» и повтори правку'));
    return;
  }
  box.innerHTML = '<span>⚠ Другое окно изменило план, твоя правка не записана</span>' +
    '<button type="button" id="wk-force">Перезаписать</button>' +
    '<button type="button" id="wk-reload">Взять с диска</button>';
  box.classList.add('on');
  $('wk-force').addEventListener('click', ()=>{ if(conflictRev) DATA.rev = conflictRev; flush(true); });
  $('wk-reload').addEventListener('click', ()=>{
    dirty = false; conflictRev = null; setSaveError(null);
    loadWeek().then(()=>notify('Взял версию с диска, твоя несохранённая правка ушла', null, 6000));
  });
  notify('Другое окно уже сохранило свою версию плана.\nТвоя правка НЕ записана: выбери в шапке «Перезаписать» или «Взять с диска»', 'err', 12000);
}
/* уходим со страницы внутри дебаунса - досылаем маячком */
function beaconFlush(){
  if(!dirty || !DATA) return;
  clearTimeout(saveTimer); saveTimer = null;
  try{
    const blob = new Blob([payloadJSON()], {type:'application/json'});
    if(navigator.sendBeacon && navigator.sendBeacon('/api/data', blob)) dirty = false;
  }catch(e){ /* уходящую страницу спасать больше нечем */ }
}

/* ---------- контракт волны: «документ изменился» ----------
   Cmd+K (command.js) и вкладка «План» пишут своим каналом со своей версией
   документа. Раньше открытая сетка про это не знала: задачи не видно, rev
   протухла, и первый же конфликт предлагал «Перезаписать» - то есть затереть
   чужую свежую запись. Теперь после КАЖДОЙ подтверждённой записи модуль кричит
   на window, а слушатели перечитывают документ. Своё событие узнаём по source
   и на него не реагируем - иначе получилась бы петля. */
function dispatchChanged(){
  try{ window.dispatchEvent(new CustomEvent('sprint:changed', {detail:{source:'week'}})); }
  catch(e){ /* старый браузер без CustomEvent - соседи перечитают при заходе */ }
}

let extPending = false, extTimer = null, extTries = 0;
/* Перечитку откладываем, пока идёт незакоммиченное действие: под пальцем блок,
   открыта карточка задачи или диалог, либо своя правка ещё не доехала до диска.
   Свежесть данных не стоит потерянного драга. */
function extBusy(){
  return dragging || !!sel || !!$('wk-modal') || dirty || inFlight;
}
function extReload(){
  clearTimeout(extTimer); extTimer = null;
  if(!extPending) return;
  if(!$('grid') || !DATA){ extPending = false; extTries = 0; return; }  // вкладка закрыта: перечитает loadWeek
  if(extBusy()){
    if(extTries++ > 240){ extPending = false; extTries = 0; return; }   // 2 минуты ждём, дальше не навязываемся
    extTimer = setTimeout(extReload, 500);
    return;
  }
  extPending = false; extTries = 0;
  App.api.get('/api/data').then(doc=>{
    if(!doc || typeof doc !== 'object') return;
    if(!$('grid') || extBusy()) { extPending = true; extReload(); return; }   // пока читали, начали действие
    DATA = doc;
    DATA.events  = Array.isArray(DATA.events)  ? DATA.events  : [];
    DATA.backlog = Array.isArray(DATA.backlog) ? DATA.backlog : [];
    DATA.auto    = Array.isArray(DATA.auto)    ? DATA.auto    : [];
    DATA.tracks  = (DATA.tracks && typeof DATA.tracks === 'object') ? DATA.tracks : {};
    dirty = false; conflictRev = null;
    setSaveError(null);
    resetRhythm();
    histPrev = histSnap();       // базой истории становится диск, сам стек отмены живёт дальше
    render();
  }).catch(()=>{ /* сеть моргнула - перечитаем при следующем заходе на вкладку */ });
}
function onExternalChange(ev){
  const src = (ev && ev.detail && ev.detail.source) || '';
  if(src === 'week') return;                   // своё же эхо
  extPending = true;
  extReload();
}

/* стрелки: в режиме недели шаг 7 дней, в режиме дня - один день */
function shift(n){
  if(viewMode === 'day'){
    dayCursor = addDays(isDate(dayCursor) ? dayCursor : iso(new Date()), n > 0 ? 1 : -1);
    syncWeekToCursor();
    render();
    return;
  }
  weekStart.setDate(weekStart.getDate()+n);
  render();
}
function goToday(){
  dayCursor = iso(new Date());
  weekStart = startOfWeek(new Date());
  render();
  scrollToNow();
}

/* ---------- наложения: не блокируем, но молчать нельзя ---------- */
/* минуты от эпохи, чтобы хвост через полночь честно пересекался со следующим днём */
function absRange(e){
  if(!isDate(e.date)) return null;
  const s = parseISO(e.date).getTime()/60000 + tmin(e.start);
  return {s, e: s + Math.max(0, +e.dur||0)};
}
function overlapsOf(ev){
  const a = absRange(ev);
  if(!a || a.e <= a.s) return [];
  return DATA.events
    .filter(x=>x !== ev && x.id !== ev.id)
    .map(x=>({x, r:absRange(x)}))
    .filter(o=>o.r && o.r.e > o.r.s && o.r.e > a.s && o.r.s < a.e)
    .sort((p,q)=>p.r.s - q.r.s)
    .map(o=>o.x);
}
function overlapMsg(ev){
  const hit = overlapsOf(ev);
  if(!hit.length) return null;
  const f = hit[0];
  const fin = hhmm((tmin(f.start) + (+f.dur||0)) % DAY_END);
  return '⚠ Наложение: «' + ev.title + '» пересекается с «' + f.title + '» (' +
         shortDate(f.date) + ' ' + f.start + '-' + fin + ')' +
         (hit.length > 1 ? ' и ещё с ' + (hit.length-1) : '') +
         '. Не отменяю - если это нарочно, просто иди дальше';
}
/* Один вход для всех мягких предупреждений хода: наложение задач + попадание в
   перерыв, обед или зону сна (pushSoft ниже по файлу). Зовётся из всех мест,
   где задача переехала - перенос, тяга длительности, правка карточки, решение
   по застрявшей, раскладка чипа из бэклога. Ничего не блокирует. */
function pushOverlap(msgs, ev){
  const m = overlapMsg(ev);
  if(m){ msgs.push(m); msgs.overlap = true; }
  pushSoft(msgs, ev);
  return msgs;
}
/* один рупор на все сообщения хода: тосты не должны перебивать друг друга */
function tell(msgs){
  if(!msgs || !msgs.length) return;
  notify(msgs.join('\n'), msgs.warn ? 'err' : (msgs.overlap ? 'warn' : null), 9000);
}

/* ---------- профиль: окно суток, пик, защищённые дни, тренировка ---------- */
/* Низ сетки всегда полночь. Верх - 06:00, и опускается выше только если иначе
   что-то реальное окажется за кадром: ранняя тренировка, начало пика или уже
   запланированная задача. От wake/sleep граница больше НЕ зависит - они рисуются
   зонами внутри сетки, а не режут её. */
function computeBounds(days){
  let h0 = GRID_H0;
  if(PROFILE){
    if(PROFILE.peakFrom) h0 = Math.min(h0, Math.floor(tmin(PROFILE.peakFrom)/60));
    const t = PROFILE.training;
    if(t && t.start) h0 = Math.min(h0, Math.floor(tmin(t.start)/60));
  }
  // что уже запланировано в этой неделе, обязано быть видно
  const keys = days.map(iso);
  DATA.events.forEach(e=>{
    if(keys.indexOf(e.date) < 0) return;
    h0 = Math.min(h0, Math.floor(tmin(e.start)/60));
  });
  H0 = Math.max(0, Math.min(GRID_H1 - 1, h0));
  H1 = GRID_H1;
}
function peakWindow(){
  if(!PROFILE || !PROFILE.peakFrom || !PROFILE.peakTo) return null;
  const a = tmin(PROFILE.peakFrom), b = tmin(PROFILE.peakTo);
  return b > a ? {from:a, to:b} : null;
}
function protectedDays(){
  const p = PROFILE && PROFILE.protectedDays;
  return Array.isArray(p) ? p : [];
}
function isProtectedDay(k){ return protectedDays().indexOf(dowOf(k)) >= 0; }
function trainingFor(k){
  const t = PROFILE && PROFILE.training;
  if(!t || !t.start || !Array.isArray(t.days)) return null;
  if(t.days.indexOf(dowOf(k)) < 0) return null;
  const s = tmin(t.start), d = Math.max(15, +t.dur || 60);
  return {start:s, end:Math.min(DAY_END, s+d)};
}
/* почему в этот слот нельзя: защищённый день или тренировка */
function slotBlocked(dateKey, startMin, dur){
  if(!isDate(dateKey)) return 'Дата не распознана';
  if(isProtectedDay(dateKey)){
    const d = DOW_RU[dowOf(dateKey)] || dateKey;
    return 'День ' + d + ' (' + shortDate(dateKey) + ') помечен защищённым в настройках: работу туда не кладём';
  }
  const t = trainingFor(dateKey);
  if(t && startMin < t.end && startMin + dur > t.start){
    return 'Слот ' + hhmm(t.start) + '-' + hhmm(t.end) + ' занят тренировкой из настроек, он защищён';
  }
  /* Утреннее окно от подъёма до начала работы. Подсказка блока утра обещает
     «Рабочие блоки сюда не ставятся», а сторожа у этого обещания не было: он
     закрывал только час тренировки, и задача спокойно вставала в 08:15. Обещание
     интерфейса обязано иметь механизм, иначе это просто надпись. */
  const p = PROFILE || {};
  const wake = p.wake ? tmin(p.wake) : null;
  const ws = p.workStart ? tmin(p.workStart) : null;
  if(wake != null && ws != null && ws > wake && startMin < ws && startMin + dur > wake){
    return 'Утро ' + hhmm(wake) + '-' + hhmm(ws) + ' - окно вне работы из настроек: ' +
           'своё, не рабочее. Рабочие блоки сюда не ставятся';
  }
  return null;
}

/* ================= ритм дня: блоки, перерывы, обед, зоны суток =================
   Владелец не видел, куда целиться при перетаскивании: в сетке были только
   часовые линии. Теперь рабочее окно из профиля размечено фоном - блоки по 90
   минут (ультрадианный цикл), между ними перерывы, в циркадный дип - обед.
   Это ФОН: pointer-events нет, задачи рисуются поверх и остаются читаемыми.

   Физиология, зашитая в подписи и подсказки:
   · фокус-блок 90 минут, дальше концентрация падает;
   · перерыв 10-30 минут и обязательно без экрана;
   · провал бдительности - через 6-8 часов после подъёма (циркадный дип);
   · глубоких блоков в день реально один-два, остальные средней нагрузки;
   · заполнять стоит ~60% ёмкости, остальное буфер (валидатор перегруза выше). */

function clampNum(v, lo, hi, fallback){
  const n = +v;
  if(!isFinite(n)) return fallback;
  return Math.max(lo, Math.min(hi, Math.round(n)));
}
function timeOr(v, fallback){
  return /^\d{1,2}:\d{2}$/.test(String(v||'')) ? tmin(v) : tmin(fallback);
}
function rhythmCfg(){
  const p = PROFILE || {};
  return {
    on: p.rhythmOn !== false,                                   // ключа нет - считаем «включено»
    block: clampNum(p.deepBlockMin, 15, 480, RHY_BLOCK),
    brk: clampNum(p.breakMin, 0, 180, RHY_BREAK),
    lunch: timeOr(p.lunchStart, RHY_LUNCH),
    lunchDur: clampNum(p.lunchDur, 0, 240, RHY_LUNCH_DUR),
    dinner: timeOr(p.dinnerStart, RHY_DINNER),
    dinnerDur: clampNum(p.dinnerDur, 0, 240, RHY_DINNER_DUR),
  };
}
/* Циркадный дип: 6-8 часов после подъёма. При подъёме 07:00 это 13:00-15:00. */
function dipWindow(){
  if(!PROFILE || !PROFILE.wake) return null;
  const w = tmin(PROFILE.wake);
  const from = w + 6*60;
  if(from >= DAY_END) return null;
  return {from, to: Math.min(DAY_END, w + 8*60)};
}
function workWindow(){
  if(!PROFILE || !PROFILE.workStart || !PROFILE.workEnd) return null;
  const a = tmin(PROFILE.workStart), b = tmin(PROFILE.workEnd);
  return b - a >= 30 ? {from:a, to:b} : null;
}
/* пересечение отрезков в минутах */
function cross(a1, a2, b1, b2){ return Math.max(0, Math.min(a2, b2) - Math.max(a1, b1)); }

/* Разметка рабочего окна одного дня. Отрезки: block (внутри него focusEnd и
   хвост-перерыв), lunch, dinner, gap (огрызок короче получаса).
   Раскладка при профиле владельца (работа 09-21, блок 90, перерыв 10,
   обед 12:00 на час, ужин 19:00 на полчаса) - ровно семь блоков без остатка:
     09:00-10:30 блок 1 глубокий (фокус до 10:20) · 10:30-12:00 блок 2 глубокий
     · 12:00-13:00 обед · 13:00-14:30 блок 3 механика · 14:30-16:00 блок 4
     средний · 16:00-17:30 блок 5 рутина · 17:30-19:00 блок 6 рутина
     · 19:00-19:30 ужин · 19:30-21:00 блок 7 буфер */
function buildRhythm(dateKey){
  const cfg = rhythmCfg();
  const w = workWindow();
  if(!cfg.on || !w) return [];
  if(isProtectedDay(dateKey)) return [];      // защищённый день работой не размечаем

  const meals = [];
  const meal = (type, from, dur, label)=>{
    if(dur <= 0 || from < w.from || from >= w.to) return;
    meals.push({type, start:from, end:Math.min(w.to, from + dur), label});
  };
  meal('lunch', cfg.lunch, cfg.lunchDur, 'Обед');
  meal('dinner', cfg.dinner, cfg.dinnerDur, 'Ужин');
  meals.sort((a,b)=>a.start - b.start);

  const out = [];
  let t = w.from, n = 0, guard = 0;
  while(t < w.to && guard++ < 80){
    const now = meals.find(m=>t >= m.start && t < m.end);
    if(now){                                                  // еда: обед или ужин
      out.push({type:now.type, start:t, end:now.end, label:now.label});
      t = now.end;
      continue;
    }
    const next = meals.find(m=>m.start > t);
    const limit = next ? Math.min(w.to, next.start) : w.to;
    const end = Math.min(t + cfg.block, limit);
    if(end <= t) break;
    /* Хвост, который заметно короче полного блока, отдельным миниблоком НЕ
       рисуем: владелец видит в нём «огрызок вместо блока». Вливаем его в
       перерыв предыдущего блока - тот просто заканчивается позже. Если
       предыдущего блока нет (работа началась впритык к еде) - оставляем чисто.
       Порог = две трети блока, но не выше самого блока: иначе при коротком
       блоке из настроек разметка исчезла бы целиком. */
    const minTail = Math.min(cfg.block, Math.max(RHY_MIN_BLOCK, Math.ceil(cfg.block*2/3)));
    if(end - t < minTail){
      const prev = out[out.length-1];
      if(prev && prev.type === 'block'){ prev.end = end; prev.brk = end - prev.focusEnd; }
      t = end;
      continue;
    }
    // перерыв живёт ВНУТРИ блока, в его конце. Фокус короче блока ровно на него
    const brk = Math.min(cfg.brk, Math.max(0, (end - t) - RHY_MIN_FOCUS));
    out.push({type:'block', start:t, end, n:++n, brk, focusEnd: end - brk});
    t = end;
  }

  /* Нагрузка блока. Глубокий - в пиковом окне и не в провале, таких максимум
     два: больше тяжёлого в сутки не помещается. В провале - механика. Последний
     блок дня - буфер под то, что прилетит: заполнять его планом нельзя. */
  const peak = peakWindow(), dip = dipWindow();
  const blocks = out.filter(s=>s.type === 'block');
  let deep = 0, mid = 0;
  blocks.forEach((s, i)=>{
    const len = Math.max(1, s.focusEnd - s.start);
    const inDip = !!(dip && cross(s.start, s.focusEnd, dip.from, dip.to) >= len/2);
    const inPeak = !!(peak && cross(s.start, s.focusEnd, peak.from, peak.to) >= len/2);
    s.dip = inDip;
    if(i === blocks.length - 1 && blocks.length > 1){ s.level = 'buf'; s.tag = 'буфер'; return; }
    if(inPeak && !inDip && deep < RHY_MAX_DEEP){ s.level = 'deep'; s.tag = 'глубокий'; deep++; return; }
    if(inDip){ s.level = 'mech'; s.tag = 'механика'; return; }
    s.level = 'mid'; s.tag = (mid++ === 0) ? 'средний' : 'рутина';
  });
  // обед, подводящий к провалу, помечаем - это часть той же физиологии
  out.forEach(s=>{
    if(s.type !== 'lunch' && s.type !== 'dinner') return;
    if(dip && cross(s.start, s.end, dip.from, dip.to) > 0) s.dip = true;
  });
  return out;
}

/* Сколько из фокус-окна блока уже занято задачами и где самая большая дыра.
   Считается на каждый рендер: зависит от событий, в кэш геометрии не лезет. */
function blockFill(dateKey, s){
  const a = s.start, b = s.focusEnd, span = Math.max(0, b - a);
  const busy = [];
  DATA.events.forEach(e=>{
    if(e.date !== dateKey) return;
    const es = tmin(e.start), x1 = Math.max(a, es), x2 = Math.min(b, es + Math.max(0, +e.dur||0));
    if(x2 > x1) busy.push([x1, x2]);
  });
  busy.sort((p,q)=>p[0] - q[0]);
  const merged = [];
  busy.forEach(x=>{
    const last = merged[merged.length-1];
    if(last && x[0] <= last[1]) last[1] = Math.max(last[1], x[1]);
    else merged.push([x[0], x[1]]);
  });
  let taken = 0, cur = a, gap = null;
  merged.forEach(m=>{ taken += m[1] - m[0]; });
  merged.concat([[b, b]]).forEach(m=>{
    if(m[0] - cur > 0 && (!gap || m[0] - cur > gap[1] - gap[0])) gap = [cur, m[0]];
    cur = Math.max(cur, m[1]);
  });
  return {span, taken, free: Math.max(0, span - taken), gap};
}
/* Кэш на день: во время перетаскивания магнит дёргает разметку на каждый
   пиксель, пересобирать её там незачем. Сбрасывается в render() и loadWeek(). */
let rhyCache = new Map();
function rhythmFor(dateKey){
  if(!isDate(dateKey)) return [];
  if(!rhyCache.has(dateKey)) rhyCache.set(dateKey, buildRhythm(dateKey));
  return rhyCache.get(dateKey);
}
function resetRhythm(){ rhyCache = new Map(); }

/* Зоны суток: сетка идёт от 06:00 до полуночи всегда, а границы дня владельца
   показываем заливкой, а не обрезкой шкалы. */
function dayZones(){
  const p = PROFILE || {};
  const top = H0*60, bot = H1*60;
  const out = [];
  const add = (type, a, b, label, tip)=>{
    a = Math.max(a, top); b = Math.min(b, bot);
    if(b - a >= 5) out.push({type, start:a, end:b, label, tip});
  };
  const wake = p.wake ? tmin(p.wake) : null;
  const w = workWindow();
  const ws = w ? w.from : (p.workStart ? tmin(p.workStart) : null);
  const we = w ? w.to : (p.workEnd ? tmin(p.workEnd) : null);
  const sleep = p.sleep ? tmin(p.sleep) : null;

  if(wake != null && wake > top)
    add('pre', top, wake, 'до подъёма',
        'Подъём в ' + hhmm(wake) + ' из настроек. Всё, что выше - ещё ночь');
  /* Утреннее окно рисуют ДВА элемента поверх друг друга: эта зона суток и блок
     renderMorningBlock(). Оба ложатся на один и тот же top с одинаковым z-index, и
     живой замер в браузере показал пересечение подписей в 102 пикселя у шести дней
     из семи. Это и есть то, что владелец назвал «блоки друг на друга наезжают».
     Правка самая дешёвая из возможных: у зоны снимается ПОДПИСЬ, заливка и подсказка
     при наведении остаются. Подписанным на утре остаётся ровно один элемент - блок.
     renderMorningBlock() не трогается вовсе, поэтому ветка защищённого дня
     (воскресенье утро не подписывает) остаётся как была: ноль подписей на утре
     законен, две не законны нигде. */
  /* Подсказка у зоны и у блока теперь ОДНА строка (morningTip). Раньше здесь
     стоял свой текст, и в будни он был физически недостижим: сверху лежит блок
     утра со своей подсказкой, elementFromPoint в середине окна возвращает блок.
     Два разных текста на одном прямоугольнике, один мёртвый. Один текст на оба
     носителя снимает разночтение и на защищённом дне, где блока нет вовсе. */
  if(wake != null && ws != null && ws > wake)
    add('morning', wake, ws, '', morningTip(wake, ws));
  // обед виден фоном и при выключенной разметке блоков: граница суток, как сон
  const rc = rhythmCfg();
  if(!rc.on && rc.lunchDur > 0){
    const la = rc.lunch, lb = Math.min(bot, la + rc.lunchDur);
    if(lb > la && la >= top)
      add('lunch', la, lb, 'обед',
          'Обед ' + hhmm(la) + '-' + hhmm(lb) + ' из настроек. Накрывает провал бдительности: после еды прогулка на свету или NSDR, тяжёлое сюда не ставим');
  }
  if(!rc.on && rc.dinnerDur > 0){
    const da = rc.dinner, db = Math.min(bot, da + rc.dinnerDur);
    if(db > da && da >= top)
      add('dinner', da, db, 'ужин',
          'Ужин ' + hhmm(da) + '-' + hhmm(db) + ' из настроек. За 3-4 часа до сна: позже еда ломает ночь');
  }
  if(we != null){
    const real = (sleep != null && sleep > we && sleep < bot) ? sleep : null;
    const wd = p.windDown ? tmin(p.windDown) : null;
    const wdTip = 'Работа закончена в ' + hhmm(we) +
      (real != null ? ', отбой в ' + hhmm(real) : '') +
      '. Wind-down' + (wd != null ? ' с ' + hhmm(wd) : '') + ': экраны и яркий свет приглушить, тяжёлых разговоров не заводим';
    if(real != null){
      add('wind', we, real, 'wind down', wdTip);
      add('sleep', real, bot, 'сон',
          'Отбой в ' + hhmm(real) + ' из настроек. Задачу сюда положить можно, но предупрежу: за сон платят следующим днём');
    }else{
      add('wind', we, bot, 'wind down', wdTip);
    }
  }
  return out;
}
function sleepZone(){ return dayZones().find(z=>z.type === 'sleep') || null; }

/* ---------- мягкие подсказки: перерыв, еда, сон ---------- */
/* Целиком в перерыве, обеде или ужине - подсказываем, но не блокируем: бывает
   нарочно. Перерыв теперь хвост блока [focusEnd, end], отдельного отрезка нет. */
function restHit(dateKey, startMin, dur){
  const end = startMin + Math.max(0, +dur || 0);
  let hit = null;
  rhythmFor(dateKey).forEach(s=>{
    if(hit) return;
    if((s.type === 'lunch' || s.type === 'dinner') && startMin >= s.start && end <= s.end)
      hit = {kind:s.type, from:s.start, to:s.end};
    else if(s.type === 'block' && s.brk > 0 && startMin >= s.focusEnd && end <= s.end)
      hit = {kind:'break', from:s.focusEnd, to:s.end, n:s.n};
  });
  return hit;
}
function softMsg(ev){
  if(!ev || !isDate(ev.date)) return null;
  const s = tmin(ev.start), dur = Math.max(0, +ev.dur || 0);
  const z = sleepZone();
  if(z && cross(s, s + dur, z.start, z.end) > 0)
    return '⚠ «' + ev.title + '» заходит в зону сна (' + hhmm(z.start) + '-' + hhmm(z.end) +
           '). Не запрещаю, но за это платит следующий день';
  const r = restHit(ev.date, s, dur);
  if(!r) return null;
  const span = hhmm(r.from) + '-' + hhmm(r.to);
  if(r.kind === 'lunch')
    return '⚠ «' + ev.title + '» целиком села в обед (' + span + '). Обед подводит к провалу бдительности, тяжёлое тут не идёт';
  if(r.kind === 'dinner')
    return '⚠ «' + ev.title + '» целиком села в ужин (' + span + '). Ужин за 3-4 часа до сна, позже ломает ночь';
  return '⚠ «' + ev.title + '» целиком села в перерыв блока ' + r.n + ' (' + span +
         '). Эти минуты нужны без экрана, иначе следующий блок стартует с пустой головой';
}
function pushSoft(msgs, ev){
  const m = softMsg(ev);
  if(m){ msgs.push(m); msgs.overlap = true; }
  return msgs;
}

/* ---------- ёмкость и загрузка дня ---------- */
function dayCapacity(){
  if(!PROFILE || !PROFILE.workStart || !PROFILE.workEnd) return null;
  const avail = tmin(PROFILE.workEnd) - tmin(PROFILE.workStart);
  if(avail <= 0) return null;
  const pct = typeof PROFILE.capacityPercent === 'number' ? PROFILE.capacityPercent : 60;
  return {avail, norm: avail * pct / 100, pct};
}
/* минуты, реально падающие в этот день: хвост после полуночи считаем следующему */
function dayLoad(k){
  const prev = addDays(k, -1);
  let total = 0;
  DATA.events.forEach(e=>{
    if(e.kind === 'launch') return;
    const dur = Math.max(0, +e.dur || 0);
    if(e.date === k){
      total += Math.min(dur, Math.max(0, DAY_END - tmin(e.start)));
    }else if(e.date === prev){
      const over = tmin(e.start) + dur - DAY_END;
      if(over > 0) total += Math.min(over, DAY_END);
    }
  });
  return total;
}
function dayCount(k){
  const all = DATA.events.filter(e=>e.date === k);
  return {done: all.filter(e=>e.done).length, total: all.length};
}

/* ---------- «сейчас» ---------- */
function nowMin(){ const n = new Date(); return n.getHours()*60 + n.getMinutes(); }
function currentEvent(){
  const k = iso(new Date()), m = nowMin();
  const live = DATA.events.filter(e=>e.date === k && !e.done && tmin(e.start) <= m && m < tmin(e.start) + (+e.dur||0));
  live.sort((a,b)=>tmin(b.start) - tmin(a.start));
  return live[0] || null;
}
function nextEvent(){
  const k = iso(new Date()), m = nowMin();
  return DATA.events.filter(e=>e.date === k && !e.done && tmin(e.start) > m)
                    .sort((a,b)=>tmin(a.start) - tmin(b.start))[0] || null;
}

/* ---------- рендер ---------- */
function render(){
  if(!$('grid')) return;                       // вкладку успели переключить
  if(!isNarrow() && viewMode !== 'week') viewMode = 'week';   // десктоп: недельная сетка неприкосновенна
  const dayMode = viewMode === 'day';
  if(dayMode){
    if(!isDate(dayCursor)) dayCursor = iso(new Date());
    syncWeekToCursor();
  }
  const root = document.querySelector('.week-root');
  if(root) root.classList.toggle('wk-day1', dayMode);

  const days = visibleDays();
  computeBounds(days);
  resetRhythm();                               // профиль или день могли поменяться
  const todayISO = iso(new Date());

  $('range').textContent = dayMode
    ? `${DOW_RU[dowOf(iso(days[0]))] || ''}, ${days[0].getDate()} ${MON[days[0].getMonth()]}` +
      (iso(days[0]) === todayISO ? ' · сегодня' : '')
    : `${days[0].getDate()} ${MON[days[0].getMonth()].slice(0,3)} - ${days[6].getDate()} ${MON[days[6].getMonth()]}`;
  const vb = $('wk-view');
  if(vb){
    vb.textContent = dayMode ? 'Неделя' : 'День';
    vb.title = dayMode ? 'Показать всю неделю целиком' : 'Показать один день во всю ширину';
  }
  renderGoal();

  // легенда + подсказка «что делаю сейчас»
  const cur = currentEvent(), nxt = nextEvent();
  let nowTxt;
  if(cur) nowTxt = `Сейчас: ${cur.title} (до ${hhmm(tmin(cur.start) + (+cur.dur||0))})`;
  else if(nxt) nowTxt = `Сейчас свободно · дальше в ${nxt.start}: ${nxt.title}`;
  else nowTxt = 'Сейчас свободно, на сегодня задач больше нет';
  /* кнопка фокуса при чипе «Сейчас»: цель - текущая задача, а если сейчас
     свободно, то ближайшая следующая. В режиме дня чип спрятан стилями,
     поэтому там вход в фокус живёт на крупной карточке (renderFocus) */
  const fzT = cur || nxt;
  $('legend').innerHTML =
    `<span class="wk-nowchip" id="wk-nowchip"></span>`
    + (fzT ? `<button type="button" class="wk-fzchip" id="wk-nowfocus"
         title="${esc('Фокус на задаче «' + fzT.title + '»: таймер на весь экран')}">▶ Фокус</button>` : '')
    + Object.keys(DATA.tracks).map(k=>{
        const v = DATA.tracks[k] || {};
        return `<span><i style="background:${color(v.color)}"></i>${esc(v.label||k)}</span>`;
      }).join('')
    + `<span class="wk-lgd" style="border-left:1px solid var(--bd);padding-left:14px">
         <b style="color:var(--txt)">Сплошной блок</b> = твоё время ·
         <b style="color:var(--txt)">▶ пунктир</b> = только запустить ·
         <b style="color:var(--txt)">▸ лента сверху</b> = идёт само</span>`
    + `<span class="hint">${dayMode
         ? 'свайп влево-вправо или стрелки = соседний день · держи палец на блоке = перенести · тяни за низ = длительность'
         : 'тянуть = перенести · тянуть за низ = длительность · двойной клик по пустому = новая задача · на телефоне держи палец на блоке'}</span>`
    + `<button type="button" class="wk-helpbtn" id="wk-helpbtn" title="Что значат блоки и как ими управлять">?</button>`;
  /* Пояснения показываются только по «?»: шапка обязана быть тонкой, календарь - главным
     (причина - решение владельца) */
  try{ $('legend').classList.toggle('wk-help-on', localStorage.getItem('wk-help-open') === '1'); }catch(e){}
  const hb = $('wk-helpbtn');
  if(hb) hb.addEventListener('click', ()=>{
    const on = $('legend').classList.toggle('wk-help-on');
    try{ localStorage.setItem('wk-help-open', on ? '1' : '0'); }catch(e){}
  });
  const chip = $('wk-nowchip');
  if(chip){ chip.textContent = nowTxt; chip.title = nowTxt; }
  if($('wk-nowfocus') && fzT) $('wk-nowfocus').addEventListener('click', ()=>fzOpen(fzT.id));

  const WD = ['ПН','ВТ','СР','ЧТ','ПТ','СБ','ВС'];
  const cap = dayCapacity();

  // строка дней: загрузка часов, валидатор ёмкости, счётчик сделанного
  $('dayrow').innerHTML = '<div class="corner"></div>' + days.map(d=>{
    const k = iso(d);
    const i = (d.getDay()+6)%7;               // в режиме дня индекс в массиве не равен дню недели
    const load = dayLoad(k);
    const c = dayCount(k);
    const prot = isProtectedDay(k);
    const cls = (k === todayISO ? 'today' : (k < todayISO ? 'past' : '')) + (prot ? ' wk-protday' : '');
    const over = !!(cap && load > cap.norm);
    const loadTxt = load ? hoursTxt(load) : '';
    const title = over
      ? ` title="Перегруз: запланировано ${(load/60).toFixed(1)} ч, норма ${(cap.norm/60).toFixed(1)} ч (${cap.pct}% от ${(cap.avail/60).toFixed(1)} ч рабочего дня из настроек)"`
      : (prot ? ` title="Защищённый день из настроек"` : '');
    const cntCls = c.total && c.done === c.total ? ' all' : '';
    const cnt = c.total
      ? `<div class="dcount${cntCls}" title="Сделано ${c.done} из ${c.total}">сделано ${c.done} из ${c.total}</div>`
      : `<div class="dcount"></div>`;
    return `<div class="day ${cls}"><div class="dw">${WD[i]}</div><div class="dn">${d.getDate()}</div>
            <div class="load${over?' over':''}"${title}>${loadTxt}</div>${cnt}</div>`;
  }).join('');

  // сетка
  let html = '<div class="hours">' + [...Array(H1-H0)].map((_,i)=>
      `<div><span>${pad(H0+i)}:00</span></div>`).join('') + '</div>';

  const curId = cur ? cur.id : null;
  const zones = renderZones();                 // от дня не зависят, считаем один раз
  days.forEach(d=>{
    const k = iso(d);
    const past = k < todayISO ? 'past' : '';
    const prot = isProtectedDay(k) ? ' wk-prot' : '';
    const R = renderRhythm(k);
    /* Порядок = стопка слоёв. Ниже всех часовые линии и зоны суток, над ними
       фон блоков, над ним поверхность «поставить сюда», дальше пик и
       тренировка, потом сами задачи, и уже поверх задач - тонкие полосы
       перерывов, чтобы задача на два блока не съедала паузу между ними. */
    html += `<div class="col ${past}${prot}" data-date="${esc(k)}"` +
            (prot ? ` title="Защищённый день: ${esc(DOW_RU[dowOf(k)]||'')} закрыт в настройках"` : '') + '>' +
            [...Array(H1-H0)].map((_,i)=>`<div class="slot" data-h="${H0+i}"></div>`).join('') +
            zones + R.bands + R.fills +
            renderPeak() + renderTraining(k) + renderMorningBlock(k) +
            renderEvents(k, curId) + R.breaks +
            (k === todayISO ? nowLine() : '') +
            '</div>';
  });
  $('grid').innerHTML = html;
  renderAuto(days);

  // бэклог: активные в полосе, отложенные за счётчиком, просроченный TTL всплывает
  safePart('бэклог', renderBacklog, 'backlog');

  safePart('решения', renderDecideBar, 'wk-decidebar');
  safePart('задачи цикла', renderProjection, 'wk-projection');
  safePart('следующий шаг', renderNextStep, 'wk-nextstep');
  safePart('отмена', renderUndoBar, 'wk-undobar');
  safePart('фокус', ()=>renderFocus(iso(days[0]), dayMode), 'wk-focus');
  safePart('обработчики', wire, null);
}

/* Гард на КЛАСС, а не на одну строку. Один упавший рендер хвоста раньше
   обрывал всю цепочку молча: полоса оставалась пустой либо держала разметку
   ЧУЖОЙ недели с прошлого прохода, и владелец видел это как «движок ничего не
   показывает». Теперь падение локально, видно глазами и лежит в консоли. */
function safePart(name, fn, boxId){
  try{
    fn();
  }catch(err){
    console.error('[неделя] блок «' + name + '» упал:', err);
    const box = boxId ? $(boxId) : null;
    if(box) box.innerHTML = '<b>' + esc(name) + '</b><span class="wk-prj-note">блок не построился: '
                          + esc(String(err && err.message || err)) + '. Подробности в консоли</span>';
  }
}


/* ================== ПРОЕКЦИЯ ЗАДАЧ ЦИКЛА В НЕДЕЛЮ ==================
   Методология владельца: «в понедельник открыть 12wy/current.md, выписать тактики,
   попадающие на эту неделю, перенести в week.md как конкретные действия»
   (mastery/planning/СИСТЕМА.md:62). Здесь это сделано ЧТЕНИЕМ, а не копией.

   Почему проекция, а не перенос. Копия названия задачи в sprint.json живёт своей
   жизнью: переименовал задачу в цикле - в неделе висит старое имя; закрыл задачу -
   строка в неделе остаётся. Проекция читает goals-cycle.json на каждый рендер и не
   пишет туда ничего, поэтому расхождение невозможно по конструкции, done гасит
   строку сам, а идемпотентность достаётся бесплатно.

   ЗАПИСЬ появляется ровно в одном месте: когда владелец сам тянет строку в
   календарь - тогда рождается событие с полем taskId. Пакетного переноса и кнопки
   «взять все задачи» нет намеренно.

   Принадлежность задачи неделе считается ПО ДАТАМ, а не по одному номеру: календарная
   неделя движка начинается с понедельника, а неделя цикла - со дня старта цикла. Две
   сетки разъезжаются на день, и если брать один номер, часть задач теряется. Поэтому
   для каждого из семи открытых дней считается свой номер недели цикла, и задача
   берётся, если её weeks пересекаются с этим набором. */

function cycleStartDate(){
  const c = (GOALS && GOALS.cycle) || {};
  return isDate(c.start) ? parseISO(c.start) : null;
}
/* номера недель цикла, накрывающие открытые семь дней */
function cycleWeeksOfOpenWeek(){
  const start = cycleStartDate();
  const total = ((GOALS && GOALS.cycle && +GOALS.cycle.weeks) || 0);
  const out = new Set();
  if(!start || !total) return out;
  weekKeys().forEach(k=>{
    const diff = Math.round((parseISO(k) - start) / 86400000);
    if(diff < 0) return;
    const idx = Math.floor(diff / 7) + 1;
    if(idx >= 1 && idx <= total) out.add(idx);
  });
  return out;
}
/* задачи целей, попадающие на открытую неделю и ещё не закрытые */
function projectedTasks(){
  const weeks = cycleWeeksOfOpenWeek();
  if(!weeks.size || !GOALS || !Array.isArray(GOALS.goals)) return [];
  const out = [];
  GOALS.goals.forEach(g=>{
    (g.tasks || []).forEach(t=>{
      if(t.done === true) return;
      const w = Array.isArray(t.weeks) ? t.weeks : [];
      if(!w.some(n=>weeks.has(+n))) return;
      out.push({goal:g, task:t});
    });
  });
  return out;
}
/* сколько действий уже стоит под задачей в открытой неделе */
function actionsForTask(taskId){
  const keys = new Set(weekKeys());
  return DATA.events.filter(e=>e.taskId === taskId && keys.has(e.date));
}
function taskById(taskId){
  if(!GOALS || !Array.isArray(GOALS.goals)) return null;
  for(const g of GOALS.goals){
    for(const t of (g.tasks || [])){
      if(t.id === taskId) return {goal:g, task:t};
    }
  }
  return null;
}

/* Полоса задач цикла СВЁРНУТА по умолчанию. Прецедент: 16 карточек
   съели верхнюю половину экрана, владелец дословно приведён ответ владельца. Календарь первым, карточки по клику; выбор помнит
   localStorage этого браузера и переживает перезагрузку. */
function prjOpen(){ try{ return localStorage.getItem('wk-prj-open') === '1'; }catch(e){ return false; } }
function togglePrj(){
  try{ localStorage.setItem('wk-prj-open', prjOpen() ? '0' : '1'); }catch(e){}
  renderProjection(); wireProjection();
}
function renderProjection(){
  const box = $('wk-projection');
  if(!box) return;
  const weeks = [...cycleWeeksOfOpenWeek()].sort((a,b)=>a-b);
  const rows = projectedTasks();
  if(!rows.length){
    const c = (GOALS && GOALS.cycle) || {};
    /* weekKeys() отдаёт УЖЕ готовые ISO-строки (см. её тело: `return iso(d)`).
       Второй iso() поверх строки валил `d.getFullYear is not a function`, и
       исключение обрывало render() ровно на той ветке, ради которой полоса и
       строилась: «задач цикла на эту неделю нет». Сравниваем строку со строкой. */
    const lastDay = weekKeys().slice(-1)[0];
    box.innerHTML = isDate(c.start) && lastDay < c.start
      ? `<b>Задачи цикла</b><span class="wk-prj-note">цикл стартует ${esc(shortDate(c.start))}, на эту неделю задач цикла ещё нет</span>`
      : `<b>Задачи цикла</b><span class="wk-prj-note">на эту неделю незакрытых задач цикла нет</span>`;
    return;
  }
  if(!prjOpen()){
    const withActs = rows.filter(({task})=>actionsForTask(task.id).length).length;
    box.innerHTML = `<b>Задачи цикла</b>` +
      `<span class="wk-prj-note">неделя цикла ${weeks.join(', ')} · задач ${rows.length}, с действиями ${withActs}</span>` +
      `<span class="chip wk-prj-toggle" title="Показать карточки, чтобы тянуть их в календарь">развернуть ▾</span>`;
    const tg = box.querySelector('.wk-prj-toggle');
    if(tg) tg.onclick = togglePrj;
    return;
  }
  box.innerHTML = `<b>Задачи цикла</b>` +
    `<span class="wk-prj-note" title="Номер недели цикла считается по датам семи открытых дней">неделя цикла ${weeks.join(', ')} · тяни строку в календарь, чтобы завести действие</span>` +
    `<span class="chip wk-prj-toggle">свернуть ▴</span>` +
    rows.map(({goal, task})=>{
      const n = actionsForTask(task.id).length;
      const tip = `${goal.title} -> ${task.title}. Действий в этой неделе: ${n}. ` +
                  `Тяни в календарь, чтобы завести действие с привязкой к этой задаче`;
      return `<span class="chip wk-prj-chip${n?'':' wk-prj-empty'}" draggable="true" ` +
             `data-task-id="${esc(task.id)}" title="${esc(tip)}">` +
             `<small class="wk-prj-goal">${esc(goal.title)}</small>${esc(task.title)}` +
             `<b class="wk-prj-count">${n}</b></span>`;
    }).join('');
  const tg = box.querySelector('.wk-prj-toggle');
  if(tg) tg.onclick = togglePrj;
}

function wireProjection(){
  document.querySelectorAll('#wk-projection .wk-prj-chip').forEach(ch=>{
    ch.addEventListener('dragstart', e=>e.dataTransfer.setData('taskid', ch.dataset.taskId));
  });
}

/* Запись рождается ТОЛЬКО здесь: владелец сам притащил конкретную строку */
function placeTask(taskId, col, clientY){
  const found = taskById(taskId);
  if(!found) return notify('задача цикла не найдена: ' + taskId, 'err');
  const m = timeAt(col, clientY);
  const dur = clampDur(60, false);
  const blocked = slotBlocked(col.dataset.date, m, dur);
  if(blocked) return notify(blocked, 'err');
  const ev = {id:uid('e'), kind:'active', title:found.task.title, date:col.dataset.date,
              start:hhmm(m), dur, est:dur, who:'владелец', taskId:taskId};
  DATA.events.push(ev);
  const msgs = [];
  pushOverlap(msgs, ev);
  save('действие под задачей цикла «' + found.task.title + '»'); render();
  tell(msgs);
}

/* ================== ЦЕЛЬ НЕДЕЛИ: ВЫЧИСЛЯЕТСЯ, А НЕ ХРАНИТСЯ ==================
   Северная задача по фокусирующему вопросу Келлера (mastery/planning/СИСТЕМА.md:63):
   «какое одно дело по цели номер один на эту неделю делает остальное проще». Отсюда
   правило отбора: первая незакрытая задача ПЕРВОЙ цели, чьи weeks пересекают открытую
   неделю. Порядок задач внутри цели и есть порядок зависимости, его задавал владелец.

   Хранимая строка осталась ОВЕРРАЙДОМ по ключу понедельника недели (DATA.sprintGoals).
   Так цель не протухает при правке задачи, а написанное руками не теряется. Прежний
   текст недели живёт оверрайдом с ключом понедельника. */
function weekKeyOfOpenWeek(){ return iso(weekStart); }
function computedGoal(){
  const weeks = cycleWeeksOfOpenWeek();
  if(!weeks.size || !GOALS || !Array.isArray(GOALS.goals) || !GOALS.goals.length) return null;
  const g = GOALS.goals[0];
  const t = (g.tasks || []).find(x=>x.done !== true &&
              (Array.isArray(x.weeks) ? x.weeks : []).some(n=>weeks.has(+n)));
  return t ? {goal:g, task:t} : null;
}
function goalOverride(){
  const map = (DATA && DATA.sprintGoals && typeof DATA.sprintGoals === 'object') ? DATA.sprintGoals : {};
  const v = map[weekKeyOfOpenWeek()];
  return (typeof v === 'string' && v.trim()) ? v.trim() : '';
}

/* ================== СЛЕДУЮЩИЙ ШАГ ==================
   владелец обозначил приоритет явно.
   Значит движок обязан назвать ОДНО конкретное действие по имени, а не показать
   сетку и промолчать. Та же строка печатается ритуалом daily_open.py. */
/* Шаг считается ПО ОТКРЫТОЙ неделе, а не по сегодняшнему дню всегда.
   Владелец, планирующий неделю, читал здесь «10:00 · Операционка» из другого дня и мог принять подсказку про сегодня за подсказку про ту неделю.
   Правило: сегодня внутри открытых семи дней - показываем ближайшее незакрытое
   действие сегодня; открыта чужая неделя - показываем первое незакрытое
   действие ЭТОЙ недели, а если действий нет, первую задачу цикла без действий. */
function nextStep(){
  const keys = weekKeys();
  const todayK = iso(new Date());
  const todayInWeek = keys.indexOf(todayK) >= 0;
  const scope = todayInWeek ? [todayK] : keys;
  const evs = DATA.events
    .filter(e=>scope.indexOf(e.date) >= 0 && e.done !== true && /^\d{2}:\d{2}$/.test(String(e.start||'')))
    .sort((a,b)=>(a.date === b.date ? tmin(a.start) - tmin(b.start) : (a.date < b.date ? -1 : 1)));
  if(evs.length){
    const when = todayInWeek ? evs[0].start : `${shortDate(evs[0].date)} ${evs[0].start}`;
    return {kind:'event', text:`${when} · ${evs[0].title}`, ev:evs[0], scope: todayInWeek ? 'today' : 'week'};
  }
  const rows = projectedTasks();
  const bare = rows.find(r=>!actionsForTask(r.task.id).length);
  if(bare) return {kind:'task', scope:'week',
                   text:`${bare.task.title} (${bare.goal.title}) - ни одного действия в этой неделе`};
  if(rows.length) return {kind:'task', scope:'week', text:`${rows[0].task.title} (${rows[0].goal.title})`};
  return {kind:'none', scope: todayInWeek ? 'today' : 'week', text:''};
}
function renderNextStep(){
  const box = $('wk-nextstep');
  if(!box) return;
  const s = nextStep();
  const label = (s && s.scope === 'week') ? 'Следующий шаг на этой неделе:' : 'Следующий шаг:';
  box.innerHTML = (s && s.kind !== 'none')
    ? `<b>${label}</b> <span class="wk-ns-text">${esc(s.text)}</span>` +
      (s.kind === 'task' ? `<small> - вытяни строку из полосы задач цикла в календарь</small>` : '')
    : `<b>${label}</b> <span class="wk-ns-text">${
        (s && s.scope === 'week') ? 'на этой неделе незакрытых действий нет' : 'на сегодня незакрытых действий нет'
      }</span>`;
}

/* цель спринта: читается И правится прямо из шапки */
function renderGoal(){
  const box = $('goal');
  if(!box) return;
  /* Порядок такой: оверрайд недели -> вычисленная северная задача -> старое поле
     sprintGoal (оно одно на все недели и осталось только ради совместимости).
     Хранимого дубля вычисленного текста не создаётся: он протух бы при первой же
     правке задачи цели. */
  const over = goalOverride();
  const comp = over ? null : computedGoal();
  const legacy = typeof DATA.sprintGoal === 'string' ? DATA.sprintGoal.trim() : '';
  const g = over || (comp ? comp.task.title : '') || (goalOverride() ? '' : (cycleWeeksOfOpenWeek().size ? '' : legacy));
  const src = over ? 'написана руками на эту неделю'
            : comp ? `вычислена по фокусирующему вопросу: первая незакрытая задача цели «${comp.goal.title}» на эту неделю (${comp.task.id})`
            : 'старое поле цели, к неделе не привязано';
  box.innerHTML = g
    ? `<span class="gtxt" title="${esc(g + ' · ' + src)}"><b>Цель недели:</b> ${esc(g)}${comp?` <small class="wk-goalsrc">${esc(comp.task.id)}</small>`:''}</span> <button type="button" class="wk-goaledit" id="wk-goaledit" title="Переписать цель именно этой недели">✎</button>`
    : `<button type="button" class="wk-goaladd" id="wk-goaledit">+ Цель недели</button>`;
  const b = $('wk-goaledit');
  if(b) b.addEventListener('click', openGoalEdit);
  const gt = box.querySelector('.gtxt');
  if(gt) gt.addEventListener('click', ()=>box.classList.toggle('full'));
}

/* ---------- «требует решения»: флаг обязан быть виден, а не лежать в файле ---------- */
function stuckList(){ return DATA.events.filter(e=>e.needsDecision === true); }
function renderDecideBar(){
  const box = $('wk-decidebar');
  if(!box) return;
  const stuck = stuckList();
  if(!stuck.length){ box.className = 'wk-decidebar'; box.innerHTML = ''; return; }
  box.className = 'wk-decidebar on';
  box.innerHTML = `<b>⚠ Ждут решения: ${stuck.length}</b>` +
    stuck.slice(0,4).map(e=>
      `<button type="button" class="wk-dchip" data-id="${esc(e.id)}">${esc(e.title)} · ${esc(shortDate(e.date))}</button>`
    ).join('') +
    (stuck.length > 4 ? `<span class="more">и ещё ${stuck.length-4}</span>` : '') +
    `<span class="more">переносов 3+, движок их больше не двигает</span>`;
  box.querySelectorAll('.wk-dchip').forEach(b=>
    b.addEventListener('click', ()=>openPanel(b.dataset.id)));
}

/* ---------- крупная карточка «что сейчас» для режима одного дня ---------- */
function renderFocus(dayKey, dayMode){
  const box = $('wk-focus');
  if(!box) return;
  if(!dayMode){ box.className = 'wk-focus'; box.innerHTML = ''; return; }
  const todayK = iso(new Date());
  let e = null, label = '';
  if(dayKey === todayK){
    e = currentEvent();
    if(e) label = 'Сейчас';
    else { e = nextEvent(); if(e) label = 'Дальше в ' + e.start; }
  }else{
    e = DATA.events.filter(x=>x.date === dayKey && !x.done)
                   .sort((a,b)=>tmin(a.start) - tmin(b.start))[0] || null;
    if(e) label = 'Первое дело дня, ' + e.start;
  }
  if(!e){
    box.className = 'wk-focus on empty';
    box.innerHTML = `<div class="lb">${dayKey === todayK ? 'На сегодня задач больше нет' : 'На этот день задач нет'}</div>
      <div class="acts"><button type="button" class="ok" id="wk-fadd">+ Поставить задачу</button></div>`;
    $('wk-fadd').addEventListener('click', ()=>openQuickAdd({date:dayKey}));
    return;
  }
  const dur = +e.dur||0;
  const end = tmin(e.start) + dur;
  const c = color((DATA.tracks[e.track]||{}).color);
  const tr = (DATA.tracks[e.track]||{}).label || e.track || '';
  box.className = 'wk-focus on' + (e.needsDecision ? ' decide' : '');
  box.innerHTML =
    `<div class="lb"><i style="background:${c}"></i>${esc(label)}${e.done ? ' · сделано' : ''}${
      e.needsDecision ? ' · <b>требует решения</b>' : ''}</div>
     <div class="ttl">${esc(e.title)}</div>
     <div class="sub">${esc(e.start)} - ${hhmm(end % DAY_END)} · ${hoursTxt(dur)}${tr ? ' · ' + esc(tr) : ''}${
       e.kind === 'launch' ? ' · ▶ только запустить' : ''}</div>
     <div class="acts">
       <button type="button" class="ok" id="wk-fdone">${e.done ? 'Вернуть в работу' : 'Готово'}</button>
       ${e.done ? '' : '<button type="button" class="fz" id="wk-ffocus">Фокус</button>'}
       <button type="button" class="op" id="wk-fopen">Открыть карточку</button>
     </div>`;
  $('wk-fdone').addEventListener('click', ()=>setDone(e.id, false));
  if($('wk-ffocus')) $('wk-ffocus').addEventListener('click', ()=>fzOpen(e.id));
  $('wk-fopen').addEventListener('click', ()=>openPanel(e.id));
}

/* Зоны суток заливкой: до подъёма / утро вне работы / wind down / сон.
   Фон, кликов не ловит, подпись жмётся к правому краю, чтобы не спорить с
   названиями задач (они прижаты влево). */
function renderZones(){
  const bandTop = H0*60;
  return dayZones().map(z=>{
    const top = (z.start - bandTop)/60*HH, h = (z.end - z.start)/60*HH;
    if(h < 4) return '';
    // зона, обрезанная краем сетки, не показывает диапазон-обрезок:
    const span = z.end >= DAY_END
      ? 'с ' + hhmm(z.start)
      : (z.start <= H0*60 ? 'до ' + hhmm(z.end) : hhmm(z.start) + '-' + hhmm(z.end));
    /* Пустая подпись = зона рисует только заливку. Так снят наезд подписей на
       утреннем окне: там подписан ровно один элемент, блок утра. Подсказка при
       наведении остаётся у зоны всегда, смысл окна не теряется */
    return `<div class="wk-zone wk-z-${z.type}" style="top:${top}px;height:${h}px" title="${esc(z.tip)}">` +
           (z.label ? `<span>${esc(z.label)} · ${span}</span>` : '') + `</div>`;
  }).join('');
}

/* Пояснение нагрузки блока - идёт и в подпись, и в подсказку */
const LEVEL_TIP = {
  deep: 'Глубокий: попадает в пиковое окно. Сюда весь запас тяжёлого - съёмка, решения, то что требует головы. Таких в день реально один-два',
  mech: 'Механика: блок сидит в провале бдительности, он приходит через 6-8 часов после подъёма. Сюда только то, что не требует головы - разбор почты, рутина',
  mid:  'Средняя нагрузка: голова вернулась, но не на пик. Производство, сборка, работа по готовому плану, операционка',
  buf:  'Буфер: последний блок дня держим пустым под то, что прилетит. Если день прошёл чисто - закрытие и разбор',
};

/* Разметка рабочего окна: блоки, внутри каждого хвост-перерыв, обед и ужин.
   Возвращает ТРИ слоя, у них разная высота в стопке:
     bands  - фон под задачами (подписи, заливка, номер блока)
     fills  - «поставить сюда» на свободной части фокуса, кликается
     breaks - тонкая полоса перерыва ПОВЕРХ задач: задача на два блока не
              должна визуально затирать паузу между ними */
function renderRhythm(dateKey){
  const segs = rhythmFor(dateKey);
  const layers = {bands:'', fills:'', breaks:''};
  if(!segs.length) return layers;
  const bandTop = H0*60, bandBot = H1*60;
  const y = m => (m - bandTop)/60*HH;
  const vis = (a, b) => Math.min(b, bandBot) - Math.max(a, bandTop) >= 4;

  segs.forEach(s=>{
    if(!vis(s.start, s.end)) return;
    const top = y(Math.max(s.start, bandTop));
    const h = (Math.min(s.end, bandBot) - Math.max(s.start, bandTop))/60*HH;
    const span = hhmm(s.start) + '-' + hhmm(s.end);
    const mins = s.end - s.start;

    if(s.type === 'lunch' || s.type === 'dinner'){
      const tip = s.label + ' ' + span + ' · ' + mins + ' мин. Без экрана и без задач' +
        (s.type === 'lunch'
          ? (s.dip ? '. Обед подводит к провалу бдительности: прогулка на свету или NSDR тут работают лучше кофе'
                   : '. Крупный приём еды в середине дня, не вечером')
          : '. За 3-4 часа до сна, позже ломает ночь');
      layers.bands += `<div class="wk-seg wk-s-meal wk-s-${s.type}" style="top:${top}px;height:${h}px" title="${esc(tip)}">` +
                      `<span>${esc(s.label)} <small>${span}</small></span></div>`;
      return;
    }
    // блок. Подпись = ПОЛНОЕ окно блока (09:00-10:30), а не окно фокуса:
    // перерыв живёт внутри и показан полоской у нижнего края, отдельной строкой
    // «перерыв N мин» его больше не рисуем
    const f = blockFill(dateKey, s);
    const focus = hhmm(s.start) + '-' + hhmm(s.focusEnd);
    const load = f.taken > 0
      ? 'занято ' + f.taken + ' из ' + f.span + ' мин фокуса, свободно ' + f.free
      : 'фокус ' + f.span + ' мин свободен целиком';
    const tip = 'Блок ' + s.n + ' · ' + span + ' · ' + mins + ' мин целиком: фокус ' + focus +
      (s.brk > 0 ? ' и перерыв ' + hhmm(s.focusEnd) + '-' + hhmm(s.end) + ' внутри самого блока' : '') +
      '. ' + (LEVEL_TIP[s.level] || '') + '. Сейчас ' + load +
      (f.free >= DUR_MIN ? '. Клик по свободному месту поставит сюда задачу на окно фокуса' : '');
    layers.bands +=
      `<div class="wk-seg wk-s-block lv-${s.level}${f.taken > 0 ? ' busy' : ''}" style="top:${top}px;height:${h}px" title="${esc(tip)}">
        <span class="wk-bnum">Блок ${s.n}<i>${esc(s.tag || '')}</i> <small>${span}</small></span>
        <span class="wk-bsub">${f.taken > 0 ? 'занято ' + f.taken + ' из ' + f.span + ' мин фокуса, свободно ' + f.free : 'фокус ' + f.span + ' мин · перерыв ' + s.brk}</span>
      </div>`;

    // перерыв внутри блока - верхний слой, поверх задач
    if(s.brk > 0 && vis(s.focusEnd, s.end)){
      const bt = y(s.focusEnd), bh = (s.end - s.focusEnd)/60*HH;
      layers.breaks += `<div class="wk-brk" style="top:${bt}px;height:${bh}px"></div>`;
    }

    // свободное место в фокусе: кликабельная поверхность «поставить сюда»
    if(f.gap && f.gap[1] - f.gap[0] >= DUR_MIN && !isProtectedDay(dateKey)){
      const g0 = f.gap[0], g1 = f.gap[1], dur = g1 - g0;
      const gt = y(g0), gh = (g1 - g0)/60*HH;
      const whole = dur >= f.span;
      layers.fills +=
        `<button type="button" class="wk-fill${gh < 26 ? ' tiny' : ''}" style="top:${gt}px;height:${gh}px"
           data-date="${esc(dateKey)}" data-start="${g0}" data-dur="${dur}"
           title="${esc('Поставить задачу на ' + hhmm(g0) + '-' + hhmm(g1) + ' (' + dur + ' мин' +
                 (whole ? ', всё окно фокуса блока ' + s.n : ' - свободный кусок блока ' + s.n) + ')')}">
           <span>+ поставить сюда <small>${hhmm(g0)}-${hhmm(g1)} · ${dur} мин</small></span></button>`;
    }
  });
  return layers;
}

function renderPeak(){
  const p = peakWindow();
  if(!p) return '';
  const top = (Math.max(p.from, H0*60) - H0*60)/60*HH;
  const h = (Math.min(p.to, H1*60) - Math.max(p.from, H0*60))/60*HH;
  if(h <= 0) return '';
  return `<div class="wk-peak" style="top:${top}px;height:${h}px" title="Пиковое окно ${hhmm(p.from)}-${hhmm(p.to)} из настроек"><span>пик</span></div>`;
}
function renderTraining(k){
  const t = trainingFor(k);
  if(!t) return '';
  /* Утреннее окно подъём-работа рисуется единым блоком «утро» (см. renderMorningBlock):
     тренировка внутри него отдельно не дублируется. Просьба владельца:
     «пометь весь слот утра одним блоком» - один блок, три активности. */
  const p = PROFILE || {};
  const wake = p.wake ? tmin(p.wake) : null, ws = p.workStart ? tmin(p.workStart) : null;
  if(wake != null && ws != null && t.start >= wake && t.end <= ws) return '';
  const top = (Math.max(t.start, H0*60) - H0*60)/60*HH;
  const h = Math.max(14, (Math.min(t.end, H1*60) - Math.max(t.start, H0*60))/60*HH - 2);
  if(h <= 0) return '';
  return `<div class="wk-train" style="top:${top}px;height:${h}px" title="Тренировка из настроек, слот защищён">🏋 Тренировка<br><small>${hhmm(t.start)}-${hhmm(t.end)}</small></div>`;
}
/* Единственный текст подсказки утреннего окна. Носителей два (зона суток и блок),
   и оба берут строку отсюда: разных текстов на одном прямоугольнике больше нет */
function morningTip(wake, ws){
  return `Утро вне работы ${hhmm(wake)}-${hhmm(ws)}: своё, не рабочее. ` +
         `Рабочие блоки сюда не ставятся`;
}
function renderMorningBlock(k){
  const p = PROFILE || {};
  const wake = p.wake ? tmin(p.wake) : null, ws = p.workStart ? tmin(p.workStart) : null;
  if(wake == null || ws == null || ws <= wake) return '';
  if(isProtectedDay(k)) return '';
  const top = (Math.max(wake, H0*60) - H0*60)/60*HH;
  const h = Math.max(14, (Math.min(ws, H1*60) - Math.max(wake, H0*60))/60*HH - 2);
  if(h <= 0) return '';
  return `<div class="wk-train wk-morning" style="top:${top}px;height:${h}px" ` +
         `title="${esc(morningTip(wake, ws))}">` +
         `Утро вне работы<br><small>${hhmm(wake)}-${hhmm(ws)}</small></div>`;
}

/* Связь действия с задачей цели видна прямо на карточке, а не только в файле:
   без этого поле taskId существует, а владелец о связи не знает */
function taskLabel(e, compact){
  if(!e.taskId) return '';
  const f = taskById(e.taskId);
  if(!f) return `<span class="ev-task" title="Задача цикла ${esc(e.taskId)} не найдена в целях">↳ ${esc(e.taskId)}</span>`;
  return `<span class="ev-task" title="Цель: ${esc(f.goal.title)} · Задача: ${esc(f.task.title)} (${esc(f.task.id)})">↳ ${esc(compact ? f.task.id : f.goal.title)}</span>`;
}

function renderEvents(dateKey, curId){
  const evs = DATA.events.filter(e=>e.date === dateKey).sort((a,b)=>tmin(a.start) - tmin(b.start));
  // раскладка пересечений в колонки, как в Google Calendar (без записи в данные)
  const lanes = [], laneOf = new Map();
  evs.forEach(e=>{
    const s = tmin(e.start), en = s + (+e.dur||0);
    let lane = lanes.findIndex(L=>L.every(o=>tmin(o.start) + (+o.dur||0) <= s || tmin(o.start) >= en));
    if(lane < 0){ lanes.push([e]); lane = lanes.length-1; } else lanes[lane].push(e);
    laneOf.set(e.id, lane);
  });
  const n = Math.max(lanes.length, 1);
  const gridEnd = H1*60;
  // кто с кем пересекается: наложение должно быть видно, а не только в тосте
  const clash = new Set();
  evs.forEach(a=>{
    const as = tmin(a.start), ae = as + (+a.dur||0);
    evs.forEach(b=>{
      if(b === a) return;
      const bs = tmin(b.start), be = bs + (+b.dur||0);
      if(be > as && bs < ae && ae > as && be > bs) clash.add(a.id);
    });
  });

  const own = evs.map(e=>{
    const dur = Math.max(0, +e.dur||0);
    const s = tmin(e.start), top = (s - H0*60)/60*HH;
    const fullH = dur/60*HH - 2;
    const maxH = Math.max(16, (gridEnd - s)/60*HH - 2);
    const clipped = fullH > maxH + 1;
    const h = Math.max(Math.min(fullH, maxH), 16);
    const c = color((DATA.tracks[e.track]||{}).color);
    const w = 100/n, left = laneOf.get(e.id)*w;
    const compact = h < 34;
    const isL = e.kind === 'launch';
    const style = isL
      ? `top:${top}px;height:20px;left:calc(${left}% + 2px);width:calc(${w}% - 8px);border-color:${c};color:${c}`
      : `top:${top}px;height:${h}px;background:${c};left:calc(${left}% + 2px);width:calc(${w}% - 8px)`;
    const end = s + dur;
    const ovl = clash.has(e.id), dec = e.needsDecision === true;
    const tip = `${esc(e.title)} · ${esc(e.start)}-${hhmm(end % DAY_END)}${end > DAY_END ? ' (следующий день)' : ''}` +
      (ovl ? ' · ⚠ наложение с другой задачей' : '') +
      (dec ? ' · ⚠ требует решения: переносов ' + esc(e.moved == null ? '3+' : e.moved) : '');
    return `<div class="ev ${isL?'launch':''} ${e.done?'done':''} ${e.fixed?'fixed':''} ${clipped?'wk-clip':''} ${e.id===curId?'wk-cur':''} ${ovl?'wk-ovl':''} ${dec?'wk-decide':''} ${fz && fz.id===e.id?'wk-infocus':''}"
        style="${style}" data-id="${esc(e.id)}" title="${tip}">
        <span class="t">${dec?'⚠ ':''}${esc(e.title)}</span>
        ${taskLabel(e, compact)}
        ${(compact||isL)?'':`<span class="m">${esc(e.start)} · ${hoursTxt(dur)}${e.actual?' · факт ' + hoursTxt(+e.actual):''}</span>`}
        ${isL?'':'<div class="rz"></div>'}</div>`;
  });

  // хвост вчерашнего события, переехавший через полночь
  const prev = addDays(dateKey, -1);
  DATA.events.forEach(e=>{
    if(e.date !== prev) return;
    const over = tmin(e.start) + (+e.dur||0) - DAY_END;
    if(over <= 0) return;
    const c = color((DATA.tracks[e.track]||{}).color);
    const h = H0 === 0 ? Math.max(16, Math.min(over, (H1-H0)*60)/60*HH - 2) : 20;
    own.unshift(`<div class="ev wk-spill" style="top:0;height:${h}px;background:${c};left:2px;width:calc(100% - 8px)"
        title="Продолжение: ${esc(e.title)} · 00:00-${hhmm(Math.min(over, DAY_END))} (${hoursTxt(Math.min(over, DAY_END))} перешли через полночь)">
        <span class="t">↳ ${esc(e.title)}</span></div>`);
  });
  return own.join('');
}

/* полоса «идёт само»: ленты машинных потоков, часов владельца не едят */
function renderAuto(days){
  const keys = days.map(iso);
  const N = Math.max(keys.length, 1);
  const first = keys[0], last = keys[N-1];
  const row = $('autorow');
  // пересечение окна ленты с показанным диапазоном (в режиме дня диапазон = один день)
  const items = DATA.auto.filter(a=>{
    const f = a.from || a.to, t = a.to || a.from;
    return isDate(f) && isDate(t) && f <= last && t >= first;
  });
  // раскладка по строкам, чтобы ленты не наезжали (служебное держим локально)
  const rows = [], pos = new Map();
  items.forEach(a=>{
    const s = Math.max(keys.indexOf(a.from), 0);
    const e = a.to && keys.indexOf(a.to) >= 0 ? keys.indexOf(a.to) : N-1;
    const box = {s, e: Math.max(e, s), row: 0};
    let r = rows.findIndex(R=>R.every(o=>o.e < box.s || o.s > box.e));
    if(r < 0){ rows.push([box]); r = rows.length-1; } else rows[r].push(box);
    box.row = r;
    pos.set(a, box);
  });
  const h = Math.max(rows.length*23 + 8, 30);
  row.style.minHeight = h + 'px';
  row.innerHTML = `<div class="lbl">идёт<br>само</div>` +
    [...Array(N)].map(()=>'<div class="cell"></div>').join('') +
    `<div class="lanes">` + items.map(a=>{
      const c = color((DATA.tracks[a.track]||{}).color);
      const b = pos.get(a);
      const left = b.s/N*100, width = (b.e - b.s + 1)/N*100;
      const by = a.launchedBy ? ' · запускаешь ты' : '';
      return `<div class="lane" style="left:${left}%;width:calc(${width}% - 6px);top:${b.row*23}px;background-color:${c}"
              title="${esc((a.note||'') + by)} · окно ${esc(shortDate(a.from))}-${esc(shortDate(a.to))}">${esc(a.title)}${by}</div>`;
    }).join('') + `</div>`;
}

function nowLine(){
  const n = new Date(), m = nowMin();
  if(m < H0*60 || m > H1*60) return '';
  const top = (m - H0*60)/60*HH;
  return `<div class="now" style="top:${top}px"></div>
          <div class="nowlabel" style="top:${top}px;left:-2px">${pad(n.getHours())}:${pad(n.getMinutes())}</div>`;
}

/* ---------- взаимодействие ---------- */
const snap = m => Math.min(H1*60 - 15, Math.max(H0*60, Math.round(m/15)*15));

/* Магнит к началу блока. Помогает, а не запрещает: тянешь ближе 10 минут к
   границе блока - встаёт ровно на неё, дальше работает обычный шаг 15 минут.
   Точное время всегда можно вписать руками в карточке задачи - там магнита нет. */
function snapMag(dateKey, m){
  const segs = rhythmFor(dateKey);
  let best = null, bd = MAGNET + 1;
  segs.forEach(s=>{
    if(s.type !== 'block') return;
    const d = Math.abs(s.start - m);
    if(d < bd){ bd = d; best = s.start; }
  });
  return best == null ? snap(m) : Math.min(H1*60 - 15, Math.max(H0*60, best));
}

function wire(){
  document.querySelectorAll('.ev').forEach(el=>{
    if(el.classList.contains('wk-spill')) return;      // хвост через полночь не таскаем
    el.addEventListener('mousedown', ev=>{
      if(ev.button !== 0) return;
      ev.preventDefault();
      if(ev.target.classList.contains('rz')) startResize(el, ev.clientY, false);
      else startDrag(el, ev.clientX, ev.clientY, false);
    });
    bindTouchDrag(el);
    el.addEventListener('click', ()=>{
      if(el._moved || Date.now() < suppressClickUntil) return;
      openPanel(el.dataset.id);
    });
  });

  wireBacklog();
  wireProjection();

  /* «Поставить сюда»: клик по свободной части фокус-окна блока. Кнопка накрывает
     ровно свободную дыру, поэтому «клик по пустому блоку» и есть клик по ней.
     Сама полоса разметки под кнопкой прозрачна для указателя - перенос задач,
     бросок чипа и двойной клик по пустому месту работают как раньше. */
  document.querySelectorAll('.wk-fill').forEach(b=>{
    b.addEventListener('click', e=>{
      e.stopPropagation();
      if(Date.now() < suppressClickUntil) return;
      createAt(b.dataset.date, +b.dataset.start, +b.dataset.dur);
    });
  });

  document.querySelectorAll('.col').forEach(col=>{
    col.addEventListener('dragover', e=>e.preventDefault());
    col.addEventListener('drop', e=>{
      e.preventDefault();
      const tid = e.dataTransfer.getData('taskid');
      if(tid) return placeTask(tid, col, e.clientY);
      const bid = e.dataTransfer.getData('bid'); if(!bid) return;
      placeBacklog(bid, col, e.clientY);
    });
    col.addEventListener('dblclick', e=>{
      if(e.target.closest && e.target.closest('.ev')) return;
      if(e.target.closest && e.target.closest('.wk-fill')) return;   // там уже отработал клик
      createAt(col.dataset.date, timeAt(col, e.clientY));
    });
    // двойной тап по пустому месту = то же самое (dblclick на тач бывает не везде).
    // passive:false обязателен: внутри зовём preventDefault, чтобы браузер не
    // догнал двойной тап зумом и синтетическим кликом
    let lastTap = 0, lastY = 0;
    col.addEventListener('touchend', e=>{
      if(e.target.closest && e.target.closest('.ev')) return;
      if(e.target.closest && e.target.closest('.wk-fill')) return;   // одиночный тап уже создал задачу
      const t = e.changedTouches[0], now = Date.now();
      if(now - lastTap < 400 && Math.abs(t.clientY - lastY) < 24){
        lastTap = 0;
        if(e.cancelable) e.preventDefault();
        createAt(col.dataset.date, timeAt(col, t.clientY));
      }else{ lastTap = now; lastY = t.clientY; }
    }, {passive:false});
  });
}

/* Чипы бэклога живут отдельной проводкой: раскрытие «Someday (N)» перерисовывает
   ТОЛЬКО полосу, и вешать заново слушатели всей сетки при этом нельзя - вышло бы
   по два обработчика на задачу и двойной клик создавал бы две задачи. */
function wireBacklog(){
  document.querySelectorAll('#backlog .chip').forEach(ch=>{
    if(ch.id === 'wk-chipadd'){
      ch.addEventListener('click', ()=>openQuickAdd({where:'backlog'}));
      return;
    }
    // ссылка-счётчик «Someday (N)»: раскрывает и сворачивает отложенные
    if(ch.id === 'wk-sdtoggle'){
      ch.addEventListener('click', ()=>{ somedayOpen = !somedayOpen; renderBacklog(); wireBacklog(); });
      return;
    }
    ch.addEventListener('dragstart', e=>e.dataTransfer.setData('bid', ch.dataset.bid));
    bindChipTouch(ch);
    ch.addEventListener('click', ()=>{
      if(Date.now() < suppressClickUntil) return;
      const b = DATA.backlog.find(x=>x.id === ch.dataset.bid);
      if(b) openQuickAdd({fromBacklog:b});
    });
  });
}

function timeAt(col, clientY){
  const r = col.getBoundingClientRect();
  return snapMag(col.dataset.date, (clientY - r.top)/HH*60 + H0*60);
}

/* создать событие прямо в слоте сетки */
function createAt(dateKey, startMin, wantDur){
  /* Целимся в окно ФОКУСА блока, а не в весь блок: перерыв в его конце
     остаётся перерывом. wantDur приходит с кнопки «поставить сюда» - там
     ширина уже посчитана по реально свободной дыре. */
  const hit = rhythmFor(dateKey).find(s=>s.type === 'block' && s.start === startMin);
  let dur = wantDur > 0 ? clampDur(wantDur, false)
                        : (hit ? clampDur(hit.focusEnd - hit.start, false) : 60);
  if(startMin + dur > H1*60) dur = Math.max(DUR_MIN, H1*60 - startMin);
  const blocked = slotBlocked(dateKey, startMin, dur);
  if(blocked) return notify(blocked, 'err');
  const track = Object.keys(DATA.tracks)[0] || 'operac';
  const id = uid('e');
  const ev = {id, kind:'active', title:'Новая задача', date:dateKey, start:hhmm(startMin), dur, track, who:'владелец'};
  DATA.events.push(ev);
  const msgs = pushOverlap([], ev);
  save('создание задачи'); render();
  openPanel(id, 'f-title');
  const where = hit
    ? ' - это блок ' + hit.n + (hit.tag ? ', ' + hit.tag : '') + ', занял ' + dur + ' мин фокуса'
    : '';
  notify('Создал задачу на ' + shortDate(dateKey) + ' в ' + hhmm(startMin) + where +
         ', впиши название' + (msgs.length ? '\n' + msgs.join('\n') : ''),
         msgs.length ? 'warn' : 'ok', msgs.length ? 9000 : 4500);
}

/* положить чип бэклога в колонку */
function placeBacklog(bid, col, clientY){
  const b = DATA.backlog.find(x=>x.id === bid); if(!b) return;
  const m = timeAt(col, clientY);
  const dur = clampDur(+b.est || 60, false);
  const blocked = slotBlocked(col.dataset.date, m, dur);
  if(blocked) return notify(blocked, 'err');
  const ev = {id:uid('e'), kind:'active', title:b.title, date:col.dataset.date,
              start:hhmm(m), dur, est:dur, track:b.track, who:'владелец'};
  DATA.events.push(ev);
  DATA.backlog = DATA.backlog.filter(x=>x.id !== bid);
  const msgs = [];
  if(dur !== (+b.est||0)) msgs.push('Длительность подтянул до ' + hoursTxt(dur) + ': в бэклоге стояла оценка ' + (+b.est||0) + ' мин');
  pushOverlap(msgs, ev);
  save('раскладка «' + b.title + '» из бэклога'); render();
  tell(msgs);
}

/* ---------- перенос и длительность: мышь + палец ---------- */
/* ВАЖНО: touchstart тут регистрируется с {passive:false}. Внутри зовём
   preventDefault (тяга за нижнюю кромку), а в пассивном слушателе браузер его
   игнорирует и ругается в консоль «Unable to preventDefault inside passive
   event listener invocation» - на живом телефоне это означало, что вместе с
   длительностью ехала вся страница. */
function bindTouchDrag(el){
  el.addEventListener('touchstart', ev=>{
    if(ev.touches.length !== 1) return;
    const t = ev.touches[0], x0 = t.clientX, y0 = t.clientY;
    if(ev.target.classList.contains('rz')){
      if(ev.cancelable) ev.preventDefault();
      startResize(el, y0, true);
      return;
    }
    let dead = false;
    const timer = setTimeout(()=>{
      if(dead) return;
      dead = true; clean();
      if(navigator.vibrate) try{ navigator.vibrate(12); }catch(e){}
      startDrag(el, x0, y0, true);
    }, 280);
    function clean(){
      el.removeEventListener('touchmove', guard);
      el.removeEventListener('touchend', cancel);
      el.removeEventListener('touchcancel', cancel);
    }
    function guard(e2){
      const p = e2.touches[0];
      if(Math.abs(p.clientX - x0) > 9 || Math.abs(p.clientY - y0) > 9){ dead = true; clearTimeout(timer); clean(); }
    }
    function cancel(){ dead = true; clearTimeout(timer); clean(); }
    el.addEventListener('touchmove', guard, {passive:true});   // guard ничего не отменяет
    el.addEventListener('touchend', cancel);
    el.addEventListener('touchcancel', cancel);
  }, {passive:false});
}

/* один драйвер потока указателя на мышь и на палец */
function pointerStream(isTouch, onMove, onEnd){
  const mv = isTouch ? 'touchmove' : 'mousemove';
  const up = isTouch ? 'touchend' : 'mouseup';
  const move = e=>{
    const p = isTouch ? e.touches[0] : e;
    if(!p) return;
    if(isTouch && e.cancelable) e.preventDefault();       // держим страницу от прокрутки
    onMove(p.clientX, p.clientY);
  };
  const end = e=>{
    document.removeEventListener(mv, move);
    document.removeEventListener(up, end);
    if(isTouch) document.removeEventListener('touchcancel', end);
    onEnd(e);
  };
  // оба слушателя non-passive: и move, и end зовут preventDefault
  document.addEventListener(mv, move, {passive:false});
  document.addEventListener(up, end, {passive:false});
  if(isTouch) document.addEventListener('touchcancel', end, {passive:false});
}

function startDrag(el, x0, y0, isTouch){
  const e = DATA.events.find(x=>x.id === el.dataset.id); if(!e) return;
  releasePanelFocus();          // мышь взяла задачу - Cmd+Z теперь про сетку, не про поле
  const before = {date:e.date, start:e.start, dur:e.dur};
  const chain = findChain(e);
  const origin = tmin(e.start);
  dragging = true;
  el._moved = false;
  el.classList.add('drag');
  const cols = [...document.querySelectorAll('.col')];
  let overCol = null;

  pointerStream(isTouch, (x,y)=>{
    const dy = y - y0, dx = x - x0;
    if(Math.abs(dy) > 3 || Math.abs(dx) > 3) el._moved = true;
    // колонку определяем ПЕРВОЙ: магнит тянется к блокам того дня, над которым палец
    const under = cols.find(c=>{ const r = c.getBoundingClientRect(); return x >= r.left && x <= r.right; });
    e.date = under ? under.dataset.date : before.date;
    let ns = snapMag(e.date, origin + dy/HH*60);
    if(ns + (+e.dur||0) > H1*60) ns = Math.max(H0*60, H1*60 - (+e.dur||0));
    e.start = hhmm(ns);
    if(overCol !== under){
      if(overCol) overCol.classList.remove('wk-over');
      overCol = under || null;
      if(overCol) overCol.classList.add('wk-over');
    }
    el.style.top = ((ns - H0*60)/60*HH) + 'px';
  }, ev=>{
    dragging = false;
    if(overCol) overCol.classList.remove('wk-over');
    el.classList.remove('drag');
    // просто клик: сетку не трогаем, иначе click прилетит в уже снесённый узел
    if(!el._moved) return;
    if(isTouch){
      suppressClickUntil = Date.now() + 500;
      if(ev && ev.cancelable) ev.preventDefault();
    }
    const blocked = slotBlocked(e.date, tmin(e.start), +e.dur||0);
    if(blocked){
      e.date = before.date; e.start = before.start;
      notify(blocked + '\nВернул задачу на место: ' + shortDate(before.date) + ' ' + before.start, 'err', 7000);
      render();
      return;
    }
    const msgs = applyCascade(e, before, chain);
    pushOverlap(msgs, e);
    save('перенос задачи «' + e.title + '»'); render();
    tell(msgs);
    setTimeout(()=>{ el._moved = false; }, 50);
  });
}

function startResize(el, y0, isTouch){
  const e = DATA.events.find(x=>x.id === el.dataset.id); if(!e) return;
  releasePanelFocus();
  const before = {date:e.date, start:e.start, dur:e.dur};
  const chain = findChain(e);
  const orig = +e.dur || 0;
  const isL = e.kind === 'launch';
  dragging = true;
  el._moved = true;
  pointerStream(isTouch, (x,y)=>{
    let nd = clampDur(orig + (y - y0)/HH*60, isL);
    if(tmin(e.start) + nd > H1*60) nd = Math.max(isL?DUR_MIN_L:DUR_MIN, H1*60 - tmin(e.start));
    e.dur = nd;
    el.style.height = Math.max(nd/60*HH - 2, 16) + 'px';
  }, ev=>{
    dragging = false;
    if(isTouch){
      suppressClickUntil = Date.now() + 500;
      if(ev && ev.cancelable) ev.preventDefault();
    }
    const t = trainingFor(e.date);
    if(t && tmin(e.start) < t.end && tmin(e.start) + e.dur > t.start){
      e.dur = before.dur;
      notify('Задача наехала бы на тренировку ' + hhmm(t.start) + '-' + hhmm(t.end) + ': длительность вернул', 'err', 6000);
      render(); return;
    }
    const msgs = applyCascade(e, before, chain);
    pushOverlap(msgs, e);
    save('длительность «' + e.title + '»'); render();
    tell(msgs);
    setTimeout(()=>{ el._moved = false; }, 50);
  });
}

/* ---------- цепочка: точка запуска и лента «идёт само» ---------- */
function laneOfLaunch(L){
  if(!L) return null;
  return (L.starts ? DATA.auto.find(a=>a.id === L.starts) : null)
      || DATA.auto.find(a=>a.launchedBy === L.id) || null;
}
/* Что поедет вслед за этим событием. Считается ДО переноса. */
function findChain(e){
  if(e.kind === 'launch'){
    const lane = laneOfLaunch(e);
    return {launch:e, lane, self:true, gap:0,
            span: lane ? dayDiff(lane.from, lane.to) : 0,
            missing: (!lane && e.starts) ? e.starts : null};
  }
  const end = tmin(e.start) + (+e.dur||0);
  let best = null;
  DATA.events.forEach(x=>{
    if(x.kind !== 'launch' || x.date !== e.date || x.track !== e.track) return;
    const s = tmin(x.start);
    if(s < end || s - end > 240) return;         // точка запуска стоит сразу за работой
    if(!best || s < tmin(best.start)) best = x;
  });
  if(!best) return null;
  const lane = laneOfLaunch(best);
  return {launch:best, lane, self:false, gap: tmin(best.start) - end,
          span: lane ? dayDiff(lane.from, lane.to) : 0,
          missing: (!lane && best.starts) ? best.starts : null};
}
/* Подтянуть точку запуска и окно ленты за переехавшим событием.
   Возвращает список сообщений: молчать про сорванную цепочку нельзя. */
function applyCascade(e, before, chain){
  const msgs = [];
  if(!chain) return msgs;
  const moved = e.date !== before.date || e.start !== before.start || (+e.dur||0) !== (+before.dur||0);
  if(!moved) return msgs;
  const L = chain.launch;

  if(!chain.self){
    const prevWhen = shortDate(L.date) + ' ' + L.start;
    let ns = tmin(e.start) + (+e.dur||0) + chain.gap;
    if(ns + (+L.dur||0) > H1*60){
      ns = Math.max(H0*60, H1*60 - (+L.dur||0));
      msgs.push('Точка запуска «' + L.title + '» не влезала в конец дня: поставил на ' + hhmm(ns) + ', проверь глазами');
      msgs.warn = true;
    }
    if(ns < H0*60) ns = H0*60;
    const blocked = slotBlocked(e.date, ns, +L.dur||0);
    if(blocked){
      msgs.push('Каскад невозможен: точку запуска «' + L.title + '» некуда поставить (' + blocked + '). Она осталась на ' + prevWhen + ', перенеси руками');
      msgs.warn = true;
      return msgs;
    }
    L.date = e.date;
    L.start = hhmm(ns);
    msgs.push('Сдвинул точку запуска «' + L.title + '»: ' + prevWhen + ' → ' + shortDate(L.date) + ' ' + L.start);
  }

  const lane = chain.lane;
  if(!lane){
    msgs.push(chain.missing
      ? 'У точки запуска «' + L.title + '» указана лента ' + chain.missing + ', но её нет в данных: окно машины не сдвинулось, поправь руками'
      : 'К точке запуска «' + L.title + '» лента не привязана: окно машины не сдвигал');
    msgs.warn = true;
    return msgs;
  }
  const span = Math.max(0, chain.span);
  const prevWin = shortDate(lane.from) + '-' + shortDate(lane.to);
  lane.from = L.date;
  lane.to = addDays(L.date, span);
  if(chain.span < 0){
    msgs.push('У ленты «' + lane.title + '» окно было задом наперёд: выровнял в один день');
    msgs.warn = true;
  }
  const newWin = shortDate(lane.from) + '-' + shortDate(lane.to);
  if(prevWin !== newWin) msgs.push('Окно ленты «' + lane.title + '»: ' + prevWin + ' → ' + newWin);
  return msgs;
}

/* ---------- боковая панель ---------- */
function openPanel(id, focusField){
  const e = DATA.events.find(x=>x.id === id); if(!e) return;
  sel = id;
  const tr = DATA.tracks[e.track] || {};
  const p = $('panel');
  const isL = e.kind === 'launch';
  const kindLabel = isL ? '▶ только запустить' : 'твоё время';
  const chain = findChain(e);
  const lane = chain ? chain.lane : null;
  const end = tmin(e.start) + (+e.dur||0);
  const ovl = overlapsOf(e);
  const fact = +e.actual;
  const plan = +e.est || +e.dur || 0;
  p.innerHTML = `
    <h3>${esc(e.title)}</h3>
    <div class="meta"><span style="display:inline-block;width:9px;height:9px;border-radius:2px;background:${color(tr.color)};margin-right:6px"></span>
      ${esc(tr.label||e.track)} · <b>${kindLabel}</b> · ${esc(e.start)}-${hhmm(end % DAY_END)} · ${+e.dur||0} мин${end > DAY_END ? ' · хвост уходит в следующий день' : ''}</div>
    ${e.needsDecision === true ? `<div class="wk-decidebox">
      <b>⚠ Задача застряла</b>
      <p>Переносов ${esc(e.moved == null ? '3+' : e.moved)}${e.stuckSince ? ', висит с ' + esc(shortDate(e.stuckSince)) : ''}. Дальше движок её не двигает, пока не решишь</p>
      <div class="dacts">
        <button type="button" id="d-do">Сделать</button>
        <button type="button" id="d-deleg">Делегировать</button>
        <button type="button" id="d-later">Отложить</button>
        <button type="button" class="rm" id="d-drop">Удалить</button>
      </div></div>` : ''}
    ${ovl.length ? `<div class="wk-ovlbox">⚠ Наложение: пересекается с <b>${esc(ovl[0].title)}</b> (${esc(shortDate(ovl[0].date))} ${esc(ovl[0].start)})${
       ovl.length > 1 ? ' и ещё с ' + (ovl.length-1) : ''}. Если нарочно - оставляй</div>` : ''}
    ${chain && lane ? `<div class="wk-chain">Цепочка: ${chain.self ? '' : 'после этого точка запуска <b>' + esc(chain.launch.title) + '</b> в ' + esc(chain.launch.start) + ', дальше '}машина делает <b>${esc(lane.title)}</b><br>
      окно ${esc(shortDate(lane.from))}-${esc(shortDate(lane.to))}. Перенесёшь задачу - подтяну и точку запуска, и окно</div>` : ''}
    ${isFinite(fact) && fact > 0 ? `<div class="wk-fact">Факт: <b>${hoursTxt(fact)}</b> против плана ${hoursTxt(plan)}${
       plan > 0 ? ' · ×' + (fact/plan).toFixed(2) : ''} <button type="button" class="lnk" id="f-actual">изменить</button></div>` : ''}
    ${+e.focusMin > 0 ? `<div class="wk-focusbox">В фокусе: <b>${Math.round(+e.focusMin)} мин</b> накоплено таймером${
       plan > 0 ? ' из плана ' + hoursTxt(plan) : ''}</div>` : ''}
    ${e.note ? `<div class="note">${esc(e.note)}</div>` : ''}
    <label for="f-title">Название</label><input id="f-title" value="${esc(e.title)}">
    <div class="row">
      <div style="flex:1"><label for="f-start">Начало</label><input id="f-start" type="time" step="900" value="${esc(e.start)}"></div>
      <div style="flex:1"><label for="f-dur">Часов</label><input id="f-dur" type="number" step="0.05" min="${isL ? '0.05' : '0.25'}" max="12" value="${hoursVal(e.dur)}"></div>
    </div>
    <label for="f-track">Дорожка</label>
    <select id="f-track">${Object.keys(DATA.tracks).map(k=>
      `<option value="${esc(k)}" ${k===e.track?'selected':''}>${esc((DATA.tracks[k]||{}).label||k)}</option>`).join('')}</select>
    <label for="f-kind">Тип</label>
    <select id="f-kind">
      <option value="active" ${isL?'':'selected'}>Активная задача</option>
      <option value="launch" ${isL?'selected':''}>▶ Точка запуска</option>
    </select>
    <label for="f-date">Дата</label><input id="f-date" type="date" value="${esc(e.date)}">
    <div class="acts">
      <button class="bt-done" id="p-done">${e.done?'Вернуть в работу':'Готово'}</button>
      ${e.done ? '' : '<button class="bt-focus" id="p-focus" title="Таймер на весь экран: минуты уйдут в задачу">Фокус</button>'}
      <button class="bt-del" id="p-del">Удалить</button>
      <button class="bt-close" id="p-close">Закрыть</button>
    </div>`;
  p.classList.add('on');
  ['f-title','f-start','f-dur','f-track','f-kind','f-date'].forEach(fid=>{
    const el = $(fid);
    if(el) el.addEventListener('change', ()=>applyPanel(fid));
  });
  $('p-done').addEventListener('click', toggleDone);
  if($('p-focus')) $('p-focus').addEventListener('click', ()=>fzOpen(e.id));
  $('p-del').addEventListener('click', delEvent);
  $('p-close').addEventListener('click', closePanel);
  if($('f-actual')) $('f-actual').addEventListener('click', ()=>askActual(e, null));
  if(e.needsDecision === true){
    $('d-do').addEventListener('click', ()=>decideDo(e.id));
    $('d-deleg').addEventListener('click', ()=>decideDelegate(e.id));
    $('d-later').addEventListener('click', ()=>decideLater(e.id));
    $('d-drop').addEventListener('click', ()=>decideDrop(e.id));
  }
  if(focusField){
    const f = $(focusField);
    if(f){ f.focus(); if(f.select) try{ f.select(); }catch(err){} }
  }
}

function applyPanel(fromField){
  const e = DATA.events.find(x=>x.id === sel); if(!e) return;
  const before = {date:e.date, start:e.start, dur:e.dur};
  const chain = findChain(e);

  const title = ($('f-title').value||'').trim();
  if(!title) notify('Название пустым не оставляем, вернул прежнее', 'err');
  e.title = title || e.title;
  e.start = /^\d{2}:\d{2}$/.test($('f-start').value) ? $('f-start').value : e.start;

  const kind = $('f-kind').value === 'launch' ? 'launch' : 'active';
  const rawHours = parseFloat(String($('f-dur').value).replace(',','.'));
  const raw = Math.round((isFinite(rawHours) ? rawHours : (+e.dur||60)/60) * 60);
  const dur = clampDur(raw, kind === 'launch');
  if(dur !== raw) notify('Длительность держим в границах ' + (kind==='launch'?DUR_MIN_L:DUR_MIN) + ' мин - 12 ч: поставил ' + hoursTxt(dur), 'err', 6000);
  e.dur = dur;
  e.kind = kind;
  e.track = $('f-track').value;

  const date = $('f-date').value;
  if(isDate(date)) e.date = date; else notify('Дата не распознана, оставил прежнюю', 'err');

  const blocked = slotBlocked(e.date, tmin(e.start), e.dur);
  if(blocked){
    e.date = before.date; e.start = before.start; e.dur = before.dur;
    notify(blocked + '\nПравку отменил', 'err', 7000);
  }
  const msgs = blocked ? [] : applyCascade(e, before, chain);
  if(!blocked) pushOverlap(msgs, e);
  save('правка карточки «' + e.title + '»'); render();
  tell(msgs);
  // панель обязана показывать то, что в данных, а не то, что было
  const keep = fromField && fromField !== 'f-title' ? fromField : null;
  openPanel(sel, keep);
}

/* ---------- «готово» + сколько реально заняло ---------- */
function toggleDone(){ setDone(sel, true); }

/* Личный коэффициент оценки жив только если есть чем его считать: при
   отметке «готово» спрашиваем факт, подставляя план - один тап подтверждает
   «как планировал». */
function setDone(id, fromPanel){
  const e = DATA.events.find(x=>x.id === id); if(!e) return;
  if(e.done){
    e.done = false;
    save('возврат «' + e.title + '» в работу'); render();
    if(fromPanel) openPanel(id);
    return;
  }
  askActual(e, ()=>{
    e.done = true;
    save('отметка «сделано»: ' + e.title); render();
    if(fromPanel) openPanel(id);
  });
}

/* коэффициент недооценки: факт / план по задачам, где факт проставлен */
function estFactor(){
  let plan = 0, fact = 0, n = 0;
  DATA.events.forEach(e=>{
    const a = +e.actual, p = +e.est || +e.dur;
    if(!isFinite(a) || a <= 0 || !isFinite(p) || p <= 0) return;
    plan += p; fact += a; n++;
  });
  if(n < 3 || plan <= 0) return null;
  return {k: fact/plan, n};
}

/* prefillMin - чем заполнить поле (минуты). Фокус-режим подставляет сюда
   накопленные минуты, обычный путь «готово» - план задачи, как было. */
function askActual(e, onOk, prefillMin){
  qaClose();
  const planned = Math.max(0, +e.dur || 0);
  const had = +e.actual;
  const pre = (isFinite(+prefillMin) && +prefillMin > 0) ? +prefillMin
            : ((isFinite(had) && had > 0) ? had : planned);
  const box = document.createElement('div');
  box.className = 'wk-modal';
  box.id = 'wk-modal';
  box.innerHTML = `
    <div class="wk-dlg" role="dialog" aria-label="Сколько реально заняло">
      <h3>Сколько реально заняло?</h3>
      <div class="wk-hint">«${esc(e.title)}» · по плану ${hoursTxt(planned)}.${
        /* «ровно как планировал» - только когда подставленное РЕАЛЬНО равно плану.
           таймер подставил 0.05 ч при плане 0.8, а подпись
           уговаривала «оставь как есть» - поверишь ей и запишешь 3 минуты вместо 45 */
        pre === planned
          ? ' Оставь как есть и жми «Готово» - значит, ровно как планировал'
          : ` В поле подставлено ${hoursTxt(pre)} - это НЕ план, поправь, если было иначе`}${
        (isFinite(+prefillMin) && +prefillMin > 0)
          ? '<br>Таймер насчитал ' + Math.round(+prefillMin) + ' мин, поле округляет до 3 минут - впиши точнее, если важно'
          : ''}</div>
      <label for="ac-h">Часов по факту</label>
      <input id="ac-h" type="number" step="0.05" min="0.05" max="24" value="${hoursVal(pre)}">
      <div class="wk-err" id="ac-err"></div>
      <div class="acts">
        <button type="button" class="ok" id="ac-ok">Готово</button>
        <button type="button" class="no" id="ac-skip">Не считал</button>
        <button type="button" class="no" id="ac-cancel">Отмена</button>
      </div>
    </div>`;
  document.body.appendChild(box);

  const finish = (mins)=>{
    if(mins != null){
      if(!(+e.est > 0)) e.est = planned;        // план фиксируем, иначе коэффициент врёт
      e.actual = mins;
    }
    qaClose();
    if(onOk) onOk(); else { save('факт по «' + e.title + '»'); render(); if(sel === e.id) openPanel(sel); }
    if(mins != null){
      const f = estFactor();
      notify('Факт: ' + hoursTxt(mins) + ' против плана ' + hoursTxt(+e.est || planned) +
             (f ? '\nТвой коэффициент оценки: ×' + f.k.toFixed(2) + ' по ' + f.n + ' задачам. Новые оценки умножай на него' : ''),
             null, 7000);
    }
  };
  $('ac-ok').addEventListener('click', ()=>{
    const raw = parseFloat(String($('ac-h').value).replace(',','.'));
    if(!isFinite(raw) || raw <= 0){ const b = $('ac-err'); if(b) b.textContent = 'Часы числом, от 0.05 до 24'; return; }
    const mins = Math.max(1, Math.min(1440, Math.round(raw*60)));
    finish(mins);
  });
  $('ac-skip').addEventListener('click', ()=>finish(null));
  $('ac-cancel').addEventListener('click', qaClose);
  box.addEventListener('mousedown', ev=>{ if(ev.target === box) qaClose(); });
  const inp = $('ac-h');
  inp.addEventListener('keydown', ev=>{ if(ev.key === 'Enter'){ ev.preventDefault(); $('ac-ok').click(); } });
  inp.focus();
  if(inp.select) try{ inp.select(); }catch(err){}
}

/* ---------- решения по застрявшей задаче (зеркало rituals/decide.py) ---------- */
/* первый день без перегруза и без защиты, как next_free_day в ритуалах */
function nextFreeDay(fromKey, dur){
  const cap = dayCapacity();
  let fallback = null;
  for(let i = 0; i < 21; i++){
    const k = addDays(fromKey, i);
    if(isProtectedDay(k)) continue;
    if(!fallback) fallback = k;
    if(!cap || dayLoad(k) + dur <= cap.norm) return k;
  }
  return fallback || fromKey;
}
function clearStuck(e){
  delete e.needsDecision;
  delete e.stuckSince;
  e.moved = 0;
}
function decideDo(id){
  const e = DATA.events.find(x=>x.id === id); if(!e) return;
  const dur = Math.max(0, +e.dur||0);
  const k = nextFreeDay(iso(new Date()), dur);
  e.date = k;
  const t = trainingFor(k);
  if(t && tmin(e.start) < t.end && tmin(e.start) + dur > t.start){
    e.start = hhmm(Math.max(H0*60, Math.min(H1*60 - dur, t.end)));
  }
  clearStuck(e);
  const msgs = ['Решение принято: делаю. Задача «' + e.title + '» встала на ' + shortDate(k) + ' в ' + e.start];
  pushOverlap(msgs, e);
  save('решение «сделать»: ' + e.title); render(); openPanel(id);
  tell(msgs);
}
function decideDrop(id){
  const e = DATA.events.find(x=>x.id === id); if(!e) return;
  if(!window.confirm('Удалить задачу «' + e.title + '»? Вернуть её будет нечем')) return;
  DATA.events = DATA.events.filter(x=>x.id !== id);
  save('удаление «' + e.title + '»'); render(); closePanel();
  notify('Решение принято: удалил «' + e.title + '»', null, 4000);
}
function toBacklog(e, when){
  DATA.events = DATA.events.filter(x=>x.id !== e.id);
  const item = {id:e.id, title:e.title, est:Math.max(0, +e.est || +e.dur || 0), track:e.track, when};
  DATA.backlog.push(item);
  return item;
}
function decideLater(id){
  const e = DATA.events.find(x=>x.id === id); if(!e) return;
  const ttl = addDays(iso(new Date()), SOMEDAY_TTL);
  /* статус someday: запись уходит из видимой полосы за счётчик и сама всплывает
     обратно в день TTL с бейджем «пора решить» */
  const item = toBacklog(e, '');
  delete item.when;
  item.status = 'someday';
  item.ttl = ttl;
  save('откладывание «' + e.title + '»'); render(); closePanel();
  notify('Решение принято: отложил «' + e.title + '» в Someday до ' + shortDate(ttl) +
         '\nВ полосе его нет, ищи за счётчиком «Someday». В день TTL всплывёт сам', null, 7000);
}
function decideDelegate(id){
  const e = DATA.events.find(x=>x.id === id); if(!e) return;
  qaClose();
  const box = document.createElement('div');
  box.className = 'wk-modal';
  box.id = 'wk-modal';
  box.innerHTML = `
    <div class="wk-dlg" role="dialog" aria-label="Делегировать">
      <h3>Кому делегируешь?</h3>
      <div class="wk-hint">«${esc(e.title)}» уйдёт в «Не разложено» с пометкой «делегировано»</div>
      <label for="dg-who">Имя</label>
      <input id="dg-who" value="${esc(e.who && e.who !== 'владелец' ? e.who : '')}" placeholder="напр. Вика" autocomplete="off">
      <div class="acts">
        <button type="button" class="ok" id="dg-ok">Делегировать</button>
        <button type="button" class="no" id="dg-cancel">Отмена</button>
      </div>
    </div>`;
  document.body.appendChild(box);
  const go = ()=>{
    const who = ($('dg-who').value||'').trim().slice(0,120);
    toBacklog(e, 'делегировано' + (who ? ': ' + who : ''));
    qaClose();
    save('делегирование «' + e.title + '»'); render(); closePanel();
    notify('Решение принято: «' + e.title + '» делегирована' + (who ? ' - ' + who : '') + ', лежит в «Не разложено»', null, 5000);
  };
  $('dg-ok').addEventListener('click', go);
  $('dg-cancel').addEventListener('click', qaClose);
  box.addEventListener('mousedown', ev=>{ if(ev.target === box) qaClose(); });
  $('dg-who').addEventListener('keydown', ev=>{ if(ev.key === 'Enter'){ ev.preventDefault(); go(); } });
  $('dg-who').focus();
}

/* ---------- цель спринта: правится из интерфейса, не только читается ---------- */
function openGoalEdit(){
  qaClose();
  /* Правится ОВЕРРАЙД именно этой недели, а не одна строка на все недели сразу.
     Пусто в оверрайде = цель считается из задач цикла */
  const wk = weekKeyOfOpenWeek();
  const comp = computedGoal();
  const cur = goalOverride();
  const box = document.createElement('div');
  box.className = 'wk-modal';
  box.id = 'wk-modal';
  box.innerHTML = `
    <div class="wk-dlg" role="dialog" aria-label="Цель спринта">
      <h3>Цель недели ${esc(shortDate(wk))}</h3>
      <div class="wk-hint">Одной фразой: что считается победой к концу этой недели.
        Оставишь пусто - движок сам возьмёт северную задачу из целей цикла${comp?`: «${esc(comp.task.title)}»`:''}</div>
      <label for="g-txt">Формулировка</label>
      <textarea id="g-txt" rows="4" maxlength="2000">${esc(cur)}</textarea>
      <div class="wk-err" id="g-err"></div>
      <div class="acts">
        <button type="button" class="ok" id="g-ok">Сохранить</button>
        <button type="button" class="no" id="g-cancel">Отмена</button>
        ${cur.trim() ? '<button type="button" class="rm" id="g-clear">Убрать цель</button>' : ''}
      </div>
    </div>`;
  document.body.appendChild(box);
  $('g-ok').addEventListener('click', ()=>{
    const v = ($('g-txt').value||'').trim();
    if(v.length > 2000){ $('g-err').textContent = 'Слишком длинно: до 2000 знаков'; return; }
    if(!v){ $('g-err').textContent = 'Пусто. Чтобы убрать цель совсем - кнопка «Убрать цель»'; return; }
    if(!DATA.sprintGoals || typeof DATA.sprintGoals !== 'object') DATA.sprintGoals = {};
    DATA.sprintGoals[wk] = v;
    save('правка цели недели ' + wk); render(); qaClose();
    notify('Цель недели записана', 'ok');
  });
  $('g-cancel').addEventListener('click', qaClose);
  if($('g-clear')) $('g-clear').addEventListener('click', ()=>{
    if(!window.confirm('Убрать свою формулировку на эту неделю? Цель начнёт считаться из задач цикла')) return;
    if(DATA.sprintGoals && typeof DATA.sprintGoals === 'object') delete DATA.sprintGoals[wk];
    save('снятие оверрайда цели недели ' + wk); render(); qaClose();
    notify('Цель недели снова считается из целей цикла', null, 3500);
  });
  box.addEventListener('mousedown', ev=>{ if(ev.target === box) qaClose(); });
  $('g-txt').focus();
}
function delEvent(){
  const e = DATA.events.find(x=>x.id === sel); if(!e) return;
  if(!window.confirm('Удалить задачу «' + e.title + '»? Вернуть её будет нечем')) return;
  DATA.events = DATA.events.filter(x=>x.id !== sel);
  save('удаление задачи «' + e.title + '»'); render(); closePanel();
  notify('Удалил: ' + e.title, null, 3500);
}
/* Панель закрыли - отпускаем и фокус. Иначе он остаётся в скрытом поле
   названия, и Cmd+Z уходит в текстовую отмену этого поля вместо сетки. */
function releasePanelFocus(){
  const a = document.activeElement;
  const p = $('panel');
  if(a && p && p.contains(a) && a.blur) a.blur();
}
function closePanel(){
  releasePanelFocus();
  const p = $('panel');
  if(p) p.classList.remove('on');
  sel = null;
}

/* Прокручиваем только .scroll. В мобильной недельной раскладке скроллером
   работает .week-root (это правила app.css, чужой файл) - трогать его отсюда
   нельзя: уедет вся шапка вкладки вместе с сеткой. */
function scrollToNow(){
  const m = nowMin();
  const scroll = $('scroll');
  if(scroll) scroll.scrollTop = Math.max(0, (m - H0*60)/60*HH - 180);
}

/* ---------- быстрый ввод ---------- */
function qaClose(){ const m = $('wk-modal'); if(m) m.remove(); }
function qaErr(text){ const b = $('qa-err'); if(b) b.textContent = text; return false; }

function openQuickAdd(opt){
  opt = opt || {};
  if(!DATA) return;
  qaClose();
  const fromB = opt.fromBacklog || null;
  const where = opt.where || (fromB ? 'grid' : 'grid');
  const today = iso(new Date());
  const inWeek = today >= iso(weekStart) && today <= addDays(iso(weekStart), 6);
  // в режиме дня по умолчанию ставим в тот день, который открыт
  const date = opt.date || (viewMode === 'day' && isDate(dayCursor) ? dayCursor : (inWeek ? today : iso(weekStart)));
  let start = opt.start;
  if(start == null){
    const m = Math.max(H0*60, Math.min(H1*60 - 60, Math.ceil(nowMin()/15)*15));
    start = hhmm(date === today ? m : Math.max(H0*60, tmin((PROFILE&&PROFILE.workStart)||'10:00')));
  }
  const dur = opt.dur || (fromB ? clampDur(+fromB.est || 60, false) : 60);
  const trackKeys = Object.keys(DATA.tracks);
  const track = opt.track || (fromB ? fromB.track : trackKeys[0]);
  const fac = estFactor();

  const box = document.createElement('div');
  box.className = 'wk-modal';
  box.id = 'wk-modal';
  box.innerHTML = `
    <div class="wk-dlg" role="dialog" aria-label="Новая задача">
      <h3>${fromB ? 'Разложить задачу' : 'Новая задача'}</h3>
      <label for="qa-title">Название</label>
      <input id="qa-title" value="${esc(fromB ? fromB.title : '')}" placeholder="Что надо сделать" autocomplete="off">
      <div class="row">
        <div><label for="qa-where">Куда</label>
          <select id="qa-where">
            <option value="grid" ${where==='grid'?'selected':''}>В сетку недели</option>
            <option value="backlog" ${where==='backlog'?'selected':''}>В «Не разложено»</option>
          </select></div>
        <div><label for="qa-kind">Тип</label>
          <select id="qa-kind">
            <option value="active">Активная задача</option>
            <option value="launch">▶ Точка запуска</option>
          </select></div>
      </div>
      <div class="row" id="qa-when-row">
        <div><label for="qa-date">Дата</label><input id="qa-date" type="date" value="${esc(date)}"></div>
        <div><label for="qa-time">Время</label><input id="qa-time" type="time" step="900" value="${esc(start)}"></div>
      </div>
      <div class="row">
        <div><label for="qa-dur">Длительность, ч</label><input id="qa-dur" type="number" step="0.05" min="0.05" max="12" value="${hoursVal(dur)}"></div>
        <div><label for="qa-track">Дорожка</label>
          <select id="qa-track">${trackKeys.map(k=>
            `<option value="${esc(k)}" ${k===track?'selected':''}>${esc((DATA.tracks[k]||{}).label||k)}</option>`).join('')}</select></div>
      </div>
      ${fac ? `<div class="wk-hint">Ты недооцениваешь время в ×${fac.k.toFixed(2)} (по ${fac.n} задачам с фактом).
        <button type="button" class="lnk" id="qa-fac">применить к оценке</button></div>` : ''}
      <div id="qa-note-row" style="display:none"><label for="qa-when">Пометка «когда» (необязательно)</label>
        <input id="qa-when" value="${esc(fromB && fromB.when ? fromB.when : '')}" placeholder="напр. след. неделя" autocomplete="off"></div>
      <div class="row" id="qa-bl-row" style="display:none">
        <div><label for="qa-prio">Приоритет 0-9</label>
          <input id="qa-prio" type="number" min="0" max="9" step="1" value="${blPrio(fromB) == null ? '' : blPrio(fromB)}" placeholder="пусто = без приоритета"></div>
        <div><label for="qa-due">Дедлайн</label>
          <input id="qa-due" type="date" value="${esc(fromB && isDate(fromB.due) ? fromB.due : '')}"></div>
      </div>
      ${fromB ? `<div class="wk-sdrow" id="qa-sd-row">
        <div class="wk-hint">${blStatus(fromB) === 'someday'
          ? 'Сейчас отложена: в полосе её нет' + (isDate(fromB.ttl) ? ', всплывёт ' + shortDate(fromB.ttl) : ', срок не задан')
          : 'Не сейчас, но и не выбрасываем: уйдёт из полосы, а в день TTL всплывёт обратно с пометкой «пора решить». TTL можно не ставить'}</div>
        <div class="wk-sdacts">
          <div><label for="qa-ttl">TTL: когда вернуть</label>
            <input id="qa-ttl" type="date" value="${esc(isDate(fromB.ttl) ? fromB.ttl : '')}"></div>
          <button type="button" id="qa-sd">${blStatus(fromB) === 'someday' ? 'Вернуть в активные' : 'в Someday'}</button>
        </div></div>` : ''}
      <div class="wk-err" id="qa-err"></div>
      <div class="acts">
        <button type="button" class="ok" id="qa-ok">${fromB ? 'Разложить' : 'Добавить'}</button>
        <button type="button" class="no" id="qa-cancel">Отмена</button>
        ${fromB ? '<button type="button" class="rm" id="qa-rm">Удалить из бэклога</button>' : ''}
      </div>
    </div>`;
  document.body.appendChild(box);

  const toggleWhere = ()=>{
    const w = $('qa-where').value;
    $('qa-when-row').style.display = w === 'backlog' ? 'none' : 'flex';
    $('qa-note-row').style.display = w === 'backlog' ? 'block' : 'none';
    $('qa-kind').disabled = w === 'backlog';
    // приоритет и дедлайн - поля записи бэклога: нужны и при раскладке чипа
    $('qa-bl-row').style.display = (fromB || w === 'backlog') ? 'flex' : 'none';
  };
  $('qa-where').addEventListener('change', toggleWhere);
  toggleWhere();

  // «в Someday» / «Вернуть в активные»: правит ту же запись, форму не покидаем
  if($('qa-sd')) $('qa-sd').addEventListener('click', ()=>{
    const b = DATA.backlog.find(x=>x.id === fromB.id);
    if(!b){ qaClose(); return notify('Запись из «Не разложено» пропала: отложить нечего', 'err'); }
    blFromForm(b);
    if(blStatus(b) === 'someday'){
      delete b.status;
      delete b.ttl;
      save('возврат «' + b.title + '» в активные'); render(); qaClose();
      notify('Вернул в полосу «Не разложено»: ' + b.title, 'ok', 4500);
      return;
    }
    b.status = 'someday';
    const ttl = $('qa-ttl') ? $('qa-ttl').value : '';
    if(isDate(ttl)) b.ttl = ttl; else delete b.ttl;
    save('откладывание «' + b.title + '» в someday'); render(); qaClose();
    notify('Отложил в Someday: ' + b.title +
           (isDate(ttl) ? '\nВ день ' + shortDate(ttl) + ' всплывёт обратно с пометкой «пора решить»'
                        : '\nБез TTL сам не всплывёт: ищи за счётчиком «Someday»'), 'ok', 7000);
  });

  box.addEventListener('mousedown', e=>{ if(e.target === box) qaClose(); });
  $('qa-cancel').addEventListener('click', qaClose);
  $('qa-ok').addEventListener('click', ()=>qaSubmit(fromB));
  if(fromB) $('qa-rm').addEventListener('click', ()=>{
    if(!window.confirm('Удалить «' + fromB.title + '» из бэклога?')) return;
    DATA.backlog = DATA.backlog.filter(x=>x.id !== fromB.id);
    save('удаление «' + fromB.title + '» из бэклога'); render(); qaClose();
    notify('Убрал из бэклога: ' + fromB.title, null, 3500);
  });
  if($('qa-fac')) $('qa-fac').addEventListener('click', ()=>{
    const el = $('qa-dur');
    const raw = parseFloat(String(el.value).replace(',','.'));
    if(!isFinite(raw) || raw <= 0) return;
    el.value = hoursVal(clampDur(Math.round(raw*60*fac.k), false));
    notify('Оценку умножил на твой коэффициент ×' + fac.k.toFixed(2), null, 4000);
  });
  ['qa-title','qa-date','qa-time','qa-dur'].forEach(id=>{
    const el = $(id);
    if(el) el.addEventListener('keydown', e=>{ if(e.key === 'Enter'){ e.preventDefault(); qaSubmit(fromB); } });
  });
  $('qa-title').focus();
}

function qaSubmit(fromB){
  const title = ($('qa-title').value||'').trim();
  if(!title) return qaErr('Впиши название: без него задача потеряется');
  const where = $('qa-where').value;
  const kind = (where === 'grid' && $('qa-kind').value === 'launch') ? 'launch' : 'active';
  const track = $('qa-track').value;
  const rawHours = parseFloat(String($('qa-dur').value).replace(',','.'));
  if(!isFinite(rawHours) || rawHours <= 0) return qaErr('Длительность в часах, от 0.25 до 12');
  const raw = Math.round(rawHours*60);
  const dur = clampDur(raw, kind === 'launch');
  const corrected = dur !== raw;

  if(where === 'backlog'){
    /* Чип открыт и переведён в «Не разложено» - правим ТУ ЖЕ запись, а не
       плодим двойника: раньше рядом со старой появлялась вторая копия. */
    const item = fromB ? (DATA.backlog.find(x=>x.id === fromB.id) || fromB) : {id:uid('b')};
    item.title = title;
    item.est = dur;
    item.track = track;
    const when = ($('qa-when').value||'').trim();
    if(when) item.when = when; else delete item.when;
    blFromForm(item);
    item.title = title;                         // название в форме главнее
    item.est = dur;
    if(!fromB) DATA.backlog.push(item);
    save((fromB ? 'правка «' : 'добавление «') + title + '» в бэклоге'); render(); qaClose();
    notify((fromB ? 'Оставил в «Не разложено»: ' : 'Добавил в «Не разложено»: ') + title +
           (corrected ? ' (длительность поправил до ' + hoursTxt(dur) + ')' : ''), 'ok');
    return true;
  }

  const date = $('qa-date').value;
  if(!isDate(date)) return qaErr('Проверь дату');
  const time = $('qa-time').value;
  if(!/^\d{2}:\d{2}$/.test(time)) return qaErr('Проверь время');
  const start = tmin(time);
  const blocked = slotBlocked(date, start, dur);
  if(blocked) return qaErr(blocked);

  const ev = {id:uid('e'), kind, title, date, start:time, dur, est:dur, track, who:'владелец'};
  const prioNow = $('qa-prio') ? String($('qa-prio').value).trim() : '';
  if(prioNow !== '' && isFinite(+prioNow)) ev.priority = Math.max(0, Math.min(9, Math.round(+prioNow)));
  DATA.events.push(ev);
  if(fromB) DATA.backlog = DATA.backlog.filter(x=>x.id !== fromB.id);
  // если задача не в показанной неделе или не в открытом дне - перепрыгиваем к ней,
  // иначе «добавил» выглядит как ничего
  if(date < iso(weekStart) || date > addDays(iso(weekStart), 6)) weekStart = startOfWeek(parseISO(date));
  if(viewMode === 'day') dayCursor = date;
  const msgs = pushOverlap([], ev);
  save('добавление задачи «' + title + '»'); render(); qaClose();
  notify('Добавил: ' + title + ' · ' + shortDate(date) + ' ' + time +
         (corrected ? ' (длительность поправил до ' + hoursTxt(dur) + ')' : '') +
         (msgs.length ? '\n' + msgs.join('\n') : ''),
         msgs.length ? 'warn' : 'ok', msgs.length ? 9000 : 4500);
  return true;
}

/* ---------- перетаскивание чипа бэклога пальцем ---------- */
function bindChipTouch(ch){
  ch.addEventListener('touchstart', ev=>{
    if(ev.touches.length !== 1) return;
    const t = ev.touches[0], x0 = t.clientX, y0 = t.clientY;
    let ghost = null, overCol = null, dead = false;
    const timer = setTimeout(start, 260);
    function start(){
      if(dead) return;
      clean();
      if(navigator.vibrate) try{ navigator.vibrate(12); }catch(e){}
      ghost = document.createElement('div');
      ghost.className = 'wk-ghost';
      ghost.textContent = ch.textContent.trim();
      ghost.style.left = x0 + 'px'; ghost.style.top = y0 + 'px';
      document.body.appendChild(ghost);
      document.addEventListener('touchmove', mv, {passive:false});
      document.addEventListener('touchend', up);
      document.addEventListener('touchcancel', up);
    }
    function mv(e2){
      if(e2.cancelable) e2.preventDefault();
      const p = e2.touches[0];
      ghost.style.left = p.clientX + 'px'; ghost.style.top = p.clientY + 'px';
      const el = document.elementFromPoint(p.clientX, p.clientY);
      const col = el && el.closest ? el.closest('.col') : null;
      if(col !== overCol){
        if(overCol) overCol.classList.remove('wk-over');
        overCol = col;
        if(overCol) overCol.classList.add('wk-over');
      }
    }
    function up(e2){
      document.removeEventListener('touchmove', mv);
      document.removeEventListener('touchend', up);
      document.removeEventListener('touchcancel', up);
      suppressClickUntil = Date.now() + 500;
      const p = e2.changedTouches[0];
      if(ghost) ghost.remove();
      if(overCol) overCol.classList.remove('wk-over');
      const el = document.elementFromPoint(p.clientX, p.clientY);
      const col = el && el.closest ? el.closest('.col') : null;
      if(col) placeBacklog(ch.dataset.bid, col, p.clientY);
      else notify('Отпусти чип над днём недели, тогда задача встанет в сетку', null, 4000);
    }
    function clean(){
      ch.removeEventListener('touchmove', guard);
      ch.removeEventListener('touchend', cancel);
      ch.removeEventListener('touchcancel', cancel);
    }
    function guard(e2){
      const p = e2.touches[0];
      if(Math.abs(p.clientX - x0) > 9 || Math.abs(p.clientY - y0) > 9){ dead = true; clearTimeout(timer); clean(); }
    }
    function cancel(){ dead = true; clearTimeout(timer); clean(); }
    ch.addEventListener('touchmove', guard, {passive:true});
    ch.addEventListener('touchend', cancel);
    ch.addEventListener('touchcancel', cancel);
  }, {passive:true});
}

/* ================= ФОКУС-РЕЖИМ: одна задача на весь экран =================
   Входы: кнопка «Фокус» в карточке задачи, кнопка у чипа «Сейчас» в недельном
   режиме и та же кнопка на крупной карточке дня (в режиме дня чип спрятан
   стилями, поэтому вход туда вынесен отдельно).

   Время считаем ОТ Date.now(), а не тиками setInterval: вкладку браузера
   уводят в фон, таймеры там душат, а фокус обязан досчитать честно. Интервал
   только перерисовывает цифры.

   По стопу (или по истечении) минуты складываются в поле focusMin события и
   предлагается записать общий факт в actual - тот самый, что кормит
   коэффициент оценки estFactor(). */
const FZ_DEF = 80;                       // окно фокуса по умолчанию, минут
const FZ_STEP = 5;                       // шаг кнопок «-5 / +5»
const FZ_MIN = 5, FZ_MAX = 480;
let fz = null;                           // {id, totalMs, accumMs, since, timer, fired}

/* ---------- страховка минут: localStorage переживает конфликт записи ----------
   Оверлей фокуса живёт на body и работает с любой вкладки, а сетка (вместе с
   контейнером ошибок) при переключении умирает. Стоп таймера в такой момент
   писал минуты только в память страницы: конфликт версий 409 - и минуты
   исчезали молча. Теперь порядок жёсткий: сначала кладём минуты в localStorage,
   мутируем документ, пишем на сервер, и ТОЛЬКО после подтверждённого 200
   страховку снимаем (fzPendDrop в flush).

   want - каким должен стать focusMin после дозаписи. По нему при загрузке видно,
   что запись всё-таки прошла (например, ответ потерялся, а файл записался), и
   предложение не дублирует уже засчитанные минуты. */
function fzPendRead(){
  try{
    const o = JSON.parse(localStorage.getItem(FZ_PEND_KEY) || 'null');
    return (o && typeof o === 'object' && !Array.isArray(o)) ? o : {};
  }catch(e){ return {}; }
}
function fzPendWrite(map){
  try{
    if(!Object.keys(map).length) localStorage.removeItem(FZ_PEND_KEY);
    else localStorage.setItem(FZ_PEND_KEY, JSON.stringify(map));
  }catch(e){ /* приватный режим или переполнение: работаем как раньше, но не падаем */ }
}
function fzPendIds(){ return Object.keys(fzPendRead()); }
function fzPendCount(){ return fzPendIds().length; }
function fzPendPut(id, title, mins, want){
  if(!id || !(mins > 0)) return;
  const map = fzPendRead();
  const had = map[id];
  map[id] = {
    id: id,
    title: String(title || ''),
    mins: Math.max(0, Math.round((had ? +had.mins || 0 : 0) + mins)),   // два стопа подряд складываются
    want: Math.max(0, Math.min(1440, Math.round(want))),
    ts: Date.now()
  };
  fzPendWrite(map);
}
function fzPendDrop(ids){
  if(!ids || !ids.length) return;
  const map = fzPendRead();
  let hit = false;
  ids.forEach(id=>{ if(map[id]){ delete map[id]; hit = true; } });
  if(hit) fzPendWrite(map);
}
/* Заход на вкладку «Неделя»: если страховка не пуста - предлагаем дозаписать.
   Молча дописывать нельзя: минуты могли не записаться именно потому, что план
   уже поменяли из другого окна, и владелец должен это увидеть. */
function fzRecoverPending(){
  const map = fzPendRead();
  const ids = Object.keys(map);
  if(!ids.length || !DATA) return;
  const live = [], drop = [];
  const oldest = Date.now() - FZ_PEND_TTL * 864e5;
  ids.forEach(id=>{
    const rec = map[id] || {};
    const e = DATA.events.find(x=>x.id === id);
    if(!e || (+rec.ts || 0) < oldest) return drop.push(id);            // задачи нет либо запись протухла
    if(Math.round(+e.focusMin || 0) >= Math.round(+rec.want || 0)) return drop.push(id);  // уже засчитано
    live.push({rec, e});
  });
  fzPendDrop(drop);
  if(!live.length) return;
  const total = live.reduce((s, x)=> s + Math.max(0, +x.rec.mins || 0), 0);
  const names = live.slice(0, 3).map(x=> '«' + (x.e.title || x.rec.title || 'задача') + '»').join(', ');
  notifyAction(
    'Минуты фокуса не записались: ' + total + ' мин по ' + names +
      (live.length > 3 ? ' и ещё ' + (live.length - 3) : '') + '. Дописать в задачи?',
    'Дописать',
    ()=>{
      live.forEach(x=>{ x.e.focusMin = Math.max(0, Math.min(1440, Math.round(+x.rec.want || 0))); });
      save('дозапись минут фокуса (' + total + ' мин)');
      render();
      notify('Дописал ' + total + ' мин фокуса. Страховку сниму, как сервер подтвердит запись', 'ok', 5000);
    },
    20000);
}

function fzOn(){ return !!(fz && $('wk-fz')); }
/* сколько уже отсидели. Больше заказанного окна не засчитываем никогда */
function fzElapsed(){
  if(!fz) return 0;
  const live = fz.since ? Math.max(0, Date.now() - fz.since) : 0;
  return Math.min(fz.totalMs, fz.accumMs + live);
}
function fzLeft(){ return fz ? Math.max(0, fz.totalMs - fzElapsed()) : 0; }
function fzMinutes(){ return Math.round(fzElapsed()/60000); }
function fzClock(ms){
  const s = Math.max(0, Math.round(ms/1000));
  return pad(Math.floor(s/60)) + ':' + pad(s%60);
}
/* дефолт = min(80 минут, остаток длительности задачи с учётом прошлых сессий) */
function fzDefaultMin(e){
  const dur = Math.max(0, +e.dur || 0);
  const had = Math.max(0, +e.focusMin || 0);
  const rest = dur - had;
  const base = rest > 0 ? rest : (dur > 0 ? dur : FZ_DEF);
  return Math.max(FZ_MIN, Math.min(FZ_DEF, Math.round(base)));
}

function fzOpen(id){
  if(!DATA) return;
  if(fzOn()) return;                                   // оверлей уже на экране
  const e = DATA.events.find(x=>x.id === id);
  if(!e) return notify('Задача не найдена: фокус не с чем запускать', 'err');
  qaClose();
  closePanel();
  const mins = fzDefaultMin(e);
  fz = {id, totalMs: mins*60000, accumMs: 0, since: Date.now(), timer: null, fired: false};

  const tr = (DATA.tracks[e.track] || {});
  const box = document.createElement('div');
  box.className = 'wk-fz';
  box.id = 'wk-fz';
  box.innerHTML = `
    <div class="wk-fzbox" role="dialog" aria-label="Фокус на задаче">
      <div class="wk-fzlb"><i style="background:${color(tr.color)}"></i>Фокус${
        tr.label ? ' · ' + esc(tr.label) : ''}</div>
      <div class="wk-fzttl">${esc(e.title)}</div>
      <div class="wk-fztime" id="wk-fztime">${fzClock(fz.totalMs)}</div>
      <div class="wk-fzbarbox"><div class="wk-fzbar" id="wk-fzbar"></div></div>
      <div class="wk-fzsub" id="wk-fzsub"></div>
      <div class="wk-fzacts">
        <button type="button" class="pa" id="wk-fzpause">Пауза</button>
        <button type="button" class="st" id="wk-fzstop">Стоп</button>
      </div>
      <div class="wk-fzadj">
        <button type="button" id="wk-fzminus">-${FZ_STEP} мин</button>
        <button type="button" id="wk-fzplus">+${FZ_STEP} мин</button>
      </div>
      <div class="wk-fzesc">Escape - выйти из фокуса</div>
    </div>`;
  document.body.appendChild(box);
  $('wk-fzpause').addEventListener('click', fzToggle);
  $('wk-fzstop').addEventListener('click', fzStop);
  $('wk-fzminus').addEventListener('click', ()=>fzShift(-FZ_STEP));
  $('wk-fzplus').addEventListener('click', ()=>fzShift(FZ_STEP));
  fz.timer = setInterval(fzTick, 250);
  fzRender();
  render();                                            // задача в сетке подсветится «в фокусе»
}

function fzSubText(){
  if(!fz) return '';
  const e = DATA.events.find(x=>x.id === fz.id);
  const had = e ? Math.max(0, +e.focusMin || 0) : 0;
  const bits = [];
  if(fz.fired) bits.push('Время вышло');
  else if(!fz.since) bits.push('Пауза');
  else bits.push('Окно ' + Math.round(fz.totalMs/60000) + ' мин');
  bits.push('в этой сессии ' + fzMinutes() + ' мин');
  if(had > 0) bits.push('раньше накоплено ' + had + ' мин');
  if(e) bits.push('план задачи ' + Math.max(0, Math.round(+e.dur || 0)) + ' мин');
  return bits.join(' · ');
}
function fzRender(){
  const box = $('wk-fz');
  if(!box || !fz) return;
  const t = $('wk-fztime');
  if(t) t.textContent = fzClock(fzLeft());
  const bar = $('wk-fzbar');
  if(bar) bar.style.width = (fz.totalMs > 0 ? Math.min(100, 100*fzElapsed()/fz.totalMs) : 0) + '%';
  const sub = $('wk-fzsub');
  if(sub) sub.textContent = fzSubText();
  const p = $('wk-fzpause');
  if(p){
    p.textContent = fz.since ? 'Пауза' : 'Продолжить';
    p.disabled = !!fz.fired;
  }
  const st = $('wk-fzstop');
  if(st) st.textContent = fz.fired ? 'Записать и выйти' : 'Стоп';
  box.classList.toggle('paused', !fz.since && !fz.fired);
}
function fzTick(){
  if(!fz || !$('wk-fz')) return;
  if(fz.since && !fz.fired && fzLeft() <= 0) fzFire();
  fzRender();
}
function fzToggle(){
  if(!fz || fz.fired) return;
  if(fz.since){ fz.accumMs = fzElapsed(); fz.since = null; }
  else fz.since = Date.now();
  fzRender();
}
/* «-5 / +5»: окно можно поджать или продлить прямо на ходу. Продление после
   звонка снимает флаг «время вышло» и снова запускает счёт. */
function fzShift(n){
  if(!fz) return;
  const want = fz.totalMs + n*60000;
  fz.totalMs = Math.max(FZ_MIN*60000, Math.min(FZ_MAX*60000, want));
  if(n > 0 && fz.fired){
    fz.fired = false;
    fz.since = Date.now();
    const box = $('wk-fz');
    if(box) box.classList.remove('fire');
  }
  fzRender();
}
/* время вышло: замораживаем счёт, вспышка и звук */
function fzFire(){
  fz.accumMs = fz.totalMs;
  fz.since = null;
  fz.fired = true;
  const box = $('wk-fz');
  if(box) box.classList.add('fire');
  fzBeep();
  if(navigator.vibrate) try{ navigator.vibrate([140, 90, 140]); }catch(e){}
  fzRender();
}
/* звук без внешних файлов: три коротких тона через WebAudio */
function fzBeep(){
  try{
    const AC = window.AudioContext || window.webkitAudioContext;
    if(!AC) return;
    const ctx = new AC();
    const t0 = ctx.currentTime;
    [0, 0.32, 0.64].forEach((dt, i)=>{
      const o = ctx.createOscillator(), g = ctx.createGain();
      o.type = 'sine';
      o.frequency.setValueAtTime(i === 2 ? 660 : 880, t0 + dt);
      g.gain.setValueAtTime(0.0001, t0 + dt);
      g.gain.exponentialRampToValueAtTime(0.22, t0 + dt + 0.02);
      g.gain.exponentialRampToValueAtTime(0.0001, t0 + dt + 0.22);
      o.connect(g); g.connect(ctx.destination);
      o.start(t0 + dt); o.stop(t0 + dt + 0.25);
    });
    setTimeout(()=>{ try{ ctx.close(); }catch(e){} }, 1600);
  }catch(e){ /* звук - приятное дополнение, без него фокус работает */ }
}
/* закрыть оверлей, ничего не записывая */
function fzClose(){
  if(fz && fz.timer) clearInterval(fz.timer);
  fz = null;
  const box = $('wk-fz');
  if(box) box.remove();
}
/* Escape: пока таймер идёт - спрашиваем, минуты при этом не теряем */
function fzEscape(){
  if(!fz) return fzClose();
  if(fz.since && !fz.fired){
    const m = fzMinutes();
    const ask = 'Таймер идёт. Выйти из фокуса?' + (m >= 1 ? '\nНакопленные ' + m + ' мин запишу в задачу' : '');
    if(!window.confirm(ask)) return;
  }
  fzStop();
}
function fzStop(){
  if(!fz) return fzClose();
  const id = fz.id, mins = fzMinutes();
  fzClose();
  const e = DATA && DATA.events.find(x=>x.id === id);
  if(!e){
    render();
    return notify('Задача пропала, пока шёл фокус: записывать минуты некуда', 'err', 6000);
  }
  if(mins < 1){
    render();
    return notify('Фокус короче минуты не записываю', null, 3500);
  }
  const want = Math.max(0, Math.min(1440, Math.round((+e.focusMin || 0) + mins)));
  fzPendPut(id, e.title, mins, want);          // страховка ДО мутации и до сети
  e.focusMin = want;
  save('фокус по «' + e.title + '» (' + mins + ' мин)');
  render();
  fzAskActual(e, mins);
}
/* «Записать N минут как факт?» - один тап да, поправить число, позже */
function fzAskActual(e, sessionMin){
  qaClose();
  const total = Math.max(0, +e.focusMin || 0);
  const box = document.createElement('div');
  box.className = 'wk-modal';
  box.id = 'wk-modal';
  box.innerHTML = `
    <div class="wk-dlg" role="dialog" aria-label="Записать факт">
      <h3>Записать ${total} мин как факт?</h3>
      <div class="wk-hint">«${esc(e.title)}» · в этой сессии ${sessionMin} мин, всего в фокусе ${total} мин${
        total !== sessionMin ? ' (с прошлыми заходами)' : ''}. План ${hoursTxt(Math.max(0, +e.dur||0))}${
        isFinite(+e.actual) && +e.actual > 0 ? ' · сейчас в факте ' + hoursTxt(+e.actual) : ''}</div>
      <div class="acts">
        <button type="button" class="ok" id="fz-yes">Да, записать ${total} мин</button>
        <button type="button" class="no" id="fz-edit">Поправить число</button>
        <button type="button" class="no" id="fz-later">Позже</button>
      </div>
    </div>`;
  document.body.appendChild(box);
  $('fz-yes').addEventListener('click', ()=>{
    if(!(+e.est > 0)) e.est = Math.max(0, +e.dur || 0);     // план фиксируем, иначе коэффициент врёт
    e.actual = total;
    qaClose();
    save('факт из фокуса по «' + e.title + '»');
    render();
    const f = estFactor();
    notify('Факт: ' + hoursTxt(total) + ' против плана ' + hoursTxt(+e.est || +e.dur || 0) +
           (f ? '\nТвой коэффициент оценки: ×' + f.k.toFixed(2) + ' по ' + f.n + ' задачам' : ''), 'ok', 7000);
  });
  $('fz-edit').addEventListener('click', ()=>{ qaClose(); askActual(e, null, total); });
  $('fz-later').addEventListener('click', ()=>{
    qaClose();
    notify('Минуты фокуса записал в задачу, факт не трогал: ' + total + ' мин накоплено', null, 5000);
  });
  box.addEventListener('mousedown', ev=>{ if(ev.target === box) qaClose(); });
}

/* ================= SOMEDAY и TTL в бэклоге =================
   Полоса «Не разложено» показывает только активные записи (status anytime).
   Отложенные прячутся за ссылкой-счётчиком, но как только их TTL истёк -
   всплывают обратно с янтарным бейджем «пора решить»: отложить навсегда и
   молча забыть нельзя. */
let somedayOpen = false;

function blStatus(b){ return (b && b.status === 'someday') ? 'someday' : 'anytime'; }
function ttlOverdue(b){
  return blStatus(b) === 'someday' && isDate(b.ttl) && b.ttl <= iso(new Date());
}
function blVisible(b){ return blStatus(b) === 'anytime' || ttlOverdue(b); }
function blHidden(b){ return blStatus(b) === 'someday' && !ttlOverdue(b); }
function blPrio(b){
  const p = b && b.priority;
  const n = +p;
  return (p === null || p === undefined || p === '' || !isFinite(n)) ? null : Math.max(0, Math.min(9, Math.round(n)));
}
/* переписать поля записи бэклога из открытой формы раскладки чипа */
function blFromForm(b){
  const t = ($('qa-title').value || '').trim();
  if(t) b.title = t;
  const rawHours = parseFloat(String($('qa-dur').value).replace(',', '.'));
  if(isFinite(rawHours) && rawHours > 0) b.est = clampDur(Math.round(rawHours*60), false);
  if($('qa-track')) b.track = $('qa-track').value;
  const p = $('qa-prio') ? String($('qa-prio').value).trim() : '';
  if(p === ''){ delete b.priority; }
  else{
    const n = Math.round(+p);
    b.priority = isFinite(n) ? Math.max(0, Math.min(9, n)) : 0;
  }
  const d = $('qa-due') ? $('qa-due').value : '';
  if(isDate(d)) b.due = d; else delete b.due;
  return b;
}
function blChip(b){
  const c = color((DATA.tracks[b.track]||{}).color);
  const est = Math.max(0, +b.est || 0);
  const sd = blStatus(b) === 'someday';
  const over = ttlOverdue(b);
  const prio = blPrio(b);
  const bits = [est ? hoursTxt(est) : 'без оценки'];
  if(prio != null) bits.push('p' + prio);
  if(isDate(b.due)) bits.push('дедлайн ' + shortDate(b.due));
  if(sd && isDate(b.ttl)) bits.push('TTL ' + shortDate(b.ttl));
  if(b.when) bits.push(b.when);
  const tip = over
    ? 'Срок отложенной задачи вышел ' + shortDate(b.ttl) + ': пора решить - разложить, переписать TTL или удалить'
    : (sd ? 'Отложена (someday)' + (isDate(b.ttl) ? ', вернётся ' + shortDate(b.ttl) : ', без срока') + '. Тап - разложить или вернуть в активные'
          : 'Тап - разложить или удалить, долгое нажатие - перетащить');
  return `<span class="chip${sd ? ' wk-chip-sd' : ''}${over ? ' wk-chip-ttl' : ''}" draggable="true"
            data-bid="${esc(b.id)}" title="${esc(tip)}">
          <i style="display:inline-block;width:8px;height:8px;border-radius:2px;background:${c};margin-right:6px"></i>
          ${esc(b.title)}${over ? '<em class="wk-badge">пора решить</em>' : (sd ? '<em class="wk-badge sd">someday</em>' : '')}
          <small>· ${esc(bits.join(' · '))}</small></span>`;
}
function renderBacklog(){
  const box = $('backlog');
  if(!box) return;
  const vis = DATA.backlog.filter(blVisible);
  const hid = DATA.backlog.filter(blHidden);
  const due = vis.filter(ttlOverdue).length;
  box.innerHTML = '<b>Не разложено</b>' +
    (due ? `<span class="wk-blnote" title="У этих записей вышел срок отложки">пора решить: ${due}</span>` : '') +
    vis.map(blChip).join('') +
    (hid.length
      ? `<button type="button" class="chip wk-sdbtn${somedayOpen ? ' on' : ''}" id="wk-sdtoggle"
           title="Отложенные записи: лежат вне полосы, пока не истечёт TTL">${
           somedayOpen ? '▾' : '▸'} Someday (${hid.length})</button>`
      : '') +
    (somedayOpen ? hid.map(blChip).join('') : '') +
    `<span class="chip wk-chipadd" id="wk-chipadd">+ в «Не разложено»</span>`;
}

/* ================= РАСКЛАДКА: контекст для автопланировщика =================
   B собирает контекст и применяет ответ, C (autoplan.js) считает раскладку и
   ничего не пишет. Единицы времени - МИНУТЫ от полуночи (0-1440), даты - ISO. */
function weekKeys(){
  return [...Array(7)].map((_,i)=>{ const d = new Date(weekStart); d.setDate(d.getDate()+i); return iso(d); });
}
/* дни вперёд от сегодня, защищённые не отдаём вовсе */
function planDates(){
  const todayK = iso(new Date());
  let keys = weekKeys().filter(k=>k >= todayK);
  if(!keys.length) keys = [...Array(7)].map((_,i)=>addDays(todayK, i));
  return keys.filter(k=>!isProtectedDay(k));
}
function planZone(k){
  const p = PROFILE || {};
  const w = workWindow();
  const work = w ? [w.from, w.to]
                 : [tmin(p.workStart || '09:00'), tmin(p.workEnd || '21:00')];
  const blocked = [];
  const add = (a, b)=>{
    a = Math.max(0, Math.round(a)); b = Math.min(DAY_END, Math.round(b));
    if(b > a) blocked.push([a, b]);
  };
  // границы суток: ночь, утро до работы, вечер после работы (wind down и сон)
  const wake = p.wake ? tmin(p.wake) : null;
  if(wake != null) add(0, wake); else add(0, work[0]);
  if(wake != null && work[0] > wake) add(wake, work[0]);
  add(work[1], DAY_END);
  const sleep = p.sleep ? tmin(p.sleep) : null;
  if(sleep != null && sleep < work[1]) add(sleep, DAY_END);
  // еда
  const cfg = rhythmCfg();
  if(cfg.lunchDur > 0) add(cfg.lunch, cfg.lunch + cfg.lunchDur);
  if(cfg.dinnerDur > 0) add(cfg.dinner, cfg.dinner + cfg.dinnerDur);
  // тренировка
  const t = trainingFor(k);
  if(t) add(t.start, t.end);
  // уже занятое: события этого дня и хвост вчерашнего через полночь
  DATA.events.forEach(e=>{
    const dur = Math.max(0, +e.dur || 0);
    if(e.date === k) add(tmin(e.start), tmin(e.start) + dur);
    else if(e.date === addDays(k, -1)){
      const over = tmin(e.start) + dur - DAY_END;
      if(over > 0) add(0, Math.min(over, DAY_END));
    }
  });
  // сегодня: прошедшее время дня закрыто, назад не планируем
  if(k === iso(new Date())) add(0, Math.ceil(nowMin()/15)*15);
  blocked.sort((a, b)=>a[0] - b[0]);
  const merged = [];
  blocked.forEach(r=>{
    const last = merged[merged.length-1];
    if(last && r[0] <= last[1]) last[1] = Math.max(last[1], r[1]);
    else merged.push([r[0], r[1]]);
  });
  const peak = peakWindow(), dip = dipWindow();
  const cap = dayCapacity();
  const norm = cap ? Math.round(cap.norm) : Math.round((work[1] - work[0]) * 0.6);
  const load = Math.round(dayLoad(k));
  return {
    work,
    blockedRanges: merged,
    peak: peak ? [peak.from, peak.to] : null,
    dip: dip ? [dip.from, dip.to] : null,
    /* capacityMin - НОРМА ДНЯ ЦЕЛИКОМ (dayCapacity: рабочее окно × capacityPercent).
       Занятое планировщик вычитает сам по ctx.events, поэтому остаток сюда класть
       нельзя - вычлось бы дважды и всё улетело бы в skipped. Остаток отдаём
       отдельным полем, справочно. */
    capacityMin: norm,
    capacityFreeMin: Math.max(0, norm - load),  // сколько ещё влезает, справочно
    loadMin: load,                              // уже занято планом
    dow: dowOf(k),
  };
}
/* глубокая копия без служебных полей: планировщик наши данные не мутирует */
function planCopy(v){
  return JSON.parse(JSON.stringify(v, (k, x)=> (k && k.charAt(0) === '_') ? undefined : x));
}
function buildPlanCtx(){
  const dates = planDates();
  const zones = {};
  dates.forEach(k=>{ zones[k] = planZone(k); });
  return {
    today: iso(new Date()),
    nowMin: nowMin(),
    dates,
    events: planCopy(DATA.events),
    backlog: planCopy(DATA.backlog.filter(b=>blStatus(b) === 'anytime' && !b.done)),
    profile: planCopy(PROFILE || {}),
    zones,
  };
}

/* ---------- кнопка «Разложить»: превью, потом запись ---------- */
function openAutoPlan(){
  if(!DATA) return;
  const AP = window.AutoPlan;
  if(!AP || typeof AP.propose !== 'function')
    return notify('Планировщик ещё не подключён: файла autoplan.js на странице нет.\nКнопка заработает, как только он приедет', 'err', 7000);
  const ctx = buildPlanCtx();
  if(!ctx.dates.length)
    return notify('Раскладывать некуда: впереди в этой неделе нет ни одного незащищённого дня', 'err', 6000);
  if(!ctx.backlog.length)
    return notify('В «Не разложено» нет активных записей: someday планировщику не отдаю', null, 5000);
  let out = null;
  try{
    out = AP.propose(ctx);
  }catch(err){
    return notify('Планировщик упал: ' + ((err && err.message) || err) + '\nДанные не тронуты', 'err', 9000);
  }
  if(!out || typeof out !== 'object')
    return notify('Планировщик вернул пустой ответ, раскладывать нечего', 'err', 6000);
  const placements = Array.isArray(out.placements) ? out.placements : [];
  const skipped = Array.isArray(out.skipped) ? out.skipped : [];
  const notes = Array.isArray(out.notes) ? out.notes : [];
  showPlanPreview(placements, skipped, notes, ctx);
}

function planRowText(p){
  const b = DATA.backlog.find(x=>x.id === p.backlogId);
  const title = b ? b.title : ('запись ' + (p.backlogId || '?'));
  const start = typeof p.start === 'number' ? hhmm(Math.max(0, Math.min(DAY_END, Math.round(p.start)))) : String(p.start || '');
  const dur = clampDur(+p.dur || (b ? +b.est : 0) || 60, false);
  const end = hhmm(Math.min(DAY_END, tmin(start) + dur));
  const d = isDate(p.date) ? p.date : '';
  const dow = d ? (DOW_RU[dowOf(d)] || '') : '';
  return {title, when: (d ? dow + ' ' + shortDate(d) : 'дата не распознана') + ' · ' + start + '-' + end + ' · ' + dur + ' мин'};
}
function showPlanPreview(placements, skipped, notes, ctx){
  qaClose();
  const sdCount = DATA.backlog.filter(blHidden).length;
  const box = document.createElement('div');
  box.className = 'wk-modal';
  box.id = 'wk-modal';
  box.innerHTML = `
    <div class="wk-dlg wk-plandlg" role="dialog" aria-label="Раскладка бэклога">
      <h3>Разложить: что предлагает движок</h3>
      <div class="wk-hint">Дни: ${ctx.dates.map(shortDate).join(', ') || 'нет'} · защищённые не в счёт${
        sdCount ? ' · someday (' + sdCount + ') не раскладываю' : ''}</div>
      ${notes.length ? `<div class="wk-plannotes">${notes.map(n=>`<div>· ${esc(String(n))}</div>`).join('')}</div>` : ''}
      <div class="wk-plansec"><b>Встанет: ${placements.length}</b></div>
      <div class="wk-planlist">${placements.length
        ? placements.map(p=>{
            const r = planRowText(p);
            return `<div class="wk-planrow"><span class="t">${esc(r.title)}</span>
                    <span class="w">${esc(r.when)}</span>
                    ${p.reason ? `<span class="r">${esc(String(p.reason))}</span>` : ''}</div>`;
          }).join('')
        : '<div class="wk-planempty">ничего не встало</div>'}</div>
      ${skipped.length ? `<div class="wk-plansec"><b>Не встало: ${skipped.length}</b></div>
        <div class="wk-planlist skip">${skipped.map(s=>{
          const b = DATA.backlog.find(x=>x.id === s.backlogId);
          return `<div class="wk-planrow"><span class="t">${esc(b ? b.title : (s.backlogId || '?'))}</span>
                  <span class="r">${esc(String(s.why || 'без причины'))}</span></div>`;
        }).join('')}</div>` : ''}
      <div class="acts">
        <button type="button" class="ok" id="pl-ok"${placements.length ? '' : ' disabled'}>Применить</button>
        <button type="button" class="no" id="pl-cancel">Отмена</button>
      </div>
    </div>`;
  document.body.appendChild(box);
  $('pl-cancel').addEventListener('click', qaClose);
  if(placements.length) $('pl-ok').addEventListener('click', ()=>{ qaClose(); applyPlacements(placements); });
  box.addEventListener('mousedown', ev=>{ if(ev.target === box) qaClose(); });
}

/* Применение: один батч через СВОЙ save() - значит одна запись в истории, и
   Cmd+Z откатывает всю раскладку целиком. Каждое размещение проверяем сами:
   защищённый день, тренировка, границы суток. Что не прошло - говорим вслух. */
function applyPlacements(list){
  const okList = [], bad = [], soft = [];
  list.forEach(p=>{
    const b = DATA.backlog.find(x=>x.id === (p && p.backlogId));
    if(!b){ bad.push('запись ' + ((p && p.backlogId) || '?') + ' в бэклоге не найдена'); return; }
    if(!isDate(p.date)){ bad.push('«' + b.title + '»: дата «' + p.date + '» не распознана'); return; }
    let start;
    if(typeof p.start === 'number' && isFinite(p.start)) start = Math.round(p.start);
    else if(/^\d{1,2}:\d{2}$/.test(String(p.start || ''))) start = tmin(p.start);
    else { bad.push('«' + b.title + '»: время «' + p.start + '» не распознано'); return; }
    const dur = clampDur(+p.dur || +b.est || 60, false);
    if(start < 0 || start + dur > DAY_END){
      bad.push('«' + b.title + '»: ' + hhmm(Math.max(0, start)) + ' + ' + dur + ' мин не помещается в сутки');
      return;
    }
    const blocked = slotBlocked(p.date, start, dur);
    if(blocked){ bad.push('«' + b.title + '»: ' + blocked); return; }
    const ev = {id: uid('e'), kind:'active', title:b.title, date:p.date, start:hhmm(start),
                dur, est: Math.max(0, +b.est || dur) || dur, track:b.track, who:'владелец'};
    const prio = blPrio(b);
    if(prio != null) ev.priority = prio;
    DATA.events.push(ev);
    DATA.backlog = DATA.backlog.filter(x=>x.id !== b.id);
    const om = overlapMsg(ev);
    if(om) soft.push(om);
    okList.push('«' + b.title + '» → ' + shortDate(p.date) + ' ' + hhmm(start));
  });

  if(!okList.length){
    render();
    return notify('Раскладка не применилась ни в одной строке:\n' + (bad.join('\n') || 'причина не пришла'), 'err', 12000);
  }
  save('раскладка бэклога: ' + okList.length + ' задач');
  render();
  const msgs = ['Разложил ' + okList.length + ':'].concat(okList.slice(0, 6));
  if(okList.length > 6) msgs.push('и ещё ' + (okList.length - 6));
  if(bad.length) msgs.push('Не встало: ' + bad.join('; '));
  if(soft.length) msgs.push(soft[0]);
  notifyAction(msgs.join('\n'), 'Отменить', undoLast, 12000);
}

/* ---------- уведомления ---------- */
let toastTimer = null;
function toastEl(){
  let t = $('wk-toast');
  if(!t){
    t = document.createElement('div');
    t.id = 'wk-toast';
    t.addEventListener('click', e=>{ if(e.target === t) t.classList.remove('on'); });
    document.body.appendChild(t);
  }
  return t;
}
function notify(text, kind, ms){
  const t = toastEl();
  t.className = 'wk-toast on ' + (kind || '');
  t.textContent = text;                       // textContent: чужой текст в разметку не попадает
  clearTimeout(toastTimer);
  toastTimer = setTimeout(()=>t.classList.remove('on'), ms || 4500);
}
/* Тост с одной кнопкой: «Отменено: перенос задачи ... [Вернуть]» */
function notifyAction(text, btn, fn, ms){
  const t = toastEl();
  t.className = 'wk-toast on act';
  t.innerHTML = '';
  const span = document.createElement('span');
  span.textContent = text;                    // текст задачи в разметку не пускаем
  t.appendChild(span);
  if(btn && fn){
    const b = document.createElement('button');
    b.type = 'button';
    b.textContent = btn;
    b.addEventListener('click', ()=>{ t.classList.remove('on'); fn(); });
    t.appendChild(b);
  }
  clearTimeout(toastTimer);
  toastTimer = setTimeout(()=>t.classList.remove('on'), ms || 7000);
}

/* ---------- стили модуля (app.css чужой, свои классы держим тут) ---------- */
function injectCSS(){
  if($('wk-css')) return;
  const s = document.createElement('style');
  s.id = 'wk-css';
  s.textContent = `
.wk-add{border:1px solid var(--blue);background:var(--blue);color:#fff;border-radius:4px;padding:8px 13px;
        font:600 13px/1 inherit;font-family:inherit;cursor:pointer;white-space:nowrap;flex:0 0 auto}
.wk-add:hover{opacity:.9}
/* переключатель «день/неделя»: на широком экране его нет вовсе, там канон - недельная сетка */
.wk-view{display:none}
.wk-goaledit,.wk-goaladd{border:1px solid var(--bd);background:#fff;color:var(--txt-dim);border-radius:4px;
        padding:3px 8px;font-size:12px;font-family:inherit;cursor:pointer;line-height:1.3}
.wk-goaledit:hover,.wk-goaladd:hover{background:var(--hover);color:var(--txt)}
.wk-goaladd{color:var(--blue);border-style:dashed}
.wk-saveerr{display:none;align-items:center;gap:8px;font-size:12px;color:#c5221f;background:#fce8e6;
            border:1px solid #f5c6c2;border-radius:4px;padding:5px 9px;max-width:40vw}
.wk-saveerr.on{display:flex}
.wk-saveerr span{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.wk-saveerr button{border:0;background:#c5221f;color:#fff;border-radius:3px;padding:4px 8px;font-size:11px;
                   cursor:pointer;font-family:inherit;flex:0 0 auto}
/* ---------- отмена: кнопки в шапке ----------
   На телефоне клавиатуры нет, значит Cmd+Z там недоступен вовсе. Кнопки
   появляются только когда есть что отменять, чтобы не занимать место зря. */
.wk-undobar{display:none}
.wk-undobar.on{display:flex;gap:4px;flex:0 0 auto}
.wk-undobar button{border:1px solid var(--bd);background:#fff;color:var(--txt);border-radius:4px;
        padding:7px 11px;font:500 12px/1 inherit;font-family:inherit;cursor:pointer;white-space:nowrap}
.wk-undobar button:hover{background:var(--hover)}
.wk-undobar button.re{padding:7px 10px;color:var(--txt-dim)}
.wk-toast.act{display:flex;align-items:center;gap:14px}
.wk-toast.act button{border:0;background:rgba(255,255,255,.16);color:#fff;border-radius:5px;
        padding:7px 12px;font:600 12px/1 inherit;font-family:inherit;cursor:pointer;flex:0 0 auto}
.wk-toast.act button:hover{background:rgba(255,255,255,.28)}
.wk-nowchip{font-size:12px;color:var(--txt);background:#fff4f3;border:1px solid #f7c6c2;border-radius:12px;
            padding:3px 10px;max-width:42vw;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.day .dcount{font-size:10px;line-height:13px;height:13px;color:var(--txt-dim);overflow:hidden;
             text-overflow:ellipsis;white-space:nowrap;padding:0 2px}
.day .dcount.all{color:var(--green);font-weight:600}
.day.wk-protday .dw,.day.wk-protday .dn{opacity:.75}
.col.wk-prot{background-image:repeating-linear-gradient(45deg,rgba(60,64,67,.055) 0,rgba(60,64,67,.055) 6px,transparent 6px,transparent 13px)}
.col.wk-over{box-shadow:inset 0 0 0 2px var(--blue)}
.wk-peak{position:absolute;left:0;right:0;z-index:0;pointer-events:none;background:rgba(26,115,232,.075);
         border-top:1px solid rgba(26,115,232,.28);border-bottom:1px solid rgba(26,115,232,.28)}
.wk-peak span{position:absolute;left:5px;top:1px;font-size:9px;letter-spacing:.5px;text-transform:uppercase;color:#1a73e8;opacity:.8}
.wk-train{position:absolute;left:2px;right:6px;z-index:0;border-radius:5px;border:1px solid var(--bd);
          background:repeating-linear-gradient(45deg,#eceff1,#eceff1 5px,#e0e3e6 5px,#e0e3e6 10px);
          color:var(--txt-dim);font-size:11px;line-height:1.25;padding:2px 6px;overflow:hidden;cursor:default}
.wk-train small{font-size:10px;opacity:.85}

/* ---------- ритм дня: зоны суток + разметка рабочего окна ----------
   Правило зрелых календарей: фон спокойный, вся яркость отдана событиям.
   Поэтому заливки почти прозрачные, границы блоков - одна волосяная линия,
   подписи мелкие и приглушённые, а при наведении на блок они проявляются.
   Полосы прозрачны для указателя (pointer-events:none): перенос задач, бросок
   чипа из бэклога и двойной клик по пустому месту работают как раньше. Ловит
   наведение только сама подпись - ради подсказки, и кнопка «поставить сюда».
   Палитра взята из static/day.html, чтобы движок и памятка говорили одинаково. */
.wk-nextstep{flex:0 0 auto;display:flex;align-items:baseline;gap:7px;padding:6px 14px;font-size:12.5px;
  background:#fffbe6;border-bottom:1px solid var(--bd-soft);color:var(--txt)}
.wk-nextstep b{font-weight:700;color:#9a6200}
.wk-nextstep small{color:var(--txt-dim);font-size:11px}
.wk-projection{flex:0 0 auto;display:flex;align-items:center;gap:6px;flex-wrap:wrap;padding:6px 14px;
  border-bottom:1px solid var(--bd-soft);font-size:12px;background:#f7f9fc}
.wk-projection>b{font-weight:700;font-size:11.5px;color:var(--txt)}
.wk-prj-toggle{cursor:pointer;user-select:none;opacity:.75}
.wk-prj-toggle:hover{opacity:1}
/* ===== КОМПАКТНАЯ ШАПКА НЕДЕЛИ (причина - решение владельца) - календарь получает верх экрана, вся техничка
   ужата до трёх тонких строк, пояснения за кнопкой «?» ===== */
.week-root:not(.wk-day1) .weekbar{padding:5px 14px;min-height:0;gap:10px}
.week-root:not(.wk-day1) .range{font-size:16px;min-width:170px}
.week-root:not(.wk-day1) .goal{max-width:52vw;line-height:1.3}
.week-root:not(.wk-day1) .goal .gtxt{display:inline-block;max-width:100%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;vertical-align:bottom;cursor:pointer}
.week-root:not(.wk-day1) .goal.full .gtxt{white-space:normal}
.wk-strip{display:flex;flex-wrap:wrap;align-items:center;column-gap:20px;row-gap:0;padding:0 4px;border-bottom:1px solid var(--bd-soft);flex:0 0 auto}
.wk-strip>.wk-nextstep,.wk-strip>.wk-projection,.wk-strip>.legend{border-bottom:0;flex:0 1 auto;padding-top:3px;padding-bottom:3px}
.wk-strip>.legend{margin-left:auto}
.legend .wk-lgd,.legend .hint{display:none}
.legend.wk-help-on .wk-lgd{display:inline}
.legend.wk-help-on .hint{display:inline;margin-left:0}
.wk-helpbtn{border:1px solid var(--bd);background:#fff;color:var(--txt-dim);border-radius:50%;width:20px;height:20px;line-height:1;font-size:12px;cursor:pointer;flex:0 0 auto}
.wk-helpbtn:hover{background:var(--hover);color:var(--txt)}
.week-root:not(.wk-day1) .day{display:flex;align-items:center;justify-content:center;gap:7px;padding:3px 2px;min-height:0}
.week-root:not(.wk-day1) .day .dw{font-size:10px;letter-spacing:.4px}
.week-root:not(.wk-day1) .day .dn{font-size:14px;line-height:22px;width:22px;height:22px;margin:0;font-weight:600}
.week-root:not(.wk-day1) .day .load,.week-root:not(.wk-day1) .day .dcount{height:auto;margin:0;font-size:10.5px}
.wk-prj-note{font-size:10.5px;color:var(--txt-dim)}
.wk-prj-chip{display:inline-flex;align-items:center;gap:6px;max-width:340px;cursor:grab;
  background:#fff;border:1px solid var(--bd);border-radius:12px;padding:3px 9px;line-height:1.25}
.wk-prj-chip .wk-prj-goal{display:block;font-size:9.5px;color:var(--txt-dim);max-width:150px;
  overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.wk-prj-count{font-size:10px;background:#e8f0fe;color:#174ea6;border-radius:8px;padding:0 6px}
.wk-prj-empty .wk-prj-count{background:#fdecea;color:#a50e0e}
.wk-goalsrc{font-size:10px;color:var(--txt-dim)}
.ev-task{display:block;font-size:9.5px;color:var(--txt-dim);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.wk-zone,.wk-seg{position:absolute;left:0;right:0;z-index:0;pointer-events:none;overflow:hidden}
.wk-zone>span,.wk-seg>span{position:absolute;right:0;pointer-events:auto;cursor:help;
        font-size:9.5px;line-height:12px;padding:2px 7px 2px 6px;white-space:nowrap;
        overflow:hidden;text-overflow:ellipsis;max-width:100%;letter-spacing:.2px}
.wk-zone>span{top:0}
.wk-seg>span small{font-size:9px;opacity:.72;font-weight:400}

/* ---- зоны суток: приглушённые, без единой яркой краски ---- */
.wk-z-pre{background-color:rgba(60,64,67,.06)}
.wk-z-pre>span{color:#9aa0a6}
.wk-z-morning{background-color:rgba(60,64,67,.035);border-bottom:1px solid rgba(60,64,67,.14)}
.wk-morning{background:repeating-linear-gradient(45deg,rgba(190,74,36,.05),rgba(190,74,36,.05) 6px,rgba(190,74,36,.10) 6px,rgba(190,74,36,.10) 12px);border-color:rgba(190,74,36,.35);color:#8a3f1f;font-weight:600}
.wk-z-morning>span{color:#8a8f94}
.wk-z-wind{background-color:rgba(60,64,67,.055);border-top:1px solid rgba(60,64,67,.16)}
.wk-z-wind>span{color:#80868b}
.wk-z-lunch,.wk-z-dinner{background:repeating-linear-gradient(45deg,rgba(15,157,88,.05),rgba(15,157,88,.05) 6px,rgba(15,157,88,.11) 6px,rgba(15,157,88,.11) 12px)}
.wk-z-lunch>span,.wk-z-dinner>span{color:#137333;font-weight:600}
.wk-z-sleep{background-color:rgba(32,33,36,.12);border-top:1px solid rgba(32,33,36,.28)}
.wk-z-sleep>span{color:#5f6368;font-weight:600}

/* ---- блоки: номер сверху, окно фокуса снизу, тон по нагрузке ---- */
.wk-s-block{border-top:1px solid rgba(60,64,67,.17);transition:background-color .14s}
.wk-s-block>.wk-bnum{top:0;font-weight:600;color:#9aa0a6}
.wk-s-block>.wk-bnum i{font-style:normal;font-weight:500;opacity:.85;margin-left:5px;
        padding:0 5px;border-radius:8px;background:rgba(60,64,67,.08)}
.wk-s-block>.wk-bsub{bottom:0;color:#b0b4b8;font-size:9px;opacity:0;transition:opacity .14s}
.wk-s-block:hover>.wk-bsub{opacity:1}
.wk-s-block:hover>.wk-bnum{color:#5f6368}
.wk-s-block.lv-deep{background-color:rgba(190,74,36,.055);border-top-color:rgba(190,74,36,.3)}
.wk-s-block.lv-deep>.wk-bnum{color:#b8663f}
.wk-s-block.lv-deep>.wk-bnum i{background:rgba(190,74,36,.14);color:#a8471f}
.wk-s-block.lv-mech{background-color:rgba(201,138,60,.085);border-top-color:rgba(201,138,60,.34)}
.wk-s-block.lv-mech>.wk-bnum{color:#a07c37}
.wk-s-block.lv-mech>.wk-bnum i{background:rgba(19,115,51,.11);color:#137333}
.wk-s-block.lv-mid{background-color:rgba(60,64,67,.018)}
.wk-s-block.lv-buf{background-color:rgba(201,138,60,.045);border-top-style:dashed}
.wk-s-block.lv-buf>.wk-bnum i{background:rgba(201,138,60,.16);color:#8a6a1f}
/* еда и огрызки: нейтральные полосы, задачам тут не место */
.wk-s-meal{background-color:rgba(60,64,67,.07);border-top:1px solid rgba(60,64,67,.16);
        border-bottom:1px solid rgba(60,64,67,.16)}
.wk-s-meal>span{color:#7d8287;font-weight:600}
.wk-s-gap{background-color:rgba(60,64,67,.04)}
.wk-s-gap>span{color:#a3a8ac}

/* ---- перерыв внутри блока: тонкая полоса ПОВЕРХ задач ----
   Задача на два блока не должна затирать паузу между ними: полоса лежит выше
   событий, но ниже подсветки текущей задачи и ниже той, что тащат. */
.wk-brk{position:absolute;left:0;right:0;z-index:4;pointer-events:none;
        background-color:rgba(255,255,255,.34);
        background-image:repeating-linear-gradient(45deg,rgba(60,64,67,.16) 0,rgba(60,64,67,.16) 1px,transparent 1px,transparent 5px);
        border-top:1px dashed rgba(60,64,67,.42)}

/* ---- «поставить сюда»: кнопка ровно по свободной дыре фокус-окна ---- */
.wk-fill{position:absolute;left:2px;right:6px;z-index:0;border:0;background:transparent;
        border-radius:6px;padding:0;cursor:pointer;font-family:inherit;overflow:hidden;
        display:flex;align-items:center;justify-content:center;transition:background-color .13s,box-shadow .13s}
.wk-fill>span{font-size:11px;color:var(--blue);opacity:0;transition:opacity .13s;
        white-space:nowrap;overflow:hidden;text-overflow:ellipsis;padding:0 8px;text-align:center}
.wk-fill>span small{display:block;font-size:9.5px;color:#7d8287;font-weight:400}
.wk-fill:hover{background-color:rgba(26,115,232,.07);box-shadow:inset 0 0 0 1px rgba(26,115,232,.4)}
.wk-fill:hover>span{opacity:1}
.wk-fill:focus-visible{outline:2px solid var(--blue);outline-offset:-2px}
.wk-fill.tiny>span small{display:none}
.wk-fill.tiny>span{font-size:10px}


.ev.wk-cur{box-shadow:0 0 0 2px #fff,0 0 0 4px var(--red),0 2px 10px rgba(60,64,67,.35);z-index:6;
           animation:wk-pulse 2.2s ease-in-out infinite}
@keyframes wk-pulse{0%,100%{box-shadow:0 0 0 2px #fff,0 0 0 4px var(--red),0 2px 10px rgba(60,64,67,.35)}
                    50%{box-shadow:0 0 0 2px #fff,0 0 0 6px rgba(234,67,53,.45),0 2px 10px rgba(60,64,67,.35)}}
.ev.wk-spill{opacity:.5;cursor:default;
             background-image:repeating-linear-gradient(45deg,transparent,transparent 5px,rgba(255,255,255,.3) 5px,rgba(255,255,255,.3) 10px)}
.ev.wk-clip::after{content:"↓";position:absolute;right:5px;bottom:1px;font-size:11px;opacity:.95}
.ev.drag{touch-action:none}
/* кромка длительности: браузер не должен начать прокрутку до нашего preventDefault */
.ev .rz{touch-action:none}
.ev.wk-ovl{outline:2px solid #f9ab00;outline-offset:-2px}
.ev.wk-decide{box-shadow:0 0 0 2px #fff,0 0 0 4px #f9ab00,0 2px 8px rgba(60,64,67,.3);z-index:5}
.ev.wk-decide.launch{border-color:#f9ab00 !important}
.chip{touch-action:pan-x}

/* ---------- полоса «ждут решения» ---------- */
.wk-decidebar{display:none}
.wk-decidebar.on{display:flex;flex-wrap:wrap;align-items:center;gap:8px;padding:8px 16px;
        background:#fef7e0;border-bottom:1px solid #f9dc9a;font-size:12px;color:#7a5300;flex:0 0 auto}
.wk-decidebar b{font-weight:700;white-space:nowrap}
.wk-decidebar .more{color:#9a7530;font-size:11px}
.wk-dchip{border:1px solid #f0c060;background:#fff;color:#7a5300;border-radius:14px;padding:5px 11px;
        font-size:12px;font-family:inherit;cursor:pointer;max-width:60vw;overflow:hidden;
        text-overflow:ellipsis;white-space:nowrap}
.wk-dchip:hover{background:#fff6e0}
.panel .wk-decidebox{background:#fef7e0;border:1px solid #f9dc9a;border-radius:6px;padding:10px;margin-bottom:12px}
.panel .wk-decidebox b{display:block;font-size:13px;color:#7a5300;margin-bottom:3px}
.panel .wk-decidebox p{margin:0 0 9px;font-size:12px;line-height:1.4;color:var(--txt-dim)}
.panel .wk-decidebox .dacts{display:flex;flex-wrap:wrap;gap:6px}
.panel .wk-decidebox button{background:#fff;border:1px solid #f0c060;color:#7a5300;padding:7px 11px;font-size:12px}
.panel .wk-decidebox button:hover{background:#fff6e0}
.panel .wk-decidebox button.rm{border-color:var(--bd);color:var(--red)}
.panel .wk-ovlbox{background:#fef7e0;border:1px solid #f9dc9a;border-radius:6px;padding:9px 10px;
        margin-bottom:12px;font-size:12px;line-height:1.45;color:#7a5300}
.panel .wk-fact{font-size:12px;background:#e6f4ea;border-radius:6px;padding:8px 10px;margin-bottom:12px;color:#0f7a46}
.lnk{border:0;background:none;color:var(--blue);font-size:12px;font-family:inherit;cursor:pointer;padding:0;text-decoration:underline}

/* ---------- крупная карточка дня ---------- */
.wk-focus{display:none}
.wk-focus.on{display:block;padding:12px 16px;border-bottom:1px solid var(--bd-soft);
        background:linear-gradient(180deg,#f8fbff,#fff);flex:0 0 auto}
.wk-focus.decide{background:linear-gradient(180deg,#fef7e0,#fff)}
.wk-focus .lb{font-size:11px;text-transform:uppercase;letter-spacing:.7px;color:var(--txt-dim);
        display:flex;align-items:center;gap:6px}
.wk-focus .lb i{display:inline-block;width:9px;height:9px;border-radius:2px;flex:0 0 auto}
.wk-focus .lb b{color:#a06400}
.wk-focus .ttl{font:600 20px/1.25 "Unbounded",-apple-system,sans-serif;margin:5px 0 3px;
        overflow-wrap:anywhere}
.wk-focus .sub{font-size:13px;color:var(--txt-dim)}
.wk-focus .acts{display:flex;gap:8px;margin-top:10px}
.wk-focus button{border:0;border-radius:6px;padding:11px 16px;font-size:14px;font-family:inherit;cursor:pointer}
.wk-focus .ok{background:var(--green);color:#fff;font-weight:600}
.wk-focus .op{background:var(--hover);color:var(--txt)}
.wk-focus.empty .lb{text-transform:none;letter-spacing:0;font-size:14px;color:var(--txt)}
.wk-focus.empty .ok{background:var(--blue)}
.wk-chipadd{border-style:dashed;color:var(--blue);cursor:pointer}
.panel .wk-chain{font-size:12px;background:#e8f0fe;border-radius:6px;padding:9px 10px;margin-bottom:12px;line-height:1.45}
.wk-toast{position:fixed;left:50%;bottom:22px;transform:translateX(-50%) translateY(14px);z-index:400;
          max-width:min(560px,92vw);background:#3c4043;color:#fff;font-size:13px;line-height:1.45;
          padding:11px 16px;border-radius:8px;box-shadow:0 6px 20px rgba(0,0,0,.32);opacity:0;
          pointer-events:none;transition:opacity .2s,transform .2s;white-space:pre-line}
.wk-toast.on{opacity:1;transform:translateX(-50%);pointer-events:auto;cursor:pointer}
.wk-toast.err{background:#c5221f}
.wk-toast.ok{background:#0f7a46}
.wk-toast.warn{background:#9a6700}
.wk-modal{position:fixed;inset:0;z-index:300;background:rgba(32,33,36,.45);display:flex;
          align-items:flex-start;justify-content:center;padding:5vh 12px 16px;overflow-y:auto}
.wk-dlg{background:#fff;border-radius:10px;padding:18px;width:min(430px,100%);box-shadow:0 12px 34px rgba(0,0,0,.3)}
.wk-dlg h3{font:600 16px/1.3 "Unbounded",sans-serif;margin:0 0 10px}
.wk-dlg label{display:block;font-size:12px;color:var(--txt-dim);margin:10px 0 3px}
.wk-dlg input,.wk-dlg select,.wk-dlg textarea{width:100%;padding:9px;border:1px solid var(--bd);border-radius:4px;
                             font-size:16px;font-family:inherit;background:#fff;color:var(--txt)}
.wk-dlg textarea{resize:vertical;line-height:1.4}
.wk-hint{font-size:12px;color:var(--txt-dim);line-height:1.45;margin-top:8px}
.wk-dlg .row{display:flex;gap:8px}
.wk-dlg .row>div{flex:1;min-width:0}
.wk-dlg .acts{display:flex;gap:8px;margin-top:16px;flex-wrap:wrap;align-items:center}
.wk-dlg button{border:0;border-radius:4px;padding:11px 16px;font-size:14px;cursor:pointer;font-family:inherit}
.wk-dlg .ok{background:var(--blue);color:#fff;font-weight:600}
.wk-dlg .no{background:var(--hover);color:var(--txt)}
.wk-dlg .rm{background:#fff;color:var(--red);border:1px solid var(--bd);margin-left:auto;font-size:13px;padding:9px 12px}
.wk-err{color:var(--red);font-size:12px;min-height:16px;margin-top:8px;line-height:1.35}
.wk-ghost{position:fixed;z-index:350;pointer-events:none;background:#fff;border:1px solid var(--blue);
          border-radius:14px;padding:6px 12px;font-size:12px;box-shadow:0 6px 16px rgba(0,0,0,.28);
          transform:translate(-50%,-150%);white-space:nowrap;max-width:60vw;overflow:hidden;text-overflow:ellipsis}
/* ---------- фокус-режим: тёмный экран, крупные цифры, ничего лишнего ---------- */
.wk-fz{position:fixed;inset:0;z-index:500;background:#0e0f12;color:#f1f3f4;display:flex;
       align-items:center;justify-content:center;padding:24px;text-align:center;
       -webkit-user-select:none;user-select:none}
.wk-fzbox{width:min(560px,100%)}
.wk-fzlb{display:flex;align-items:center;justify-content:center;gap:8px;font-size:11px;
         letter-spacing:1.6px;text-transform:uppercase;color:#9aa0a6}
.wk-fzlb i{display:inline-block;width:9px;height:9px;border-radius:2px;flex:0 0 auto}
.wk-fzttl{font:600 27px/1.28 "Unbounded",-apple-system,sans-serif;margin:14px 0 4px;
          overflow-wrap:anywhere;color:#fff}
.wk-fztime{font:600 82px/1 "JetBrains Mono",ui-monospace,SFMono-Regular,Menlo,monospace;
           letter-spacing:2px;margin:16px 0 4px;font-variant-numeric:tabular-nums;color:#fff}
.wk-fzbarbox{height:4px;border-radius:3px;background:rgba(255,255,255,.13);overflow:hidden;margin:10px auto 12px;max-width:420px}
.wk-fzbar{height:100%;width:0;background:#8ab4f8;transition:width .25s linear}
.wk-fzsub{font-size:13px;color:#9aa0a6;line-height:1.5;min-height:20px}
.wk-fzacts{display:flex;gap:10px;justify-content:center;margin-top:20px;flex-wrap:wrap}
.wk-fzacts button{border:0;border-radius:9px;padding:15px 26px;font:600 15px/1 inherit;
                  font-family:inherit;cursor:pointer}
.wk-fzacts .pa{background:rgba(255,255,255,.12);color:#f1f3f4}
.wk-fzacts .pa:disabled{opacity:.35;cursor:default}
.wk-fzacts .st{background:#0f9d58;color:#fff}
.wk-fzadj{display:flex;gap:8px;justify-content:center;margin-top:12px}
.wk-fzadj button{border:1px solid rgba(255,255,255,.18);background:none;color:#9aa0a6;border-radius:7px;
                 padding:8px 14px;font-size:12px;font-family:inherit;cursor:pointer}
.wk-fzadj button:hover{color:#f1f3f4;border-color:rgba(255,255,255,.36)}
.wk-fzesc{margin-top:16px;font-size:11px;color:#5f6368;letter-spacing:.4px}
.wk-fz.paused .wk-fztime{color:#9aa0a6}
.wk-fz.fire{animation:wk-fzflash 1s ease-in-out 3}
.wk-fz.fire .wk-fztime{color:#ffd54f}
@keyframes wk-fzflash{0%,100%{background:#0e0f12}50%{background:#3b3400}}
/* задача, по которой прямо сейчас идёт фокус */
.ev.wk-infocus{box-shadow:0 0 0 2px #fff,0 0 0 4px #0f9d58,0 2px 10px rgba(60,64,67,.35);z-index:6}
.wk-fzchip{border:1px solid var(--bd);background:#fff;color:var(--txt);border-radius:12px;
           padding:3px 11px;font:600 11px/1.5 inherit;font-family:inherit;cursor:pointer;flex:0 0 auto}
.wk-fzchip:hover{background:var(--hover)}
.panel .wk-focusbox{font-size:12px;background:#e8f5ec;border-radius:6px;padding:8px 10px;margin-bottom:12px;color:#0f7a46}
/* кнопок в панели стало четыре: поджимаем поля, чтобы строка не рвалась,
   и всё-таки разрешаем перенос на узком экране */
.panel .acts{flex-wrap:wrap;gap:6px}
.panel .acts button{padding:9px 10px}
.bt-focus{background:#17181b;color:#fff;font-weight:600}
.bt-focus:hover{background:#2b2d31}
.wk-focus .fz{background:#17181b;color:#fff;font-weight:600}

/* ---------- someday и TTL в полосе «Не разложено» ---------- */
.wk-sdbtn{border-style:dashed;color:var(--txt-dim);cursor:pointer;font-family:inherit;font-size:12px}
.wk-sdbtn.on{color:var(--txt);border-style:solid;background:var(--hover)}
.chip.wk-chip-sd{opacity:.82;border-style:dashed}
.chip.wk-chip-ttl{border-color:#f0c060;background:#fff8e6}
.chip .wk-badge{display:inline-block;margin-left:6px;padding:1px 7px;border-radius:9px;font-style:normal;
                font-size:10px;font-weight:600;background:#fce8a8;color:#7a5300;vertical-align:1px}
.chip .wk-badge.sd{background:rgba(60,64,67,.09);color:#5f6368;font-weight:500}
.wk-blnote{font-size:11px;color:#7a5300;background:#fef7e0;border:1px solid #f9dc9a;border-radius:10px;
           padding:2px 9px;flex:0 0 auto;align-self:center}
.wk-sdrow{border:1px dashed var(--bd);border-radius:6px;padding:9px 10px;margin-top:12px;background:#fafbfc}
.wk-sdrow .wk-sdacts{display:flex;gap:8px;align-items:flex-end;margin-top:6px}
.wk-sdrow .wk-sdacts>div{flex:1;min-width:0}
.wk-sdrow button{border:1px solid var(--bd);background:#fff;color:var(--txt);border-radius:4px;
                 padding:9px 12px;font-size:13px;font-family:inherit;cursor:pointer;flex:0 0 auto}
.wk-sdrow button:hover{background:var(--hover)}

/* ---------- «Разложить»: кнопка и превью раскладки ---------- */
.wk-plan{border:1px solid var(--bd);background:#fff;color:var(--txt);border-radius:4px;padding:8px 13px;
         font:600 13px/1 inherit;font-family:inherit;cursor:pointer;white-space:nowrap;flex:0 0 auto}
.wk-plan:hover{background:var(--hover)}
.wk-plandlg{width:min(560px,100%)}
.wk-plannotes{background:#e8f0fe;border-radius:6px;padding:9px 10px;margin-top:10px;font-size:12px;
              line-height:1.5;color:var(--txt)}
.wk-plansec{margin-top:14px;font-size:13px}
.wk-planlist{max-height:34vh;overflow-y:auto;margin-top:6px;border:1px solid var(--bd);border-radius:6px}
.wk-planrow{padding:8px 10px;border-bottom:1px solid var(--bd-soft,#eee);font-size:12px;line-height:1.45}
.wk-planrow:last-child{border-bottom:0}
.wk-planrow .t{display:block;font-weight:600;color:var(--txt)}
.wk-planrow .w{display:block;color:var(--txt-dim)}
.wk-planrow .r{display:block;color:#7d8287;font-size:11px}
.wk-planlist.skip .wk-planrow .t{font-weight:500;color:var(--txt-dim)}
.wk-planempty{padding:10px;font-size:12px;color:var(--txt-dim)}

@media (max-width:600px){
  /* фокус на телефоне: цифры крупные, кнопки под палец */
  .wk-fztime{font-size:64px}
  .wk-fzttl{font-size:22px}
  .wk-fzacts button{flex:1 1 40%;padding:16px 12px}
  /* на телефоне сетка выходит за свой контейнер и накрывает бэклог: без своего
     слоя чипы не видно и пальцем до них не дотянуться */
  .backlog{position:relative;z-index:12}
  /* переключатель режима живёт только на узком экране */
  .wk-view{display:inline-block;border:1px solid var(--bd);background:#fff;color:var(--txt);
           border-radius:4px;padding:8px 12px;font:600 13px/1 inherit;font-family:inherit;
           cursor:pointer;white-space:nowrap;flex:0 0 auto}
  /* полоса «ждут решения» на телефоне - одна листаемая строка в обоих режимах:
     в столбик три чипа съедали треть экрана, а сжатые до «Пере...» ничего не говорят */
  .wk-decidebar.on{flex-wrap:nowrap;overflow-x:auto;padding:6px 12px;-webkit-overflow-scrolling:touch}
  .wk-decidebar b{flex:0 0 auto;font-size:11px}
  .wk-decidebar .more{display:none}
  .wk-dchip{flex:0 0 auto;max-width:62vw}
  /* палец толще мыши: кромку длительности делаем ощутимой */
  .ev .rz{height:14px}
  .wk-focus .ttl{font-size:19px}
}

/* ---------- РЕЖИМ ОДНОГО ДНЯ ----------
   Класс wk-day1 вешается на .week-root только когда viewMode === 'day', а он
   включается только на узком экране. Поэтому правила без медиа-запроса: на
   десктопе класса нет и ни одно из них не применяется.
   !important нужен, чтобы перебить мобильный блок app.css (семь колонок по
   112px с горизонтальным скроллом) - тот файл правит другой исполнитель. */
.week-root.wk-day1 .dayrow,
.week-root.wk-day1 .autorow,
.week-root.wk-day1 .grid{grid-template-columns:var(--gut) 1fr !important;width:auto !important;min-width:0 !important}
.week-root.wk-day1{overflow:hidden !important}
.week-root.wk-day1 .scroll{overflow-y:auto !important;overflow-x:hidden !important;-webkit-overflow-scrolling:touch}
.week-root.wk-day1 .backlog{position:relative !important;width:auto !important;max-width:100% !important;box-shadow:none}
.week-root.wk-day1 .col{border-right:0}
.week-root.wk-day1 .day{padding:5px 2px 6px}
.week-root.wk-day1 .day .dn{font-size:20px;line-height:32px;width:32px;height:32px}
.week-root.wk-day1 .range{min-width:0;font-size:15px;font-weight:600}
.week-root.wk-day1 .nav button{width:38px;height:38px;font-size:20px;border:1px solid var(--bd);border-radius:8px}
.week-root.wk-day1 .ev .t{-webkit-line-clamp:3}

/* Один день на 390x844: над сеткой шесть служебных полос, и без сжатия сетке
   оставалось 58px из 844. Всё лишнее в одну строку, ничего не выкидываем:
   загрузка дня, счётчик сделанного и ленты «идёт само» остаются на месте. */
.week-root.wk-day1 .weekbar{padding:8px 12px;gap:6px 8px;min-height:0}
.week-root.wk-day1 .today-btn{padding:6px 11px;font-size:13px}
.week-root.wk-day1 .wk-add{padding:8px 11px}
.week-root.wk-day1 .range{flex:1 1 100%;order:2}
.week-root.wk-day1 .wk-add{order:3}
.week-root.wk-day1 .goal{flex:1 1 0;min-width:0;order:4;display:flex;align-items:center;gap:6px;
        font-size:12px;text-align:left;margin-left:0;max-width:none}
.week-root.wk-day1 .goal .gtxt{flex:1 1 auto;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.week-root.wk-day1 .goal button{flex:0 0 auto}
.week-root.wk-day1 .wk-focus.on{padding:9px 14px}
.week-root.wk-day1 .wk-focus .ttl{font-size:17px;margin:3px 0 2px}
.week-root.wk-day1 .wk-focus .sub{font-size:12px}
.week-root.wk-day1 .wk-focus .acts{margin-top:8px}
.week-root.wk-day1 .wk-focus button{padding:9px 14px;font-size:13px}
.week-root.wk-day1 .legend{padding:4px 12px;font-size:11px;gap:8px}
.week-root.wk-day1 .legend .wk-lgd,
.week-root.wk-day1 .wk-nowchip{display:none}      /* дубль крупной карточки */
.week-root.wk-day1 .legend .hint{margin-left:0}
.week-root.wk-day1 .day{display:flex;align-items:center;justify-content:center;gap:10px;padding:3px 4px}
.week-root.wk-day1 .day .dw,.week-root.wk-day1 .day .dn{display:none}
.week-root.wk-day1 .day .load,.week-root.wk-day1 .day .dcount{height:auto;margin:0;font-size:11px}
.week-root.wk-day1 .autorow .lbl{font-size:9px;padding-top:4px}
/* «Разложить» встаёт в ту же строку, что и «+ Задача», и жмётся так же */
.week-root.wk-day1 .wk-plan{order:3;padding:8px 10px;font-size:12px}
/* в режиме дня чип «Сейчас» спрятан, значит и кнопка фокуса при нём не нужна:
   вход в фокус живёт на крупной карточке дня */
.week-root.wk-day1 .legend .wk-fzchip{display:none}
`;
  document.head.appendChild(s);
}

window.TABS = window.TABS || {};
window.TABS.week = renderWeek;
})();

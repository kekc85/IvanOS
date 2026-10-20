/* Вкладка «План»: утренний ритуал планирования, вечернее закрытие дня и
   аналитика план/факт по трекам.

   Ритуал - конечный автомат из пяти экранов (Sunsama daily planning):
     1 Вчера      - чем кончился прошлый день + решения по застрявшим задачам
     2 Сегодня    - долг прошлых дней, задачи дня, добор из бэклога
     3 Оценки     - est на каждую задачу против ёмкости дня из профиля
     4 Порядок    - последовательность дня и одно поле «что может помешать»
     5 Старт      - итоговая карточка и кнопка «День спланирован»
   Шаг оценок пропустить нельзя: без est нечему спорить с ёмкостью, а без этого
   спора планирование превращается в список желаний.

   Границы:
   · состояние ритуалов дня живёт в ОТДЕЛЬНОМ ресурсе /api/days (карта дат в
     корне документа, ключи YYYY-MM-DD) - в sprint.json оно не лезет;
   · задачи, порядок и est пишутся в sprint.json ТОЛЬКО через App.api, каждый
     раз свежим чтением прямо перед записью, на 409 - один повтор;
   · вечернее закрытие здесь ДОБРОВОЛЬНОЕ и раннее. Машинный daily_close в 22:30
     сам переносит несделанное и сам ставит needsDecision - мы его логику НЕ
     повторяем, только показываем флаги. Закрыл день руками - машине нечего
     переносить, это и есть правильная связка.

   Всё в своей IIFE, наружу торчит только window.TABS.plan. Стили - инжект
   <style id="pl-style"> при первом рендере, классы с префиксом pl-. */

(function(){
  const U = App.utils;
  const iso = U.iso, parseISO = U.parseISO, tmin = U.mins, hhmm = U.hhmm, startOfWeek = U.startOfWeek;

  const DOW = ['sun','mon','tue','wed','thu','fri','sat'];
  const DOW_RU = {mon:'пн', tue:'вт', wed:'ср', thu:'чт', fri:'пт', sat:'сб', sun:'вс'};
  const DOW_FULL = {mon:'понедельник', tue:'вторник', wed:'среда', thu:'четверг', fri:'пятница', sat:'суббота', sun:'воскресенье'};
  const MON_RU = ['января','февраля','марта','апреля','мая','июня','июля','августа','сентября','октября','ноября','декабря'];
  const MON_NAME = ['январь','февраль','март','апрель','май','июнь','июль','август','сентябрь','октябрь','ноябрь','декабрь'];
  const DAY_END = 24 * 60;
  const DATE_RE = /^\d{4}-\d{2}-\d{2}$/;
  const EST_QUICK = [15, 30, 60, 90, 120, 180];
  const DEFAULT_EST = 30;
  const BIG3_MAX = 3;

  const esc = s => String(s == null ? '' : s)
    .replace(/&/g,'&amp;').replace(/"/g,'&quot;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  const uid = p => p + Date.now().toString(36) + Math.random().toString(36).slice(2,5);
  const $ = id => document.getElementById(id);

  function num(v){
    if(v === null || v === undefined || v === '') return null;
    const n = +v;
    return isFinite(n) ? n : null;
  }
  function clampNum(v, lo, hi, fallback){
    const n = num(v);
    if(n === null) return fallback;
    return Math.max(lo, Math.min(hi, Math.round(n)));
  }
  const todayISO = () => iso(new Date());
  const nowMin = () => { const d = new Date(); return d.getHours()*60 + d.getMinutes(); };
  function addDays(k, n){ const d = parseISO(k); d.setDate(d.getDate() + n); return iso(d); }
  function dowOf(k){ return DATE_RE.test(k) ? DOW[parseISO(k).getDay()] : 'mon'; }
  function fmtDay(k){
    if(!DATE_RE.test(k)) return k;
    const d = parseISO(k);
    return `${d.getDate()} ${MON_RU[d.getMonth()]}, ${DOW_RU[dowOf(k)]}`;
  }
  function shortDate(k){
    if(!DATE_RE.test(k)) return k;
    const d = parseISO(k);
    return `${d.getDate()} ${MON_RU[d.getMonth()].slice(0,3)}`;
  }
  function hoursTxt(m){
    const v = Math.max(0, Math.round(+m || 0));
    if(!v) return '0 мин';
    const h = Math.floor(v / 60), mm = v % 60;
    if(!h) return v + ' мин';
    if(!mm) return h + ' ч';
    return h + ' ч ' + mm + ' мин';
  }
  const plural = (n, one, few, many) => {
    const a = Math.abs(n) % 100, b = a % 10;
    if(a > 10 && a < 20) return many;
    if(b > 1 && b < 5) return few;
    if(b === 1) return one;
    return many;
  };

  /* ================== состояние модуля ================== */

  let cont = null, gen = 0;
  let DATA = null, PROFILE = null;
  let DAYS = {};                 // карта YYYY-MM-DD -> запись дня
  let DAYS_OK = false;           // ресурс /api/days доступен
  let DAYS_WRAPPED = false;      // карта лежит под ключом days (запасная форма)
  let DAY = todayISO();
  let VIEW = 'ritual';           // ritual | stats
  let W = null;                  // модель визарда
  let CLOSE = null;              // модель вечернего закрытия
  let ASK = null;                // вопрос-подтверждение перед необратимым шагом
  let busy = false;              // идёт запись - кнопки заблокированы
  let flash = null;              // строка-подсказка над экраном
  let needReload = false;        // пришло чужое изменение, пока шла запись
  const big3Cleaned = {};        // ключи дней, где мёртвые id тройки уже подчистили

  /* ================== загрузка ================== */

  function renderPlan(container){
    injectStyle();
    cont = container;
    const my = ++gen;
    container.innerHTML = '<div class="pl-loading">Загрузка дня...</div>';
    Promise.all([
      App.api.get('/api/data'),
      App.api.get('/api/profile').catch(()=>null),
      loadDays(),
    ]).then(([data, profile])=>{
      if(my !== gen) return;                 // пока грузилось, ушли на другую вкладку
      DATA = normData(data);
      PROFILE = profile;
      draw();
      flushHabitAuto();          // догоняем галочки, которые в прошлый раз не доехали
    }).catch(err=>{
      if(my !== gen) return;
      container.innerHTML = `<div class="pl-loading">Не удалось загрузить план: ${esc(err && err.message)}</div>`;
    });
  }

  /* ================== контракт волны: sprint:changed ==================
     Пишем в sprint.json - кричим об этом остальным вкладкам. Слышим чужой
     крик и, если вкладка План на экране, перечитываем данные: иначе Неделя и
     командная строка правят документ, а План продолжает считать по старому
     снимку и предлагает перенос в уже занятый слот. */

  function announce(){
    try{
      window.dispatchEvent(new CustomEvent('sprint:changed', {detail: {source: 'plan'}}));
    }catch(e){}
  }

  function planVisible(){
    if(!cont || !cont.isConnected) return false;
    const btn = document.querySelector('.tabbar button.active');
    return !!btn && btn.dataset.tab === 'plan';
  }

  function reload(){
    if(!cont) return;
    const my = ++gen;
    Promise.all([
      App.api.get('/api/data'),
      App.api.get('/api/profile').catch(()=>null),
      loadDays(),
    ]).then(([data, profile])=>{
      if(my !== gen) return;
      DATA = normData(data);
      if(profile) PROFILE = profile;
      draw();
    }).catch(()=>{});
  }

  window.addEventListener('sprint:changed', ev=>{
    const src = ev && ev.detail && ev.detail.source;
    if(src === 'plan') return;                 // свой же крик - не эхо
    if(!planVisible()) return;
    if(busy){ needReload = true; return; }     // идёт запись, перечитаем после
    reload();
  });

  function normData(d){
    const doc = d || {};
    doc.events = Array.isArray(doc.events) ? doc.events : [];
    doc.backlog = Array.isArray(doc.backlog) ? doc.backlog : [];
    doc.tracks = (doc.tracks && typeof doc.tracks === 'object') ? doc.tracks : {};
    return doc;
  }

  /* Карта дней. Ресурса может ещё не быть (сервер поднимут через минуту) -
     тогда работаем с пустым состоянием в памяти и честно об этом пишем. */
  function daysMap(doc){
    const out = {};
    if(!doc || typeof doc !== 'object') return out;
    const src = (doc.days && typeof doc.days === 'object' && !Array.isArray(doc.days)) ? doc.days : doc;
    DAYS_WRAPPED = src !== doc;
    Object.keys(src).forEach(k=>{
      if(DATE_RE.test(k) && src[k] && typeof src[k] === 'object') out[k] = src[k];
    });
    return out;
  }

  function loadDays(){
    return App.api.get('/api/days').then(doc=>{
      DAYS_OK = true;
      DAYS = daysMap(doc);
    }).catch(()=>{
      DAYS_OK = false;
      DAYS = DAYS || {};
    });
  }

  const rec = k => (DAYS && DAYS[k]) ? DAYS[k] : {};

  /* ================== запись ================== */

  /* Свежее чтение прямо перед записью: в sprint.json пишет ещё и недельная
     сетка, и вечерние ритуалы мимо HTTP. На 409 - ровно один повтор с новым
     чтением, дальше честная ошибка вместо тихой потери правки. */
  async function commit(mutate){
    const attempt = async ()=>{
      const doc = normData(await App.api.get('/api/data'));
      mutate(doc);
      await App.api.post('/api/data', doc);
      DATA = doc;
    };
    try{
      await attempt();
      App.flashSaved();
      announce();
      return true;
    }catch(err){
      if(err && err.conflict){
        try{
          await attempt();
          App.notify('Данные менялись в другом окне. Перечитал и сохранил со второй попытки, правка на месте');
          App.flashSaved();
          announce();
          return true;
        }catch(e){ return false; }
      }
      return false;
    }
  }

  function cleanDay(entry){
    const out = {};
    Object.keys(entry || {}).forEach(k=>{
      if(entry[k] === undefined) return;
      out[k] = entry[k];
    });
    return out;
  }

  /* Запись состояния ритуала. Ресурс отдельный, документ - сама карта дат,
     поэтому шлём её целиком (сервер считает пропажу ключа браком). */
  /* Привычки, которые движок ставит САМ (habit.source==='auto' в tracker.json):
     day_intent - когда владелец прошёл утренний визард, work_closed - когда закрыл день.
     Смысл: эти две вещи движок видит по факту, спрашивать про них вечером - враньё.

     Молчаливый провал здесь намеренный. Галочка привычки вторична по отношению
     к плану дня: если трекер недоступен или его правят в соседней вкладке, план
     обязан сохраниться всё равно, а не упасть вместе с ней. Один повтор на конфликт -
     read-modify-write гоняется по свежему ETag, как в saveDay. */
  async function markHabitAuto(dateKey, habitId){
    const attempt = async ()=>{
      const doc = await App.api.get('/api/track');
      if(!doc || !Array.isArray(doc.habits)) return;
      const h = doc.habits.find(x => x.id === habitId && !x.archived);
      if(!h) return;                                  // привычку сняли - молча уходим
      if(!doc.log || typeof doc.log !== 'object') doc.log = {};
      if(doc.log[dateKey] && doc.log[dateKey][habitId]) return;   // уже стоит
      if(!doc.log[dateKey]) doc.log[dateKey] = {};
      doc.log[dateKey][habitId] = true;
      await App.api.post('/api/track', doc);
    };
    /* Ошибка больше НЕ глотается молча. Раньше любой сбой кроме конфликта уходил в
       пустой catch: галочка не вставала, владелец об этом не узнавал никогда, а
       догоняющего прохода не было вовсе. Теперь неудача остаётся отложенной записью
       в localStorage, следующая загрузка вкладки её добирает, и владельцу видно
       строку, а не тишину. */
    try{ await attempt(); return true; }
    catch(err){
      if(err && err.conflict){ try{ await attempt(); return true; }catch(e){} }
      queueHabitAuto(dateKey, habitId);
      if(window.App && App.notify)
        App.notify('Галочку «' + habitId + '» за ' + dateKey + ' поставить не вышло: '
                   + ((err && err.message) || 'трекер не ответил') + '. Добью при следующем открытии вкладки');
      return false;
    }
  }

  /* очередь догона: пары дата+привычка, которые не доехали */
  const HAB_Q_KEY = 'plan-habit-auto-queue';
  function habQueue(){
    try{ const v = JSON.parse(localStorage.getItem(HAB_Q_KEY) || '[]'); return Array.isArray(v) ? v : []; }
    catch(e){ return []; }
  }
  function queueHabitAuto(dateKey, habitId){
    const q = habQueue();
    if(q.some(x => x && x.d === dateKey && x.h === habitId)) return;
    q.push({d:dateKey, h:habitId});
    try{ localStorage.setItem(HAB_Q_KEY, JSON.stringify(q.slice(-50))); }catch(e){}
  }
  async function flushHabitAuto(){
    const q = habQueue();
    if(!q.length) return;
    const left = [];
    for(const x of q){
      if(!x || !x.d || !x.h) continue;
      const ok = await markHabitAuto(x.d, x.h);
      if(!ok) left.push(x);
    }
    try{ localStorage.setItem(HAB_Q_KEY, JSON.stringify(left)); }catch(e){}
  }

  async function saveDay(dateKey, patch){
    DAYS[dateKey] = cleanDay(Object.assign({}, rec(dateKey), patch));
    if(!DAYS_OK){
      flash = 'Сохранение дня появится через минуту: ресурс /api/days ещё не поднят. Пока держу состояние в памяти вкладки';
      return false;
    }
    const attempt = async ()=>{
      const map = daysMap(await App.api.get('/api/days'));
      map[dateKey] = cleanDay(Object.assign({}, map[dateKey] || {}, patch));
      const body = DAYS_WRAPPED ? {days: map} : Object.assign({}, map);
      await App.api.post('/api/days', body);
      DAYS = map;
    };
    try{
      await attempt();
      App.flashSaved();
      return true;
    }catch(err){
      if(err && err.conflict){
        try{ await attempt(); App.flashSaved(); return true; }catch(e){}
      }
      DAYS_OK = false;
      flash = 'День не записался на сервер, состояние живёт только в этой вкладке. Обнови страницу, когда ресурс /api/days ответит';
      return false;
    }
  }

  async function withBusy(fn){
    if(busy) return false;
    busy = true;
    draw();
    let ok = false;
    try{ ok = await fn(); }
    finally{
      busy = false;
      if(needReload){ needReload = false; reload(); }
      else draw();
    }
    return ok;
  }

  /* ================== профиль: ёмкость, защищённые дни, препятствия ================== */

  function protectedDays(){
    const p = PROFILE && PROFILE.protectedDays;
    return Array.isArray(p) ? p : [];
  }
  function isProtected(k){ return protectedDays().indexOf(dowOf(k)) >= 0; }

  function capacity(){
    if(!PROFILE || !PROFILE.workStart || !PROFILE.workEnd) return null;
    const from = tmin(PROFILE.workStart), to = tmin(PROFILE.workEnd);
    const avail = to - from;
    if(avail <= 0) return null;
    const pct = typeof PROFILE.capacityPercent === 'number' ? PROFILE.capacityPercent : 60;
    return {from, to, avail, pct, norm: Math.round(avail * pct / 100)};
  }

  function trainingFor(k){
    const t = PROFILE && PROFILE.training;
    if(!t || !t.start || !Array.isArray(t.days)) return null;
    if(t.days.indexOf(dowOf(k)) < 0) return null;
    const from = tmin(t.start), dur = clampNum(t.dur, 0, 600, 60);
    return dur > 0 ? {from, to: Math.min(DAY_END, from + dur), label: 'тренировка'} : null;
  }

  function mealRanges(){
    const p = PROFILE || {};
    const out = [];
    const add = (start, dur, label)=>{
      if(!start || !/^\d{1,2}:\d{2}$/.test(String(start))) return;
      const d = clampNum(dur, 0, 240, 0);
      if(d <= 0) return;
      const a = tmin(start);
      out.push({from: a, to: Math.min(DAY_END, a + d), label});
    };
    add(p.lunchStart, p.lunchDur, 'обед');
    add(p.dinnerStart, p.dinnerDur, 'ужин');
    return out;
  }

  /* Занятые отрезки дня: жёстко закреплённые и уже сделанные задачи двигать
     нельзя, тренировка и еда из профиля - тоже не наше время. */
  function obstacles(doc, k){
    const out = [];
    (doc.events || []).forEach(e=>{
      if(e.date !== k) return;
      if(!e.fixed && !e.done) return;
      const s = tmin(e.start || '00:00');
      out.push([s, s + Math.max(1, +e.dur || 0)]);
    });
    const tr = trainingFor(k);
    if(tr) out.push([tr.from, tr.to]);
    mealRanges().forEach(m => out.push([m.from, m.to]));
    return out.sort((a,b)=>a[0]-b[0]);
  }

  function firstFree(t, dur, blocks){
    let cur = t, guard = 0, moved = true;
    while(moved && guard++ < 300){
      moved = false;
      for(let i = 0; i < blocks.length; i++){
        const b = blocks[i];
        if(cur < b[1] && cur + dur > b[0]){ cur = b[1]; moved = true; }
      }
    }
    return cur;
  }

  const ceil5 = m => Math.ceil(m / 5) * 5;

  function anchorFor(k){
    const cap = capacity();
    let a = cap ? cap.from : 9 * 60;
    if(k === todayISO()) a = Math.max(a, ceil5(nowMin()));
    return Math.min(a, DAY_END - 15);
  }

  /* Рабочее окно, за которое переносимое не выходит НИКОГДА. Верхняя граница -
     должна быть невозможна конструктивно, а не порицаема подписью. */
  function workWindow(){
    const cap = capacity();
    if(!cap) return null;
    const raw = PROFILE && PROFILE.windDown;
    const wd = (raw && /^\d{1,2}:\d{2}$/.test(String(raw))) ? tmin(raw) : null;
    const to = (wd !== null && wd > cap.from) ? Math.min(cap.to, wd) : cap.to;
    return {from: cap.from, to, workEnd: cap.to, windDown: wd, norm: cap.norm};
  }

  function busyBlocks(doc, k, extra){
    const blocks = obstacles(doc, k).slice();
    (doc.events || []).forEach(e=>{
      if(e.date !== k) return;
      const s = tmin(e.start || '00:00');
      blocks.push([s, s + Math.max(1, +e.dur || 0)]);
    });
    (extra || []).forEach(b => blocks.push(b));
    return blocks.sort((a,b)=>a[0]-b[0]);
  }

  /* Куда РЕАЛЬНО влезает переносимая задача в дне k. null - не влезает до
     конца рабочего окна. extra - куски, уже занятые в этом же заходе. */
  function fitStart(doc, k, dur, extra){
    const w = workWindow();
    const need = Math.max(1, dur);
    let floor = w ? w.from : 9 * 60;
    if(k === todayISO()) floor = Math.max(floor, ceil5(nowMin()));
    const t = firstFree(floor, need, busyBlocks(doc, k, extra));
    const limit = w ? w.to : DAY_END;
    return (t + need > limit) ? null : t;
  }

  /* Первая дата после k, куда задача влезает целиком. Защищённые дни минуем. */
  function nextFitDate(doc, k, dur, used){
    for(let i = 1; i <= 21; i++){
      const kk = addDays(k, i);
      if(isProtected(kk)) continue;
      const t = fitStart(doc, kk, dur, (used && used[kk]) || []);
      if(t !== null) return {date: kk, start: t};
    }
    return null;
  }

  /* Куда поставить новую задачу дня до того, как визард расставит порядок */
  function provisionalStart(doc, k, dur){
    const t = fitStart(doc, k, dur);
    if(t !== null) return hhmm(Math.max(0, Math.min(DAY_END - 1, t)));
    const late = firstFree(anchorFor(k), Math.max(1, dur), busyBlocks(doc, k));
    return hhmm(Math.max(0, Math.min(DAY_END - 1, late)));
  }

  /* ================== сводка дня ================== */

  function dayEventsOf(doc, k){
    return ((doc && doc.events) || []).filter(e => e.date === k && e.kind !== 'auto')
      .sort((a,b)=>tmin(a.start || '00:00') - tmin(b.start || '00:00'));
  }
  function dayEvents(k){ return dayEventsOf(DATA, k); }
  /* Точка запуска - отметка «отдал в работу», а не работа. Недельная сетка её
     в часы дня не считает (dayLoad пропускает kind launch), значит и здесь не
     считаем: иначе суммы двух экранов расходятся на ровном месте. */
  const isLaunch = e => e && e.kind === 'launch';

  function planMin(e){
    const est = num(e.est);
    return est !== null ? est : Math.max(0, +e.dur || 0);
  }
  function loadMin(e){ return isLaunch(e) ? 0 : planMin(e); }
  function factMin(e){
    const a = num(e.actual);
    return (a !== null && a > 0) ? a : null;
  }

  /* Machine-отчёт tasks/daily/*-close.md из браузера недоступен (сервер отдаёт
     только static и /api), поэтому сводку считаем по sprint.json. */
  function summaryOf(k){
    const evs = dayEvents(k);
    const done = evs.filter(e => e.done);
    const open = evs.filter(e => !e.done);
    const plan = evs.reduce((s,e)=>s + loadMin(e), 0);
    const withFact = evs.filter(e => !isLaunch(e) && factMin(e) !== null);
    const fact = withFact.reduce((s,e)=>s + factMin(e), 0);
    const gone = movedAwayFrom(k);
    return {
      evs, done, open, plan, fact, withFact, gone,
      total: evs.length,
      planned: evs.length + gone.length,   // сколько ДЕЙСТВИТЕЛЬНО стояло на день
      planTotal: plan + gone.reduce((s,e)=>s + loadMin(e), 0),
    };
  }

  /* Ближайший до k день, куда движок мог перенести задачу: защищённые минуем -
     их next_free_day вечернего ритуала тоже пропускает. */
  function prevPlanDay(k){
    for(let i = 1; i <= 7; i++){
      const kk = addDays(k, -i);
      if(!isProtected(kk)) return kk;
    }
    return addDays(k, -1);
  }

  /* Задачи, которые стояли на дне k, а сейчас стоят на другой дате. Считаем по
     origDate (его ставит перенос), а для старых записей без origDate - по паре
     «переносов > 0» + текущая дата ровно следующий рабочий день после k.
     Без этого закрытие дня переписывало вчера в свою пользу: перенёс четыре
     задачи - и утро рапортовало «сделано 2 из 2, долга нет». */
  function movedAwayFrom(k){
    if(!DATE_RE.test(String(k))) return [];
    return (DATA.events || []).filter(e=>{
      if(e.kind === 'auto' || e.date === k) return false;
      if(e.origDate === k) return true;
      if(e.origDate) return false;
      return +e.moved > 0 && String(e.date) > k && prevPlanDay(e.date) === k;
    }).sort((a,b)=>String(a.date).localeCompare(String(b.date)));
  }

  const moveCount = e => Math.max(1, clampNum(e && e.moved, 0, 99, 1));
  const movedTag = e => `переехала ${moveCount(e)}-й раз${e && e.origDate ? ' · из ' + esc(shortDate(e.origDate)) : ''}`;
  const isArrived = e => !!(e && (e.origDate && e.origDate !== e.date || +e.moved > 0));

  /* Тройка дня переживает удаление задачи: чистим мёртвые id при чтении и один
     раз за сессию подчищаем саму запись дня. */
  function big3Of(k){
    const ids = Array.isArray(rec(k).big3) ? rec(k).big3 : [];
    const live = ids.filter(id => (DATA.events || []).some(e => e.id === id));
    if(live.length !== ids.length && DAYS_OK && !big3Cleaned[k]){
      big3Cleaned[k] = true;
      saveDay(k, {big3: live});
    }
    return live;
  }

  function stuckEvents(){
    return (DATA.events || []).filter(e => e.needsDecision === true)
      .sort((a,b)=>String(a.date).localeCompare(String(b.date)));
  }

  /* Долг: не закрытое за прошлые дни. Застрявшие сюда не попадают - по ним
     решение принимается на первом шаге. */
  function debtEvents(k){
    const from = addDays(k, -21);
    return (DATA.events || []).filter(e =>
      e.kind !== 'auto' && !e.done && e.needsDecision !== true &&
      e.date < k && e.date >= from
    ).sort((a,b)=>String(a.date).localeCompare(String(b.date)));
  }

  const trackLabel = code => {
    const t = (DATA.tracks || {})[code];
    return (t && t.label) || code || 'без дорожки';
  };
  const trackColor = code => {
    const t = (DATA.tracks || {})[code];
    return (t && t.color) || '#9aa0a6';
  };
  function trackDot(code){
    return `<i class="pl-dot" style="background:${esc(trackColor(code))}"></i>`;
  }

  /* ================== модель визарда ================== */

  function newWizard(k){
    return {
      date: k,
      step: 1,
      bornOn: todayISO(),   // на каком дне визард открыли: полночь его не застанет врасплох
      stuck: {},      // eventId -> take | backlog | drop | keep
      debt: {},       // eventId -> take | backlog | skip
      today: {},      // eventId -> keep | backlog | drop
      pull: {},       // backlogId -> true
      est: {},        // eventId -> минуты
      noEst: {},      // eventId -> задача пришла из бэклога без оценки вовсе
      confirmed: {},  // eventId -> true
      order: [],      // eventId в порядке дня
      placed: {},     // eventId -> время задал сам визард (добор, перенос сюда)
      touched: {},    // eventId -> порядок этой задачи владелец трогал руками
      big3: [],
      emptyAck: false,
      obstacles: rec(k).obstacles || '',
    };
  }

  /* Визард раскладывает по часам ТОЛЬКО то, что поставил сам, и то, что
     владелец руками подвинул на шаге порядка. Задача с назначенным временем,
     которого визард не давал, стоит там, где её поставил человек. */
  function isLayout(e){
    if(!W || !e || e.fixed || e.done) return false;
    return !!(W.placed[e.id] || W.touched[e.id]);
  }
  const isAnchored = e => !isLayout(e);
  const canReorder = e => !!e && !e.fixed && !e.done;

  function wizardList(){
    return dayEvents(W.date);
  }
  function estOf(e){
    const v = num(W.est[e.id]);
    if(v !== null) return v;
    const prev = num(e.est);
    if(prev !== null && prev > 0) return prev;
    const dur = +e.dur || 0;
    return dur > 0 ? dur : DEFAULT_EST;
  }
  /* Оценку спрашиваем только там, где она есть о чём: сделанное - уже история,
     точка запуска - отметка. */
  const needEst = e => !!e && !e.done && !isLaunch(e);

  function estSource(e){
    if(num(W.est[e.id]) !== null) return 'own';
    if(W.noEst[e.id]) return 'default';          // из бэклога без оценки: цифра наша, не его
    if(num(e.est) !== null && num(e.est) > 0) return 'prev';
    return (+e.dur || 0) > 0 ? 'dur' : 'default';
  }
  function loadOfDay(){
    return wizardList().reduce((s,e)=>s + (isLaunch(e) ? 0 : estOf(e)), 0);
  }
  function capState(load){
    const cap = capacity();
    if(!cap) return {level:'none', cap:null, load};
    if(load <= cap.norm) return {level:'green', cap, load};
    if(load <= Math.round(cap.norm * 1.2)) return {level:'yellow', cap, load};
    return {level:'red', cap, load};
  }

  function orderedFrom(list){
    const byId = {};
    list.forEach(e => byId[e.id] = e);
    const out = [];
    (W.order || []).forEach(id => { if(byId[id] && out.indexOf(byId[id]) < 0) out.push(byId[id]); });
    list.forEach(e => { if(out.indexOf(e) < 0) out.push(e); });
    return out;
  }
  function orderedList(){ return orderedFrom(wizardList()); }

  const movableOf = list => list.filter(canReorder);

  /* Порядок задаёт последовательность только для того, что двигается.
     Закреплённые и сделанные стоят на своих часах и в список встают по времени -
     иначе строка «12:30» оказывалась выше строки «12:00» и день читался неверно. */
  function displayList(times){
    const list = orderedList();
    const idx = {};
    list.forEach((e,i)=>idx[e.id] = i);
    const at = e => { const t = times[e.id]; return (t === undefined || t === null) ? null : t; };
    return list.slice().sort((a,b)=>{
      const ta = at(a), tb = at(b);
      if(ta === null || tb === null || ta === tb) return idx[a.id] - idx[b.id];
      return ta - tb;
    });
  }

  const durOf = e => Math.max(1, Math.min(1440, isLaunch(e) ? (+e.dur || 1) : (+e.dur || estOf(e))));
  /* сколько места задача займёт в дне-приёмнике: оценка, а если её нет - блок */
  const durOfEvent = e => Math.max(1, Math.min(1440, isLaunch(e) ? (+e.dur || 1) : planMin(e)));

  /* Раскладка дня. Якорные (закреплённые, сделанные и те, чьё время визард не
     назначал) стоят на своих часах и занимают место. Что не влезло в рабочее
     окно - НЕ ставим в ночь, отдаём null и говорим об этом вслух. */
  function layoutTimes(doc, k){
    const ordered = orderedFrom(dayEventsOf(doc, k));
    const w = workWindow();
    const brk = clampNum(PROFILE && PROFILE.breakMin, 0, 60, 10);
    const limit = w ? w.to : DAY_END;
    const out = {};
    const blocks = obstacles(doc, k).slice();
    ordered.forEach(e=>{
      if(!isAnchored(e)) return;
      const s = tmin(e.start || '00:00');
      out[e.id] = s;
      blocks.push([s, s + durOf(e)]);
    });
    blocks.sort((a,b)=>a[0]-b[0]);
    let t = anchorFor(k);
    ordered.forEach(e=>{
      if(isAnchored(e)) return;
      const dur = Math.max(1, Math.min(1440, estOf(e)));
      const s = firstFree(t, dur, blocks);
      if(s + dur > limit){
        /* В окно не влезает. Часов не даём и в ночь не двигаем: задача
           остаётся там, где стояла, и держит своё место, чтобы сверху ничего
           не легло. Дальше идём с того же t - одна тяжёлая задача не должна
           выбивать из дня весь хвост. */
        out[e.id] = null;
        const own = tmin(e.start || '00:00');
        blocks.push([own, own + durOf(e)]);
        blocks.sort((a,b)=>a[0]-b[0]);
        return;
      }
      out[e.id] = s;
      blocks.push([s, s + dur]);
      blocks.sort((a,b)=>a[0]-b[0]);
      t = s + dur + brk;
    });
    return out;
  }

  /* Предпросчёт времён по текущему порядку - показываем на шаге 4 и 5 до записи */
  function previewTimes(){ return layoutTimes(DATA, W.date); }

  function dayEndsAt(times){
    let end = 0;
    orderedList().forEach(e=>{
      const s = times[e.id];
      if(s === undefined || s === null) return;
      end = Math.max(end, s + Math.max(1, estOf(e)));
    });
    return end;
  }
  const notFitting = times => orderedList().filter(e => times[e.id] === null);

  /* ================== мутации sprint.json ================== */

  function toBacklogItem(e){
    const est = num(e.est);
    const item = {id: uid('b'), title: e.title, status: 'anytime'};
    const minutes = est !== null && est > 0 ? est : (+e.dur || 0);
    if(minutes > 0) item.est = Math.round(minutes);
    if(e.track) item.track = e.track;
    if(e.note) item.note = e.note;
    if(num(e.priority) !== null) item.priority = clampNum(e.priority, 0, 9, 5);
    return item;
  }

  function clearStuck(e){
    delete e.needsDecision;
    delete e.stuckSince;
    e.moved = 0;
  }

  /* Откуда задача родом. Ставим один раз при первом отъезде с даты: по этому
     полю утро честно считает «переехало N», а не делает вид, что задачи
     никогда и не было. */
  function stampOrigin(e){
    if(e && !e.origDate && DATE_RE.test(String(e.date || ''))) e.origDate = e.date;
  }

  function takeToDay(doc, e, k){
    if(e.date !== k) stampOrigin(e);
    e.date = k;
    e.start = provisionalStart(doc, k, Math.max(1, +e.dur || 0));
    if(W) W.placed[e.id] = true;         // время дал визард - ему и раскладывать
    if(e.needsDecision === true) clearStuck(e);
  }

  /* шаг 1: решения по застрявшим */
  function applyStuck(doc){
    Object.keys(W.stuck).forEach(id=>{
      const verdict = W.stuck[id];
      const e = doc.events.find(x => x.id === id);
      if(!e) return;
      if(verdict === 'take'){ takeToDay(doc, e, W.date); }
      else if(verdict === 'backlog'){
        doc.backlog.push(toBacklogItem(e));
        doc.events = doc.events.filter(x => x.id !== id);
      }else if(verdict === 'drop'){
        doc.events = doc.events.filter(x => x.id !== id);
      }else if(verdict === 'keep'){
        // «оставить как есть»: флаг снимаем, задачу не двигаем - решение принято
        clearStuck(e);
      }
    });
  }

  /* шаг 2: долг прошлых дней, состав дня, добор из бэклога */
  function applyList(doc){
    Object.keys(W.debt).forEach(id=>{
      const verdict = W.debt[id];
      const e = doc.events.find(x => x.id === id);
      if(!e) return;
      if(verdict === 'take'){ takeToDay(doc, e, W.date); }
      else if(verdict === 'backlog'){
        doc.backlog.push(toBacklogItem(e));
        doc.events = doc.events.filter(x => x.id !== id);
      }
    });
    Object.keys(W.today).forEach(id=>{
      const verdict = W.today[id];
      const e = doc.events.find(x => x.id === id);
      if(!e) return;
      if(verdict === 'backlog'){
        doc.backlog.push(toBacklogItem(e));
        doc.events = doc.events.filter(x => x.id !== id);
      }else if(verdict === 'drop'){
        doc.events = doc.events.filter(x => x.id !== id);
      }
    });
    Object.keys(W.pull).forEach(bid=>{
      if(!W.pull[bid]) return;
      const item = doc.backlog.find(b => b.id === bid);
      if(!item) return;                                  // уже забрали в прошлый заход
      const est = num(item.est);
      const dur = clampNum(est !== null && est > 0 ? est : DEFAULT_EST, 1, 1440, DEFAULT_EST);
      const ev = {
        id: uid('e'),
        kind: 'active',
        title: item.title,
        date: W.date,
        start: provisionalStart(doc, W.date, dur),
        dur: dur,
        est: dur,
      };
      if(item.track) ev.track = item.track;
      if(item.note) ev.note = item.note;
      if(num(item.priority) !== null) ev.priority = clampNum(item.priority, 0, 9, 5);
      if(est === null || est <= 0) W.noEst[ev.id] = true;
      W.placed[ev.id] = true;            // задачу принёс визард - её и двигает
      doc.events.push(ev);
      doc.backlog = doc.backlog.filter(b => b.id !== bid);
    });
  }

  /* шаг 3: оценки. est - оценка, dur - блок в сетке: на планировании они
     сходятся, иначе день в сетке врёт против плана. Закреплённые и сделанные
     задачи не трогаем. */
  function applyEst(doc){
    wizardList().forEach(item=>{
      const e = doc.events.find(x => x.id === item.id);
      if(!e) return;
      if(e.done) return;         // сделанной задаче оценку не переписываем: там уже история, а не план
      if(isLaunch(e)) return;    // точка запуска - отметка, а не работа
      const v = clampNum(estOf(item), 5, 1440, DEFAULT_EST);
      e.est = v;
      if(!e.fixed) e.dur = v;
    });
  }

  /* шаг 5: порядок дня превращается в последовательность стартов.
     Между задачами - перерыв из профиля, поверх еды и тренировки не кладём. */
  function applyOrder(doc){
    const k = W.date;
    const times = layoutTimes(doc, k);
    doc.events.forEach(e=>{
      if(e.date !== k) return;
      if(isAnchored(e)) return;                  // своё время или закреплено - не трогаем
      const s = times[e.id];
      if(s === undefined || s === null) return;  // не влезло в окно - в ночь не отправляем
      e.start = hhmm(Math.max(0, Math.min(DAY_END - 1, s)));
    });
  }

  /* ================== переходы визарда ================== */

  /* Перепланирование закрытого дня стирает факт закрытия, поэтому сначала
     спрашиваем вслух, а сам closedAt при записи сохраняем. */
  function startWizard(force){
    if(!force && rec(DAY).closedAt){
      ASK = {kind: 'replan', date: DAY, closedAt: rec(DAY).closedAt};
      W = null; CLOSE = null; flash = null;
      draw();
      return;
    }
    ASK = null;
    W = newWizard(DAY);
    CLOSE = null;
    flash = null;
    draw();
  }

  /* Полночь при открытом визарде: финал раскладывал вчерашний день с 09:00.
     Дата ушла - предупреждаем и пересобираем на актуальный день. */
  function rolledOver(){
    if(!W || !W.bornOn) return false;
    const now = todayISO();
    if(now === W.bornOn || W.date !== W.bornOn) return false;
    const was = W.date;
    DAY = now;
    W = newWizard(now);
    CLOSE = null; ASK = null;
    flash = `Пока собирался план, наступил новый день. ${fmtDay(was)} уже прошёл - раскладывать его задним числом нельзя, собрал визард заново на ${fmtDay(now)}`;
    draw();
    return true;
  }

  async function wizardNext(){
    if(!W) return;
    if(rolledOver()) return;
    if(W.step === 1){
      const ok = Object.keys(W.stuck).length ? await withBusy(()=>commit(applyStuck)) : true;
      if(!ok) return;
      W.stuck = {};
      W.step = 2;
    }else if(W.step === 2){
      const dirty = Object.keys(W.debt).length || Object.keys(W.today).length || Object.keys(W.pull).length;
      const ok = dirty ? await withBusy(()=>commit(applyList)) : true;
      if(!ok) return;
      W.debt = {}; W.today = {}; W.pull = {};
      W.step = 3;
    }else if(W.step === 3){
      const list = wizardList();
      if(!list.length && !W.emptyAck){
        W.emptyAck = true;
        flash = 'Планировать нечего: на этот день не взято ни одной задачи. Вернись на шаг назад и добери из бэклога - или жми ещё раз, и я запишу пустой день как есть';
        draw();
        return;
      }
      const unconfirmed = list.filter(e => needEst(e) && !W.confirmed[e.id]);
      if(unconfirmed.length){ flash = 'Подтверди оценку на каждой задаче: без этого шага ёмкости не с чем спорить'; draw(); return; }
      const ok = await withBusy(()=>commit(applyEst));
      if(!ok) return;
      if(!W.order.length) W.order = wizardList().map(e => e.id);
      W.step = 4;
    }else if(W.step === 4){
      W.order = orderedList().map(e => e.id);
      W.step = 5;
    }
    flash = null;
    draw();
  }

  function wizardBack(){
    if(!W) return;
    if(W.step <= 1){ W = null; }
    else W.step -= 1;
    flash = null;
    draw();
  }

  async function finishWizard(){
    if(rolledOver()) return;
    W.order = orderedList().map(e => e.id);
    const big3 = (W.big3 || []).filter(id => W.order.indexOf(id) >= 0).slice(0, BIG3_MAX);
    const list = big3.length ? big3 : W.order.slice(0, BIG3_MAX);
    const obstaclesText = String(W.obstacles || '').slice(0, 2000);
    const dateKey = W.date;
    const wasClosed = rec(dateKey).closedAt || null;    // факт закрытия перепланированием не стираем
    const leftOut = notFitting(previewTimes()).length;
    const ok = await withBusy(async ()=>{
      const saved = await commit(applyOrder);
      if(!saved) return false;
      await saveDay(dateKey, {
        planned: true,
        plannedAt: hhmm(Math.min(DAY_END - 1, nowMin())),
        big3: list,
        obstacles: obstaclesText,
        closedAt: wasClosed,
        reflection: rec(dateKey).reflection || '',
      });
      return true;
    });
    if(!ok) return;
    markHabitAuto(dateKey, 'day_intent');   // намеренно без await: план уже сохранён
    W = null;
    flash = leftOut
      ? `День спланирован. ${leftOut} ${plural(leftOut,'задача осталась','задачи остались','задач остались')} на прежнем месте: в рабочее окно они не влезли, а в ночь я их не ставлю`
      : 'День спланирован. Задачи и порядок уехали в недельную сетку';
    draw();
  }

  /* ================== модель вечернего закрытия ================== */

  function newClose(k){
    return {date: k, decide: {}, dates: {}, reflection: rec(k).reflection || ''};
  }

  const closeOrder = k => summaryOf(k).open.map(e => e.id);

  /* Живой счёт нагрузки дня-приёмника. Арифметика та же, что на утреннем шаге
     оценок: ёмкость из профиля, уже стоящие события плюс переносимое. Считаем
     ДО записи и показываем прямо в списке решений - вечер больше не строит
     невозможное завтра молча. */
  function closePlan(){
    const k = CLOSE.date;
    const open = summaryOf(k).open;
    const used = {};                 // дата -> куски, занятые этим же заходом
    const items = [];
    open.forEach(e=>{
      const verdict = CLOSE.decide[e.id] || '';
      if(verdict !== 'tomorrow' && verdict !== 'date') return;
      const raw = verdict === 'tomorrow' ? addDays(k, 1) : CLOSE.dates[e.id];
      const target = DATE_RE.test(String(raw || '')) ? raw : null;
      /* dur - сколько места занять в дне, load - сколько часов прибавить к
         счётчику: точка запуска место занимает, а часами дня не считается */
      const it = {e, verdict, target, dur: durOfEvent(e), load: loadMin(e), start: null, alt: null};
      if(target){
        used[target] = used[target] || [];
        const s = fitStart(DATA, target, it.dur, used[target]);
        if(s !== null){ it.start = s; used[target].push([s, s + it.dur]); }
        else it.alt = nextFitDate(DATA, target, it.dur, used);
      }
      items.push(it);
    });

    const dates = {};
    items.forEach(it=>{
      if(!it.target) return;
      if(!dates[it.target]){
        const evs = dayEvents(it.target);
        dates[it.target] = {
          date: it.target,
          existing: evs.reduce((s,e)=>s + loadMin(e), 0),
          count: evs.length,
          incoming: 0,
          items: [],
        };
      }
      dates[it.target].incoming += it.load;
      dates[it.target].items.push(it);
    });
    Object.keys(dates).forEach(d=>{
      const box = dates[d];
      box.load = box.existing + box.incoming;
      box.st = capState(box.load);
    });

    return {
      items,
      dates,
      byId: items.reduce((m,it)=>{ m[it.e.id] = it; return m; }, {}),
      stuck: items.filter(it => it.target && it.start === null),
      over: Object.keys(dates).map(d=>dates[d]).filter(b => b.st.cap && b.load > b.st.cap.norm),
    };
  }

  function applyClose(doc){
    const k = CLOSE.date;
    const used = {};
    const order = closeOrder(k);
    Object.keys(CLOSE.decide).forEach(id => { if(order.indexOf(id) < 0) order.push(id); });
    order.forEach(id=>{
      const verdict = CLOSE.decide[id];
      if(!verdict) return;
      const e = doc.events.find(x => x.id === id);
      if(!e) return;
      if(verdict === 'tomorrow' || verdict === 'date'){
        const target = verdict === 'tomorrow' ? addDays(k, 1) : CLOSE.dates[id];
        if(!DATE_RE.test(String(target || ''))) return;
        const dur = durOfEvent(e);
        used[target] = used[target] || [];
        const s = fitStart(doc, target, dur, used[target]);
        if(s === null) return;        // в рабочее окно не влезает - в ночь не отправляем
        used[target].push([s, s + dur]);
        stampOrigin(e);
        e.date = target;
        e.start = hhmm(Math.max(0, Math.min(DAY_END - 1, s)));
        e.moved = clampNum(e.moved, 0, 99, 0) + 1;
      }else if(verdict === 'backlog'){
        doc.backlog.push(toBacklogItem(e));
        doc.events = doc.events.filter(x => x.id !== id);
      }else if(verdict === 'drop'){
        doc.events = doc.events.filter(x => x.id !== id);
      }
    });
  }

  async function finishClose(){
    const plan = closePlan();
    if(plan.stuck.length){
      const w = workWindow();
      flash = `Некуда поставить: ${plan.stuck.length} ${plural(plan.stuck.length,'задача не влезает','задачи не влезают','задач не влезают')} в день до конца рабочего окна${
        w ? ' (' + hhmm(w.to) + ')' : ''}. Выбери дату позже или бэклог - в ночь я их не поставлю`;
      draw();
      return;
    }
    const dateKey = CLOSE.date;
    const reflection = String(CLOSE.reflection || '').slice(0, 4000);
    const dirty = Object.keys(CLOSE.decide).some(id => CLOSE.decide[id]);
    const movedN = plan.items.length;
    const ok = await withBusy(async ()=>{
      if(dirty){
        const saved = await commit(applyClose);
        if(!saved) return false;
      }
      await saveDay(dateKey, {closedAt: hhmm(Math.min(DAY_END - 1, nowMin())), reflection});
      return true;
    });
    if(!ok) return;
    markHabitAuto(dateKey, 'work_closed');   // намеренно без await: день уже закрыт
    CLOSE = null;
    flash = movedN
      ? `День закрыт. ${plural(movedN,'Переехала','Переехали','Переехало')} ${movedN} ${plural(movedN,'задача','задачи','задач')} - утром придут с пометкой, откуда`
      : 'День закрыт. Машинному переносу в 22:30 останется нечего двигать';
    draw();
  }

  /* ================== аналитика план/факт ================== */

  function periodRange(kind){
    const t = new Date();
    if(kind === 'week'){
      const a = startOfWeek(t);
      const b = new Date(a); b.setDate(b.getDate() + 6);
      return {from: iso(a), to: iso(b), label: `неделя ${shortDate(iso(a))} - ${shortDate(iso(b))}`};
    }
    const a = new Date(t.getFullYear(), t.getMonth(), 1);
    const b = new Date(t.getFullYear(), t.getMonth() + 1, 0);
    return {from: iso(a), to: iso(b), label: MON_NAME[t.getMonth()] + ' ' + t.getFullYear()};
  }

  function statsFor(range){
    const evs = (DATA.events || []).filter(e =>
      e.kind !== 'auto' && e.date >= range.from && e.date <= range.to);
    const rows = {};
    const touch = code => {
      if(!rows[code]) rows[code] = {code, plan: 0, fact: 0, planPaired: 0, factPaired: 0, n: 0, nFact: 0};
      return rows[code];
    };
    evs.forEach(e=>{
      const r = touch(e.track || '');
      const plan = planMin(e), fact = factMin(e);
      r.plan += plan;
      r.n += 1;
      if(fact !== null){
        r.fact += fact;
        r.nFact += 1;
        if(plan > 0){ r.planPaired += plan; r.factPaired += fact; }
      }
    });
    const list = Object.keys(rows).map(k => rows[k]).sort((a,b)=>b.plan - a.plan);
    const total = list.reduce((acc,r)=>({
      code: '__total', plan: acc.plan + r.plan, fact: acc.fact + r.fact,
      planPaired: acc.planPaired + r.planPaired, factPaired: acc.factPaired + r.factPaired,
      n: acc.n + r.n, nFact: acc.nFact + r.nFact,
    }), {code:'__total', plan:0, fact:0, planPaired:0, factPaired:0, n:0, nFact:0});
    return {list, total, hasFact: total.nFact > 0};
  }

  const ratioOf = r => (r.planPaired > 0 && r.factPaired > 0) ? r.factPaired / r.planPaired : null;

  /* ================== рендер ================== */

  function draw(){
    if(!cont) return;
    const head = renderHead();
    let body;
    if(VIEW === 'stats') body = renderStats();
    else if(ASK) body = renderAsk();
    else if(W) body = renderWizard();
    else if(CLOSE) body = renderClose();
    else if(isProtected(DAY)) body = renderProtected();
    else body = renderOverview();
    cont.innerHTML = `<div class="pl-root">${head}${renderFlash()}${body}</div>`;
    wire();
  }

  function renderFlash(){
    const warn = DAYS_OK ? '' :
      '<div class="pl-warn">Сохранение дня появится через минуту: ресурс /api/days пока не отвечает. Планировать можно, состояние живёт в памяти вкладки</div>';
    const msg = flash ? `<div class="pl-flash">${esc(flash)}</div>` : '';
    return warn + msg;
  }

  function renderHead(){
    const r = rec(DAY);
    const state = r.closedAt ? `закрыт в ${esc(r.closedAt)}`
      : r.planned ? `спланирован${r.plannedAt ? ' в ' + esc(r.plannedAt) : ''}`
      : isProtected(DAY) ? 'защищённый день' : 'план не собран';
    return `
      <div class="pl-head">
        <div class="pl-daynav">
          <button type="button" class="pl-nav" id="pl-prev" title="Предыдущий день">‹</button>
          <div class="pl-daytitle">
            <b>${esc(fmtDay(DAY))}</b>
            <span>${DAY === todayISO() ? 'сегодня · ' : ''}${state}</span>
          </div>
          <button type="button" class="pl-nav" id="pl-next" title="Следующий день">›</button>
          ${DAY === todayISO() ? '' : '<button type="button" class="pl-today" id="pl-today">Сегодня</button>'}
        </div>
        <div class="pl-viewsw">
          <button type="button" class="${VIEW === 'ritual' ? 'on' : ''}" data-view="ritual">Ритуал</button>
          <button type="button" class="${VIEW === 'stats' ? 'on' : ''}" data-view="stats">План против факта</button>
        </div>
      </div>`;
  }

  /* ---------- вопрос перед необратимым шагом ---------- */

  function renderAsk(){
    const s = summaryOf(ASK.date);
    return `
      <div class="pl-card pl-danger">
        <h2>День уже закрыт в ${esc(ASK.closedAt || '')}</h2>
        <p class="pl-sub">Итог ${esc(fmtDay(ASK.date))} записан: сделано ${s.done.length} из ${s.planned}${
          s.gone.length ? `, переехало ${s.gone.length}` : ''}. Перепланирование пересоберёт расписание дня, а отметку о закрытии я сохраню - она не должна пропадать от того, что ты решил переразложить часы.</p>
        <div class="pl-acts">
          <button type="button" class="pl-btn pl-ok" id="pl-ask-ok">Да, перепланировать</button>
          <button type="button" class="pl-btn pl-ghost" id="pl-ask-no">Отмена</button>
        </div>
      </div>`;
  }

  /* ---------- защищённый день ---------- */

  function renderProtected(){
    return `
      <div class="pl-calm">
        <div class="pl-calm-ico">◔</div>
        <h2>День защищён</h2>
        <p>${esc(DOW_FULL[dowOf(DAY)])} помечен защищённым в настройках. Плана нет и не надо: работу сюда движок не кладёт, и ритуал тоже не просит.</p>
        <p class="pl-calm-sub">Если день всё-таки рабочий - убери его из защищённых в Настройках, а разово можно спланировать и так.</p>
        <button type="button" class="pl-btn pl-ghost" id="pl-force">Всё-таки спланировать этот день</button>
      </div>`;
  }

  /* ---------- обзор дня (до и после ритуала) ---------- */

  function renderOverview(){
    const r = rec(DAY);
    const s = summaryOf(DAY);
    const yk = addDays(DAY, -1);
    const yest = summaryOf(yk);
    const yrec = rec(yk);
    const stuck = stuckEvents();
    const cap = capacity();
    const load = s.evs.reduce((acc,e)=>acc + loadMin(e), 0);

    const big3 = big3Of(DAY).map(id => s.evs.find(e => e.id === id)).filter(Boolean);
    const yestNote = (yrec.obstacles || yrec.reflection) ? `
      <div class="pl-obst">
        <span class="pl-lbl">Вчера, ${esc(shortDate(yk))}</span>
        ${yrec.obstacles ? `<p>Риск, который назвал утром: «${esc(yrec.obstacles)}»</p>` : ''}
        ${yrec.reflection ? `<p>Итог вечером: «${esc(yrec.reflection)}»</p>` : ''}
      </div>` : '';

    const head = r.closedAt
      ? `<div class="pl-card pl-done">
           <h2>День закрыт в ${esc(r.closedAt)}</h2>
           <p>Запланировано ${s.planned}, сделано ${s.done.length}${s.gone.length ? `, переехало ${s.gone.length}` : ''}${
             s.withFact.length ? ` · факт ${hoursTxt(s.fact)} против плана ${hoursTxt(s.planTotal)}` : ''}</p>
           ${r.reflection ? `<div class="pl-reflect">«${esc(r.reflection)}»</div>` : ''}
           <div class="pl-acts">
             <button type="button" class="pl-btn pl-ghost" id="pl-reclose">Изменить итог дня</button>
             <button type="button" class="pl-btn pl-ghost" id="pl-replan">Перепланировать</button>
           </div>
         </div>`
      : r.planned
        ? `<div class="pl-card">
             <h2>День спланирован${r.plannedAt ? ' в ' + esc(r.plannedAt) : ''}</h2>
             ${yestNote}
             ${big3.length ? `<div class="pl-big3"><span class="pl-lbl">Три главных дела</span><ol>${
                big3.map(e=>`<li>${trackDot(e.track)}${esc(e.title)}</li>`).join('')}</ol></div>` : ''}
             ${r.obstacles ? `<div class="pl-obst"><span class="pl-lbl">Что может помешать</span><p>${esc(r.obstacles)}</p></div>` : ''}
             <div class="pl-acts">
               <button type="button" class="pl-btn pl-ok" id="pl-close-day">Закрыть день</button>
               <button type="button" class="pl-btn pl-ghost" id="pl-replan">Перепланировать</button>
             </div>
           </div>`
        : `<div class="pl-card pl-invite">
             <h2>План дня не собран</h2>
             <p>Пять шагов: чем кончился вчерашний день, что берём сегодня, сколько это стоит по времени, в каком порядке и что может помешать. Обычно три минуты.</p>
             ${yestNote}
             ${yest.planned ? `<p class="pl-sub">Вчера: запланировано ${yest.planned}, сделано ${yest.done.length}${
                yest.gone.length ? `, переехало ${yest.gone.length}` : ''}${
                yest.open.length ? `, осталось незакрытым ${yest.open.length}` : ''}</p>` : ''}
             ${stuck.length ? `<p class="pl-sub pl-alert">⚠ Ждут решения: ${stuck.length} ${plural(stuck.length,'задача','задачи','задач')} - разберём на первом шаге</p>` : ''}
             <div class="pl-acts">
               <button type="button" class="pl-btn pl-ok" id="pl-start">Начать планирование</button>
               ${s.total ? '<button type="button" class="pl-btn pl-ghost" id="pl-close-day">Сразу закрыть день</button>' : ''}
             </div>
           </div>`;

    const listCard = s.total ? `
      <div class="pl-card">
        <div class="pl-cardhead">
          <h3>Задачи дня · ${s.total}</h3>
          <span class="pl-load ${cap && load > cap.norm ? 'over' : ''}">${hoursTxt(load)}${cap ? ' из ' + hoursTxt(cap.norm) : ''}</span>
        </div>
        <div class="pl-list">${s.evs.map(e=>`
          <div class="pl-row ${e.done ? 'is-done' : ''}">
            <span class="pl-time">${esc(e.start)}</span>
            <span class="pl-title">${trackDot(e.track)}${esc(e.title)}${
              e.fixed ? '<span class="pl-tag">закреплено</span>' : ''}${
              isArrived(e) ? `<span class="pl-tag">${movedTag(e)}</span>` : ''}${
              e.needsDecision === true ? '<span class="pl-tag pl-tag-red">ждёт решения</span>' : ''}</span>
            <span class="pl-min">${isLaunch(e) ? 'точка запуска' : hoursTxt(planMin(e))}${
              factMin(e) !== null ? ` · факт ${hoursTxt(factMin(e))}` : ''}</span>
          </div>`).join('')}</div>
      </div>` : '';

    const goneCard = s.gone.length ? `
      <div class="pl-card">
        <div class="pl-cardhead"><h3>Уехало с этого дня · ${s.gone.length}</h3></div>
        <p class="pl-sub">Эти задачи стояли на ${esc(fmtDay(DAY))} и переехали. В счёт «сделано» они не идут</p>
        <div class="pl-list pl-thin">${s.gone.map(e=>`
          <div class="pl-row">
            <span class="pl-mark">→</span>
            <span class="pl-title">${trackDot(e.track)}${esc(e.title)}<span class="pl-tag">${movedTag(e)} · теперь ${esc(shortDate(e.date))}</span></span>
            <span class="pl-min">${hoursTxt(loadMin(e))}</span>
          </div>`).join('')}</div>
      </div>` : '';

    return head + listCard + goneCard;
  }

  /* ---------- визард ---------- */

  const STEP_TITLES = ['Вчера', 'Список сегодня', 'Оценки и ёмкость', 'Порядок и препятствия', 'Старт'];

  function renderWizard(){
    const stepper = `<div class="pl-steps">${STEP_TITLES.map((t,i)=>{
      const n = i + 1;
      const cls = n === W.step ? 'now' : n < W.step ? 'done' : '';
      return `<div class="pl-step ${cls}"><span class="pl-step-n">${n < W.step ? '✓' : n}</span><span class="pl-step-t">${esc(t)}</span></div>`;
    }).join('')}</div>`;
    const body = W.step === 1 ? stepYesterday()
      : W.step === 2 ? stepList()
      : W.step === 3 ? stepEst()
      : W.step === 4 ? stepOrder()
      : stepStart();
    return stepper + body;
  }

  function wizFoot(nextLabel, extra){
    return `<div class="pl-foot">
      <button type="button" class="pl-btn pl-ghost" id="pl-back">${W.step === 1 ? 'Выйти' : 'Назад'}</button>
      ${extra || ''}
      <button type="button" class="pl-btn pl-ok" id="pl-next-step" ${busy ? 'disabled' : ''}>${busy ? 'Сохраняю...' : esc(nextLabel)}</button>
    </div>`;
  }

  /* Шаг 1: вчера */
  function stepYesterday(){
    const yk = addDays(W.date, -1);
    const s = summaryOf(yk);
    const yrec = rec(yk);
    const stuck = stuckEvents();
    const factTxt = s.withFact.length
      ? `${hoursTxt(s.fact)} по ${s.withFact.length} ${plural(s.withFact.length,'задаче','задачам','задачам')}`
      : 'не отмечен ни на одной задаче';
    const verdict = s.gone.length
      ? `Запланировано ${s.planned}, сделано ${s.done.length}, переехало ${s.gone.length}${
          s.open.length ? `, осталось незакрытым на дате ${s.open.length}` : ''}`
      : s.open.length
        ? `Запланировано ${s.planned}, сделано ${s.done.length}, осталось незакрытым ${s.open.length}. Решение по ним - на следующем шаге`
        : `Запланировано ${s.planned}, сделано ${s.done.length}. Всё закрыто, долга нет`;
    return `
      <div class="pl-card">
        <h2>Чем кончился ${esc(fmtDay(yk))}</h2>
        ${(yrec.obstacles || yrec.reflection) ? `
        <div class="pl-obst">
          ${yrec.obstacles ? `<span class="pl-lbl">Что мешало, по твоей вчерашней записи</span><p>«${esc(yrec.obstacles)}»</p>` : ''}
          ${yrec.reflection ? `<p class="pl-sub" style="margin:6px 0 0">Итог вечером: «${esc(yrec.reflection)}»</p>` : ''}
        </div>` : ''}
        ${s.planned ? `
        <div class="pl-metrics">
          <div class="pl-metric"><b>${s.done.length} из ${s.planned}</b><span>задач закрыто</span></div>
          <div class="pl-metric ${s.gone.length ? 'pl-metric-warn' : ''}"><b>${s.gone.length}</b><span>переехало на другие дни</span></div>
          <div class="pl-metric"><b>${hoursTxt(s.planTotal)}</b><span>план по времени${s.gone.length ? ', вместе с уехавшими' : ''}</span></div>
          <div class="pl-metric"><b>${s.withFact.length ? hoursTxt(s.fact) : '-'}</b><span>факт: ${esc(factTxt)}</span></div>
        </div>
        <p class="pl-sub">${esc(verdict)}</p>
        <div class="pl-list pl-thin">${s.evs.map(e=>`
          <div class="pl-row ${e.done ? 'is-done' : ''}">
            <span class="pl-mark">${e.done ? '✓' : '·'}</span>
            <span class="pl-title">${trackDot(e.track)}${esc(e.title)}</span>
            <span class="pl-min">${isLaunch(e) ? 'точка запуска' : hoursTxt(planMin(e))}${factMin(e) !== null ? ` → ${hoursTxt(factMin(e))}` : ''}</span>
          </div>`).join('')}${s.gone.map(e=>`
          <div class="pl-row pl-row-gone">
            <span class="pl-mark">→</span>
            <span class="pl-title">${trackDot(e.track)}${esc(e.title)}<span class="pl-tag">${movedTag(e)} · теперь ${esc(shortDate(e.date))}</span></span>
            <span class="pl-min">${hoursTxt(loadMin(e))}</span>
          </div>`).join('')}</div>`
        : `<p class="pl-sub">На этот день задач в сетке не было. Сводке нечего показать - начинаем с чистого листа</p>`}
      </div>
      ${stuck.length ? `
      <div class="pl-card pl-danger">
        <h3>Ждут решения · ${stuck.length}</h3>
        <p class="pl-sub">Движок перенёс их три раза и больше не двигает. Реши сейчас, иначе они будут висеть и дальше</p>
        <div class="pl-list">${stuck.map(e=>{
          const v = W.stuck[e.id] || '';
          return `<div class="pl-row pl-row-wide">
            <span class="pl-title">${trackDot(e.track)}${esc(e.title)}
              <span class="pl-tag">${esc(shortDate(e.date))} · переносов ${esc(e.moved == null ? '3+' : e.moved)}</span></span>
            <span class="pl-acts-inline">
              <button type="button" class="pl-btn pl-sm ${v==='take'?'on':''}" data-stuck="${esc(e.id)}" data-verdict="take">Взять сегодня</button>
              <button type="button" class="pl-btn pl-sm ${v==='keep'?'on':''}" data-stuck="${esc(e.id)}" data-verdict="keep">Оставить как есть</button>
              <button type="button" class="pl-btn pl-sm ${v==='backlog'?'on':''}" data-stuck="${esc(e.id)}" data-verdict="backlog">В бэклог</button>
              <button type="button" class="pl-btn pl-sm pl-rm ${v==='drop'?'on':''}" data-stuck="${esc(e.id)}" data-verdict="drop">Удалить</button>
            </span>
          </div>`;
        }).join('')}</div>
      </div>` : ''}
      ${wizFoot('Дальше: список на день')}`;
  }

  /* Шаг 2: список сегодня */
  function stepList(){
    const debt = debtEvents(W.date);
    const today = dayEvents(W.date);
    const backlog = (DATA.backlog || []).filter(b => (b.status || 'anytime') === 'anytime');

    const debtBlock = debt.length ? `
      <div class="pl-card">
        <h3>Незакрытое с прошлых дней · ${debt.length}</h3>
        <p class="pl-sub">По каждой - явное решение. Пропустить тоже решение: задача останется на своей дате, вечером её двинет движок</p>
        <div class="pl-list">${debt.map(e=>{
          const v = W.debt[e.id] || '';
          return `<div class="pl-row pl-row-wide">
            <span class="pl-title">${trackDot(e.track)}${esc(e.title)}
              <span class="pl-tag">${esc(shortDate(e.date))}${e.moved ? ' · ' + movedTag(e) : ''} · ${hoursTxt(loadMin(e))}</span></span>
            <span class="pl-acts-inline">
              <button type="button" class="pl-btn pl-sm ${v==='take'?'on':''}" data-debt="${esc(e.id)}" data-verdict="take">Взять сегодня</button>
              <button type="button" class="pl-btn pl-sm ${v==='backlog'?'on':''}" data-debt="${esc(e.id)}" data-verdict="backlog">В бэклог</button>
              <button type="button" class="pl-btn pl-sm ${v==='skip'?'on':''}" data-debt="${esc(e.id)}" data-verdict="skip">Пропустить</button>
            </span>
          </div>`;
        }).join('')}</div>
      </div>` : `
      <div class="pl-card">
        <h3>Незакрытого с прошлых дней нет</h3>
        <p class="pl-sub">Долга по задачам не накопилось</p>
      </div>`;

    const todayRow = e => {
      const v = W.today[e.id] || 'keep';
      return `<div class="pl-row pl-row-wide ${v!=='keep'?'is-out':''}">
        <span class="pl-title">${trackDot(e.track)}${esc(e.title)}
          <span class="pl-tag">${esc(e.start)} · ${isLaunch(e) ? 'точка запуска' : hoursTxt(planMin(e))}${e.fixed ? ' · закреплено' : ''}</span>
          ${isArrived(e) ? `<span class="pl-tag pl-tag-move">${movedTag(e)}</span>` : ''}</span>
        <span class="pl-acts-inline">
          <button type="button" class="pl-btn pl-sm ${v==='keep'?'on':''}" data-today="${esc(e.id)}" data-verdict="keep">Оставить</button>
          <button type="button" class="pl-btn pl-sm ${v==='backlog'?'on':''}" data-today="${esc(e.id)}" data-verdict="backlog">В бэклог</button>
          <button type="button" class="pl-btn pl-sm pl-rm ${v==='drop'?'on':''}" data-today="${esc(e.id)}" data-verdict="drop">Удалить</button>
        </span>
      </div>`;
    };
    const arrived = today.filter(isArrived);
    const own = today.filter(e => !isArrived(e));

    /* Хвосты показываем ОТДЕЛЬНО: задача, приехавшая сюда с прошлого дня, -
       это не «новая задача дня», и делать вид, что она тут родилась, нельзя. */
    const arrivedBlock = arrived.length ? `
      <div class="pl-card pl-card-move">
        <h3>Переехало сюда · ${arrived.length}</h3>
        <p class="pl-sub">Эти задачи ты уже двигал. Чем больше переносов, тем честнее вопрос: она вообще будет сделана или ей место в бэклоге</p>
        <div class="pl-list">${arrived.map(todayRow).join('')}</div>
      </div>` : '';

    const todayBlock = `
      <div class="pl-card">
        <h3>${arrived.length ? 'Своё на ' : 'Уже стоит на '}${esc(fmtDay(W.date))} · ${own.length}</h3>
        ${own.length ? `<div class="pl-list">${own.map(todayRow).join('')}</div>`
          : '<p class="pl-sub">Пока пусто. Добери из бэклога ниже</p>'}
      </div>`;

    const someday = (DATA.backlog || []).filter(b => b.status === 'someday').length;
    const backlogBlock = `
      <div class="pl-card">
        <h3>Добор из бэклога</h3>
        <p class="pl-sub">Только задачи со статусом anytime${someday ? `. Someday (${someday}) в утренний план не берём - это другой горизонт` : ''}</p>
        ${backlog.length ? `<div class="pl-list">${backlog.map(b=>{
          const on = !!W.pull[b.id];
          const est = num(b.est);
          return `<div class="pl-row pl-row-wide ${on?'is-in':''}">
            <span class="pl-title">${trackDot(b.track)}${esc(b.title)}
              <span class="pl-tag">${est !== null && est > 0 ? hoursTxt(est) : 'без оценки'}${b.due ? ' · до ' + esc(shortDate(b.due)) : ''}</span></span>
            <span class="pl-acts-inline">
              <button type="button" class="pl-btn pl-sm ${on?'on':''}" data-pull="${esc(b.id)}">${on ? '✓ Взято' : '+ Взять'}</button>
            </span>
          </div>`;
        }).join('')}</div>` : '<p class="pl-sub">Бэклог пуст</p>'}
      </div>`;

    return debtBlock + arrivedBlock + todayBlock + backlogBlock + wizFoot('Дальше: оценки');
  }

  /* Шаг 3: оценки и ёмкость */
  function stepEst(){
    const list = wizardList();
    const load = loadOfDay();
    const st = capState(load);
    const left = st.cap ? st.cap.norm - load : null;
    const pct = st.cap && st.cap.norm > 0 ? Math.round(load / st.cap.norm * 100) : null;
    const unconfirmed = list.filter(e => needEst(e) && !W.confirmed[e.id]).length;

    const capBox = st.cap ? `
      <div class="pl-cap pl-cap-${st.level}">
        <div class="pl-cap-top">
          <b>${hoursTxt(load)}</b> из ёмкости дня ${hoursTxt(st.cap.norm)}
          <span class="pl-cap-sub">рабочее окно ${esc(hhmm(st.cap.from))}-${esc(hhmm(st.cap.to))} × ${st.cap.pct}%</span>
        </div>
        <div class="pl-cap-bar"><div class="pl-cap-fill" style="width:${Math.min(100, pct || 0)}%"></div></div>
        <div class="pl-cap-msg">${
          st.level === 'green' ? `Влезает. Свободно ещё ${hoursTxt(Math.max(0, left))}` :
          st.level === 'yellow' ? `Впритык: перебор ${hoursTxt(load - st.cap.norm)}. День поедет, если хоть что-то затянется` :
          `Перебор ${hoursTxt(load - st.cap.norm)}. Столько не помещается - отложи что-то в бэклог прямо здесь`
        }</div>
      </div>` : `<div class="pl-cap pl-cap-none">Ёмкость дня не посчитать: в настройках нет рабочего окна</div>`;

    const heavy = st.level === 'red'
      ? list.filter(needEst).sort((a,b)=>estOf(b) - estOf(a)).slice(0, 2)
      : [];

    return `
      <div class="pl-card">
        <h2>Сколько это стоит по времени</h2>
        <p class="pl-sub">Оценка обязательна на каждой задаче. Подставил прошлую или ${DEFAULT_EST} минут по умолчанию - подтверди или поправь${
          unconfirmed ? `. Осталось подтвердить: ${unconfirmed}` : ''}</p>
        ${capBox}
        ${heavy.length ? `<div class="pl-suggest">Самые тяжёлые сейчас: ${heavy.map(e=>`<b>${esc(e.title)}</b> (${hoursTxt(estOf(e))})`).join(', ')}. Отложи одну - и день сойдётся</div>` : ''}
        ${list.length ? `<div class="pl-list">${list.map(e=>{
          if(!needEst(e)){
            /* сделанной задаче оценку не переписываем, точке запуска она не нужна */
            return `<div class="pl-row pl-row-est is-frozen ${e.done ? 'is-done' : ''}">
              <span class="pl-title">${trackDot(e.track)}${esc(e.title)}
                <span class="pl-tag">${e.done ? 'сделано, оценку не трогаем' : 'точка запуска, оценка не нужна'}</span></span>
              <span class="pl-min">${e.done ? hoursTxt(planMin(e)) + (factMin(e) !== null ? ` → факт ${hoursTxt(factMin(e))}` : '') : ''}</span>
            </div>`;
          }
          const ok = !!W.confirmed[e.id];
          const src = estSource(e);
          const srcTxt = src === 'own' ? 'твоя оценка' : src === 'prev' ? 'прошлая оценка'
            : src === 'dur' ? 'из длительности блока' : 'по умолчанию';
          return `<div class="pl-row pl-row-est ${ok ? 'is-ok' : 'is-wait'}">
            <span class="pl-title">${trackDot(e.track)}${esc(e.title)}
              <span class="pl-tag">${ok ? 'подтверждено' : esc(srcTxt)}${e.fixed ? ' · закреплено' : ''}</span></span>
            <span class="pl-estbox">
              <input type="number" class="pl-num" data-est="${esc(e.id)}" value="${estOf(e)}" min="5" max="1440" step="5" inputmode="numeric"> <span class="pl-unit">мин</span>
              ${EST_QUICK.map(q=>`<button type="button" class="pl-chip" data-estq="${esc(e.id)}" data-min="${q}">${q}</button>`).join('')}
              <button type="button" class="pl-btn pl-sm ${ok?'on':''}" data-confirm="${esc(e.id)}">${ok ? '✓' : 'Подтвердить'}</button>
              <button type="button" class="pl-btn pl-sm pl-rm" data-tobacklog="${esc(e.id)}">В бэклог</button>
            </span>
          </div>`;
        }).join('')}</div>` : `<div class="pl-suggest">Планировать нечего: на ${esc(fmtDay(W.date))} не взято ни одной задачи. Это нормально, если день и правда пустой. Хочешь наполнить - шаг назад и добери из бэклога</div>`}
      </div>
      ${wizFoot(list.length ? 'Дальше: порядок' : 'Всё равно дальше: пустой день',
        list.length ? `<button type="button" class="pl-btn pl-ghost" id="pl-confirm-all">Подтвердить все</button>` : '')}`;
  }

  /* Шаг 4: порядок и препятствия */
  function stepOrder(){
    const times = previewTimes();
    const shown = displayList(times);
    const move = movableOf(shown).map(e => e.id);
    const brk = clampNum(PROFILE && PROFILE.breakMin, 0, 60, 10);
    const w = workWindow();
    const end = dayEndsAt(times);
    const late = w && end > w.to;
    const own = shown.filter(e => canReorder(e) && isAnchored(e));
    const left = notFitting(times);

    return `
      <div class="pl-card">
        <div class="pl-cardhead">
          <h2>В каком порядке идём</h2>
          ${own.length ? '<button type="button" class="pl-btn pl-sm pl-ghost" id="pl-release-all">Разложить всё движком</button>' : ''}
        </div>
        <p class="pl-sub">Порядок превращается в расписание для задач, которые двигает движок: они встают одна за другой от ${esc(hhmm(anchorFor(W.date)))} с перерывом ${brk} мин, обед, ужин и тренировку обходим${
          w ? `, за ${esc(hhmm(w.to))} не выходим` : ''}. Задачу с назначенным временем не трогаем, пока ты сам её не подвинешь</p>
        <div class="pl-list pl-sortable" id="pl-sortable">${shown.map(e=>{
          const star = W.big3.indexOf(e.id) >= 0;
          const t = times[e.id];
          const pinned = e.fixed || e.done;
          const kept = !pinned && isAnchored(e);
          const stuck = pinned;
          const mi = move.indexOf(e.id);
          const noFit = t === null;
          return `<div class="pl-row pl-row-sort ${pinned ? 'is-pinned' : ''} ${kept ? 'is-kept' : ''} ${noFit ? 'is-nofit' : ''}" ${stuck ? '' : 'draggable="true"'} data-sort="${esc(e.id)}">
            <span class="pl-grab" title="${stuck ? 'Эта задача не двигается' : 'Перетащи, чтобы поменять порядок'}">${stuck ? '📌' : '⠿'}</span>
            <span class="pl-time">${noFit ? esc(e.start) : (t === undefined ? '-' : esc(hhmm(Math.min(DAY_END - 1, t))))}</span>
            <span class="pl-title">${trackDot(e.track)}${esc(e.title)}
              <span class="pl-tag">${isLaunch(e) ? 'точка запуска' : hoursTxt(estOf(e))}${e.fixed ? ' · закреплено' : ''}${e.done ? ' · сделано' : ''}${
                kept ? ' · своё время ' + esc(e.start) : ''}</span>${
              noFit ? '<span class="pl-tag pl-tag-red">не влезает в рабочее окно, оставляю на месте</span>' : ''}</span>
            <span class="pl-acts-inline">
              <button type="button" class="pl-btn pl-sm pl-star ${star?'on':''}" data-big3="${esc(e.id)}" title="Одно из трёх главных дел">${star ? '★' : '☆'}</button>
              ${stuck ? '<span class="pl-pinned-note">стоит на своих часах</span>' : `
              ${kept ? `<button type="button" class="pl-btn pl-sm" data-release="${esc(e.id)}" title="Разрешить движку двигать эту задачу">Разложить движком</button>` : ''}
              <button type="button" class="pl-btn pl-sm" data-move="up" data-id="${esc(e.id)}" ${mi<=0?'disabled':''}>↑</button>
              <button type="button" class="pl-btn pl-sm" data-move="down" data-id="${esc(e.id)}" ${mi<0||mi===move.length-1?'disabled':''}>↓</button>`}
            </span>
          </div>`;
        }).join('')}</div>
        ${left.length ? `<div class="pl-suggest pl-suggest-red">В рабочее окно не влезло: ${left.map(e=>`<b>${esc(e.title)}</b> (${hoursTxt(estOf(e))})`).join(', ')}. Новых часов не дам - позже ${
          w ? esc(hhmm(w.to)) : 'конца дня'} движок не ставит, задача остаётся там, где стояла. Шаг назад и в бэклог, либо перенеси на другой день</div>` : ''}
        ${late ? `<div class="pl-suggest">День дотягивает до ${esc(hhmm(Math.min(DAY_END - 1, end)))}, а рабочее окно кончается в ${esc(hhmm(w.to))}. Это твои закреплённые часы: либо осознанно, либо шаг назад и что-то в бэклог</div>` : ''}
        <p class="pl-sub">Отмечено главных: ${W.big3.length} из ${BIG3_MAX}${W.big3.length ? '' : ' - если не отметишь, возьму первые три по порядку'}</p>
      </div>
      <div class="pl-card">
        <h3>Что может помешать сегодня?</h3>
        <p class="pl-sub">Одна строка. Не план Б, а честное имя риска: созвон затянется, ребёнок дома, ждём ответ от подрядчика</p>
        <textarea class="pl-textarea" id="pl-obstacles" rows="2" maxlength="2000"
          placeholder="Например: съёмка сдвинется, если свет уйдёт раньше">${esc(W.obstacles)}</textarea>
        <p class="pl-sub pl-note">Заметка для тебя утром - на раскладку дня не влияет. Часы двигает порядок выше, а не эта строка</p>
      </div>
      ${wizFoot('Дальше: старт дня')}`;
  }

  /* Шаг 5: старт */
  function stepStart(){
    const ordered = orderedList();
    const times = previewTimes();
    const shown = displayList(times);
    const load = loadOfDay();
    const st = capState(load);
    const big3ids = W.big3.length ? W.big3 : ordered.slice(0, BIG3_MAX).map(e => e.id);
    const big3 = big3ids.map(id => ordered.find(e => e.id === id)).filter(Boolean);
    const at = id => { const t = times[id]; return (t === undefined || t === null) ? null : t; };
    const first = shown.filter(e => !e.done && at(e.id) !== null)[0] || null;
    const end = dayEndsAt(times);
    const left = notFitting(times);
    const clock = id => { const t = at(id); return t === null ? 'без часов' : hhmm(Math.min(DAY_END - 1, t)); };

    if(!ordered.length){
      return `
        <div class="pl-card pl-final">
          <h2>${esc(fmtDay(W.date))}</h2>
          <p class="pl-sub">На день не взято ни одной задачи. Запишу день как спланированный и пустой - если это не то, чего ты хотел, вернись на шаг «Список сегодня» и добери из бэклога</p>
          ${W.obstacles ? `<div class="pl-obst"><span class="pl-lbl">Что может помешать</span><p>${esc(W.obstacles)}</p></div>` : ''}
        </div>
        <div class="pl-foot">
          <button type="button" class="pl-btn pl-ghost" id="pl-back">Назад</button>
          <button type="button" class="pl-btn pl-go" id="pl-finish" ${busy ? 'disabled' : ''}>${busy ? 'Сохраняю...' : 'Записать пустой день'}</button>
        </div>`;
    }

    return `
      <div class="pl-card pl-final">
        <h2>${esc(fmtDay(W.date))}</h2>
        <div class="pl-metrics">
          <div class="pl-metric"><b>${ordered.length}</b><span>${plural(ordered.length,'задача','задачи','задач')} в дне</span></div>
          <div class="pl-metric"><b>${hoursTxt(load)}</b><span>${st.cap ? 'из ёмкости ' + hoursTxt(st.cap.norm) : 'плана по времени'}</span></div>
          <div class="pl-metric"><b>${first ? esc(clock(first.id)) : '-'}</b><span>${first ? 'старт: ' + esc(first.title) : 'стартовать нечего'}</span></div>
          <div class="pl-metric"><b>${esc(hhmm(Math.min(DAY_END - 1, end)))}</b><span>день заканчивается</span></div>
        </div>
        ${st.cap && st.level !== 'green' ? `<div class="pl-cap pl-cap-${st.level}"><div class="pl-cap-msg">${
          st.level === 'yellow' ? 'День впритык по ёмкости. Идём, но без запаса' : 'День перегружен. Если не отложишь - перенос вечером сделает движок'
        }</div></div>` : ''}
        ${left.length ? `<div class="pl-suggest pl-suggest-red">В рабочее окно не влезло: ${
          left.map(e=>`<b>${esc(e.title)}</b> (остаётся на ${esc(e.start)})`).join(', ')}. Новых часов движок не даёт - позже ${
          st.cap ? esc(hhmm((workWindow()||{}).to || st.cap.to)) : 'конца дня'} он не ставит</div>` : ''}
        ${big3.length ? `<div class="pl-big3"><span class="pl-lbl">Три главных дела</span><ol>${
          big3.map(e=>`<li>${trackDot(e.track)}${esc(e.title)} <span class="pl-tag">${esc(clock(e.id))}</span></li>`).join('')}</ol></div>` : ''}
        ${W.obstacles ? `<div class="pl-obst"><span class="pl-lbl">Что может помешать</span><p>${esc(W.obstacles)}</p><p class="pl-sub pl-note">Заметка для тебя утром - на раскладку не влияет</p></div>` : ''}
        <div class="pl-list pl-thin">${shown.map(e=>`
          <div class="pl-row ${e.done ? 'is-done' : ''} ${at(e.id) === null ? 'is-nofit' : ''}">
            <span class="pl-time">${at(e.id) === null ? esc(e.start) : esc(clock(e.id))}</span>
            <span class="pl-title">${trackDot(e.track)}${esc(e.title)}</span>
            <span class="pl-min">${isLaunch(e) ? 'точка запуска' : hoursTxt(estOf(e))}</span>
          </div>`).join('')}</div>
      </div>
      <div class="pl-foot">
        <button type="button" class="pl-btn pl-ghost" id="pl-back">Назад</button>
        <button type="button" class="pl-btn pl-go" id="pl-finish" ${busy ? 'disabled' : ''}>${busy ? 'Сохраняю...' : 'День спланирован'}</button>
      </div>`;
  }

  /* ---------- вечернее закрытие ---------- */

  /* Живой индикатор дня-приёмника: та же арифметика, что на утреннем шаге
     оценок, только считается на каждый клик по «на завтра». */
  function targetGauge(box, k){
    const isTom = box.date === addDays(k, 1);
    const name = isTom ? 'Завтра' : fmtDay(box.date);
    const st = box.st;
    const pct = st.cap && st.cap.norm > 0 ? Math.round(box.load / st.cap.norm * 100) : null;
    const msg = !st.cap ? 'Ёмкость дня не посчитать: в настройках нет рабочего окна'
      : st.level === 'green' ? `Влезает. Свободно ещё ${hoursTxt(Math.max(0, st.cap.norm - box.load))}`
      : st.level === 'yellow' ? `Впритык: перебор ${hoursTxt(box.load - st.cap.norm)}. Такой день едет от первой же задержки`
      : `Перебор ${hoursTxt(box.load - st.cap.norm)}. Столько в день не помещается`;
    return `
      <div class="pl-cap pl-cap-${st.level}">
        <div class="pl-cap-top">
          <b>${esc(name)}: ${hoursTxt(box.load)}</b>${st.cap ? ' из ёмкости ' + hoursTxt(st.cap.norm) : ''}
          <span class="pl-cap-sub">уже стоит ${hoursTxt(box.existing)} по ${box.count} ${plural(box.count,'задаче','задачам','задачам')} · переезжает ${hoursTxt(box.incoming)}</span>
        </div>
        <div class="pl-cap-bar"><div class="pl-cap-fill" style="width:${Math.min(100, pct || 0)}%"></div></div>
        <div class="pl-cap-msg">${esc(msg)}</div>
      </div>`;
  }

  /* Вопрос вместо молчания: день-приёмник переполнен - называем цифру и даём
     список того, что можно снять, прямо здесь. */
  function overloadQuestion(box, k){
    const isTom = box.date === addDays(k, 1);
    const name = isTom ? 'Завтра' : fmtDay(box.date);
    const cand = box.items.slice().sort((a,b)=>b.dur - a.dur);
    const cut = Math.max(0, box.load - (box.st.cap ? box.st.cap.norm : box.load));
    return `
      <div class="pl-ask">
        <h4>${esc(name)} станет ${hoursTxt(box.load)} из ${box.st.cap ? hoursTxt(box.st.cap.norm) : 'ёмкости'} - что выкидываем?</h4>
        <p class="pl-sub">Снять надо примерно ${hoursTxt(cut)}. Вот что ты в этот день везёшь, от большого к малому</p>
        <div class="pl-list">${cand.map(it=>`
          <div class="pl-row pl-row-wide">
            <span class="pl-title">${trackDot(it.e.track)}${esc(it.e.title)}
              <span class="pl-tag">${it.load ? hoursTxt(it.load) : 'точка запуска'}${it.e.moved ? ' · ' + movedTag(it.e) : ''}</span></span>
            <span class="pl-acts-inline">
              <button type="button" class="pl-btn pl-sm" data-cl="${esc(it.e.id)}" data-verdict="backlog">В бэклог</button>
              <button type="button" class="pl-btn pl-sm" data-cl="${esc(it.e.id)}" data-verdict="date">На дату позже</button>
              <button type="button" class="pl-btn pl-sm pl-rm" data-cl="${esc(it.e.id)}" data-verdict="drop">Удалить</button>
            </span>
          </div>`).join('')}</div>
        <p class="pl-sub">Оставить как есть тоже можно - но тогда это твой сознательный перегруз, а не сюрприз утром</p>
      </div>`;
  }

  function renderClose(){
    const k = CLOSE.date;
    const s = summaryOf(k);
    const r = rec(k);
    const w = workWindow();
    const plan = closePlan();
    const factTxt = s.withFact.length ? hoursTxt(s.fact) : 'не отмечен';
    const gauges = Object.keys(plan.dates).sort().map(d=>{
      const box = plan.dates[d];
      return targetGauge(box, k) + (box.st.cap && box.load > box.st.cap.norm ? overloadQuestion(box, k) : '');
    }).join('');

    return `
      <div class="pl-card">
        <h2>Закрываем ${esc(fmtDay(k))}</h2>
        <div class="pl-metrics">
          <div class="pl-metric"><b>${s.done.length} из ${s.planned}</b><span>задач закрыто</span></div>
          <div class="pl-metric"><b>${hoursTxt(s.plan)}</b><span>план по времени</span></div>
          <div class="pl-metric"><b>${esc(factTxt)}</b><span>факт${s.withFact.length ? ` по ${s.withFact.length} ${plural(s.withFact.length,'задаче','задачам','задачам')}` : ': отметок нет'}</span></div>
        </div>
        ${r.obstacles ? `<p class="pl-sub">Утром отметил риск: «${esc(r.obstacles)}»</p>` : ''}
      </div>
      ${s.open.length ? `
      <div class="pl-card">
        <h3>Не закрыто · ${s.open.length}</h3>
        <p class="pl-sub">Реши по каждой. Что не решишь - вечерний ритуал в 22:30 перенесёт сам, это не поломка</p>
        ${gauges || `<p class="pl-sub">Как отметишь «на завтра», здесь появится счётчик: во что превратится день-приёмник${
          w ? ` и влезает ли задача до ${esc(hhmm(w.to))}` : ''}</p>`}
        <div class="pl-list">${s.open.map(e=>{
          const v = CLOSE.decide[e.id] || '';
          const d = CLOSE.dates[e.id] || addDays(k, 2);
          const it = plan.byId[e.id];
          const slot = it && it.target ? (it.start !== null
            ? `<span class="pl-slot">встанет ${esc(shortDate(it.target))} в ${esc(hhmm(it.start))}</span>`
            : `<span class="pl-slot pl-slot-bad">не влезает в ${esc(shortDate(it.target))} до ${esc(w ? hhmm(w.to) : 'конца дня')}${
                it.alt ? ` · ближайший день, куда влезает - ${esc(shortDate(it.alt.date))}` : ' · ближайшие три недели тоже заняты'}</span>`) : '';
          return `<div class="pl-row pl-row-wide ${it && it.target && it.start === null ? 'is-nofit' : ''}">
            <span class="pl-title">${trackDot(e.track)}${esc(e.title)}
              <span class="pl-tag">${esc(e.start)} · ${isLaunch(e) ? 'точка запуска' : hoursTxt(loadMin(e))}${e.moved ? ' · ' + movedTag(e) : ''}</span>
              ${e.needsDecision === true ? '<span class="pl-tag pl-tag-red">движок её больше не двигает</span>' : ''}
              ${slot}</span>
            <span class="pl-acts-inline">
              <button type="button" class="pl-btn pl-sm ${v==='tomorrow'?'on':''}" data-cl="${esc(e.id)}" data-verdict="tomorrow">На завтра</button>
              <button type="button" class="pl-btn pl-sm ${v==='date'?'on':''}" data-cl="${esc(e.id)}" data-verdict="date">На дату</button>
              ${v==='date' ? `<input type="date" class="pl-date" data-cldate="${esc(e.id)}" value="${esc(d)}">` : ''}
              ${it && it.target && it.start === null && it.alt ? `<button type="button" class="pl-btn pl-sm pl-fix" data-alt="${esc(e.id)}" data-date="${esc(it.alt.date)}">Поставить ${esc(shortDate(it.alt.date))}</button>` : ''}
              <button type="button" class="pl-btn pl-sm ${v==='backlog'?'on':''}" data-cl="${esc(e.id)}" data-verdict="backlog">В бэклог</button>
              <button type="button" class="pl-btn pl-sm pl-rm ${v==='drop'?'on':''}" data-cl="${esc(e.id)}" data-verdict="drop">Удалить</button>
            </span>
          </div>`;
        }).join('')}</div>
      </div>` : `<div class="pl-card"><h3>Всё закрыто</h3><p class="pl-sub">Ни одной висящей задачи, переносить нечего</p></div>`}
      <div class="pl-card">
        <h3>Итог дня одной строкой</h3>
        <p class="pl-sub">Что сегодня сработало или где потерял время. Это же поле читаешь завтра утром</p>
        <textarea class="pl-textarea" id="pl-reflection" rows="2" maxlength="4000"
          placeholder="Например: съёмка съела вдвое больше, чем думал">${esc(CLOSE.reflection)}</textarea>
      </div>
      <div class="pl-foot">
        <button type="button" class="pl-btn pl-ghost" id="pl-close-cancel">Отмена</button>
        <button type="button" class="pl-btn pl-go" id="pl-close-finish" ${busy ? 'disabled' : ''}>${busy ? 'Сохраняю...' : 'День закрыт'}</button>
      </div>`;
  }

  /* ---------- аналитика ---------- */

  function renderStats(){
    const week = periodRange('week'), month = periodRange('month');
    const sw = statsFor(week), sm = statsFor(month);
    if(!sw.hasFact && !sm.hasFact){
      return `
        <div class="pl-card pl-calm">
          <div class="pl-calm-ico">◷</div>
          <h2>Факт копится, вернись через неделю</h2>
          <p>План есть - оценки est стоят на задачах. Факта пока нет: ни на одной задаче за ${esc(month.label)} не отмечено фактическое время.</p>
          <p class="pl-calm-sub">Факт пишет фокус-таймер и вопрос «сколько ушло» при отметке «Готово» в недельной сетке. Как накопится хотя бы неделя - здесь появится коэффициент недооценки по каждому треку, и он честный, а не нули.</p>
        </div>`;
    }
    return `
      <div class="pl-card">
        <h2>План против факта</h2>
        <p class="pl-sub">Только оценка (est) против отмеченного времени (actual). Проценты выполнения живут во вкладке Цикл, здесь их нет специально</p>
      </div>
      ${statTable('Неделя', week, sw)}
      ${statTable('Месяц', month, sm)}`;
  }

  function statTable(title, range, st){
    if(!st.hasFact){
      return `<div class="pl-card">
        <div class="pl-cardhead"><h3>${esc(title)}</h3><span class="pl-sub">${esc(range.label)}</span></div>
        <p class="pl-sub">За этот период факт нигде не отмечен. План стоит на ${st.total.n} ${plural(st.total.n,'задаче','задачах','задачах')} - как появятся отметки, строки заполнятся</p>
      </div>`;
    }
    const row = (r, isTotal)=>{
      const k = ratioOf(r);
      const label = isTotal ? 'Всего' : trackLabel(r.code);
      return `<tr class="${isTotal ? 'pl-total' : ''}">
        <td>${isTotal ? '' : trackDot(r.code)}${esc(label)}</td>
        <td>${hoursTxt(r.plan)}</td>
        <td>${r.nFact ? hoursTxt(r.fact) : '<span class="pl-none">нет отметок</span>'}</td>
        <td>${r.nFact ? `${r.nFact} из ${r.n}` : '-'}</td>
        <td>${k === null ? '<span class="pl-none">-</span>' :
          `<b class="${k > 1.15 ? 'pl-bad' : k < 0.85 ? 'pl-good' : ''}">×${k.toFixed(2)}</b>`}</td>
        <td class="pl-verdict">${k === null ? '' :
          k > 1.15 ? `недооцениваю на ${Math.round((k - 1) * 100)}%` :
          k < 0.85 ? `закладываю с запасом ${Math.round((1 - k) * 100)}%` : 'оценка сходится'}</td>
      </tr>`;
    };
    return `
      <div class="pl-card">
        <div class="pl-cardhead"><h3>${esc(title)}</h3><span class="pl-sub">${esc(range.label)}</span></div>
        <div class="pl-tablewrap">
          <table class="pl-table">
            <thead><tr><th>Трек</th><th>План</th><th>Факт</th><th>С отметкой</th><th>Коэффициент</th><th></th></tr></thead>
            <tbody>${st.list.map(r => row(r, false)).join('')}${row(st.total, true)}</tbody>
          </table>
        </div>
      </div>`;
  }

  /* ================== события ================== */

  function wire(){
    const q = (sel, fn) => cont.querySelectorAll(sel).forEach(fn);

    if($('pl-prev')) $('pl-prev').addEventListener('click', ()=>gotoDay(addDays(DAY, -1)));
    if($('pl-next')) $('pl-next').addEventListener('click', ()=>gotoDay(addDays(DAY, 1)));
    if($('pl-today')) $('pl-today').addEventListener('click', ()=>gotoDay(todayISO()));
    q('.pl-viewsw button', b => b.addEventListener('click', ()=>{ VIEW = b.dataset.view; ASK = null; flash = null; draw(); }));

    /* обёртки обязательны: обработчик получает событие, а startWizard первым
       аргументом ждёт «force» - MouseEvent проглотил бы вопрос о закрытом дне */
    if($('pl-start')) $('pl-start').addEventListener('click', ()=>startWizard());
    if($('pl-force')) $('pl-force').addEventListener('click', ()=>startWizard());
    if($('pl-replan')) $('pl-replan').addEventListener('click', ()=>startWizard());
    if($('pl-ask-ok')) $('pl-ask-ok').addEventListener('click', ()=>{ ASK = null; startWizard(true); });
    if($('pl-ask-no')) $('pl-ask-no').addEventListener('click', ()=>{ ASK = null; flash = null; draw(); });
    if($('pl-close-day')) $('pl-close-day').addEventListener('click', ()=>{ CLOSE = newClose(DAY); W = null; ASK = null; flash = null; draw(); });
    if($('pl-reclose')) $('pl-reclose').addEventListener('click', ()=>{ CLOSE = newClose(DAY); W = null; ASK = null; flash = null; draw(); });

    if($('pl-back')) $('pl-back').addEventListener('click', wizardBack);
    if($('pl-next-step')) $('pl-next-step').addEventListener('click', wizardNext);
    if($('pl-finish')) $('pl-finish').addEventListener('click', finishWizard);

    q('[data-stuck]', b => b.addEventListener('click', ()=>{
      const id = b.dataset.stuck;
      W.stuck[id] = (W.stuck[id] === b.dataset.verdict) ? '' : b.dataset.verdict;
      if(!W.stuck[id]) delete W.stuck[id];
      draw();
    }));
    q('[data-debt]', b => b.addEventListener('click', ()=>{
      const id = b.dataset.debt;
      W.debt[id] = (W.debt[id] === b.dataset.verdict) ? '' : b.dataset.verdict;
      if(!W.debt[id]) delete W.debt[id];
      draw();
    }));
    q('[data-today]', b => b.addEventListener('click', ()=>{
      const id = b.dataset.today;
      W.today[id] = b.dataset.verdict;
      draw();
    }));
    q('[data-pull]', b => b.addEventListener('click', ()=>{
      const id = b.dataset.pull;
      if(W.pull[id]) delete W.pull[id]; else W.pull[id] = true;
      draw();
    }));

    q('[data-est]', inp => {
      inp.addEventListener('change', ()=>{
        const id = inp.dataset.est;
        W.est[id] = clampNum(inp.value, 5, 1440, DEFAULT_EST);
        W.confirmed[id] = true;                    // руками поправил - это и есть подтверждение
        draw();
      });
    });
    q('[data-estq]', b => b.addEventListener('click', ()=>{
      const id = b.dataset.estq;
      W.est[id] = clampNum(b.dataset.min, 5, 1440, DEFAULT_EST);
      W.confirmed[id] = true;
      draw();
    }));
    q('[data-confirm]', b => b.addEventListener('click', ()=>{
      const id = b.dataset.confirm;
      const e = wizardList().find(x => x.id === id);
      if(e && !needEst(e)) return;                 // сделанному и точке запуска подтверждать нечего
      W.est[id] = e ? estOf(e) : DEFAULT_EST;      // фиксируем подставленное значение как своё
      W.confirmed[id] = true;
      draw();
    }));
    if($('pl-confirm-all')) $('pl-confirm-all').addEventListener('click', ()=>{
      wizardList().forEach(e => {
        if(!needEst(e)) return;
        W.est[e.id] = estOf(e);
        W.confirmed[e.id] = true;
      });
      draw();
    });
    q('[data-tobacklog]', b => b.addEventListener('click', async ()=>{
      const id = b.dataset.tobacklog;
      const ok = await withBusy(()=>commit(doc=>{
        const e = doc.events.find(x => x.id === id);
        if(!e) return;
        doc.backlog.push(toBacklogItem(e));
        doc.events = doc.events.filter(x => x.id !== id);
      }));
      if(ok){
        delete W.est[id]; delete W.confirmed[id];
        W.order = W.order.filter(x => x !== id);
        W.big3 = W.big3.filter(x => x !== id);
        flash = 'Задача уехала в бэклог';
        draw();
      }
    }));

    /* Тронул порядок руками - это и есть явное действие: с этой секунды задачу
       раскладывает движок. Не тронул - её время остаётся её временем. */
    q('[data-move]', b => b.addEventListener('click', ()=>{
      const ids = orderedList().map(e => e.id);
      const i = ids.indexOf(b.dataset.id);
      const j = b.dataset.move === 'up' ? i - 1 : i + 1;
      if(i < 0 || j < 0 || j >= ids.length) return;
      ids.splice(j, 0, ids.splice(i, 1)[0]);
      W.order = ids;
      W.touched[b.dataset.id] = true;
      draw();
    }));
    q('[data-release]', b => b.addEventListener('click', ()=>{
      W.touched[b.dataset.release] = true;
      draw();
    }));
    if($('pl-release-all')) $('pl-release-all').addEventListener('click', ()=>{
      wizardList().forEach(e => { if(canReorder(e)) W.touched[e.id] = true; });
      flash = 'Разложу движком все незакреплённые задачи дня';
      draw();
    });
    q('[data-big3]', b => b.addEventListener('click', ()=>{
      const id = b.dataset.big3;
      const i = W.big3.indexOf(id);
      if(i >= 0) W.big3.splice(i, 1);
      else if(W.big3.length < BIG3_MAX) W.big3.push(id);
      else { flash = `Главных дел не больше ${BIG3_MAX}: сними отметку с другого`; }
      draw();
    }));
    if($('pl-obstacles')) $('pl-obstacles').addEventListener('input', ev => { W.obstacles = ev.target.value; });
    wireDrag();

    q('[data-cl]', b => b.addEventListener('click', ()=>{
      const id = b.dataset.cl;
      CLOSE.decide[id] = (CLOSE.decide[id] === b.dataset.verdict) ? '' : b.dataset.verdict;
      if(CLOSE.decide[id] === 'date' && !CLOSE.dates[id]) CLOSE.dates[id] = addDays(CLOSE.date, 2);
      draw();
    }));
    q('[data-cldate]', inp => inp.addEventListener('change', ()=>{
      CLOSE.dates[inp.dataset.cldate] = inp.value;
      draw();                                    // счётчик приёмника пересчитывается сразу
    }));
    q('[data-alt]', b => b.addEventListener('click', ()=>{
      const id = b.dataset.alt;
      CLOSE.dates[id] = b.dataset.date;
      CLOSE.decide[id] = 'date';
      draw();
    }));
    if($('pl-reflection')) $('pl-reflection').addEventListener('input', ev => { CLOSE.reflection = ev.target.value; });
    if($('pl-close-cancel')) $('pl-close-cancel').addEventListener('click', ()=>{ CLOSE = null; flash = null; draw(); });
    if($('pl-close-finish')) $('pl-close-finish').addEventListener('click', finishClose);
  }

  /* Перетаскивание порядка - для мыши. На телефоне тот же порядок меняют
     кнопки ↑↓ рядом: тянуть пальцем в скролле неудобно и промахивается. */
  function wireDrag(){
    const box = $('pl-sortable');
    if(!box) return;
    let dragId = null;
    box.querySelectorAll('[data-sort]').forEach(row=>{
      row.addEventListener('dragstart', ev=>{
        dragId = row.dataset.sort;
        row.classList.add('is-drag');
        try{ ev.dataTransfer.setData('text/plain', dragId); ev.dataTransfer.effectAllowed = 'move'; }catch(e){}
      });
      row.addEventListener('dragend', ()=>{ row.classList.remove('is-drag'); dragId = null; });
      row.addEventListener('dragover', ev=>{ ev.preventDefault(); row.classList.add('is-over'); });
      row.addEventListener('dragleave', ()=>row.classList.remove('is-over'));
      row.addEventListener('drop', ev=>{
        ev.preventDefault();
        row.classList.remove('is-over');
        let src = dragId;
        if(!src){ try{ src = ev.dataTransfer.getData('text/plain'); }catch(e){} }
        const dst = row.dataset.sort;
        if(!src || src === dst) return;
        const ids = orderedList().map(e => e.id);
        const i = ids.indexOf(src), j = ids.indexOf(dst);
        if(i < 0 || j < 0) return;
        ids.splice(j, 0, ids.splice(i, 1)[0]);
        W.order = ids;
        W.touched[src] = true;
        draw();
      });
    });
  }

  function gotoDay(k){
    DAY = k;
    W = null; CLOSE = null; ASK = null; flash = null;
    draw();
  }

  /* ================== стили ================== */

  function injectStyle(){
    if($('pl-style')) return;
    const st = document.createElement('style');
    st.id = 'pl-style';
    st.textContent = `
.pl-root{height:100%;overflow-y:auto;-webkit-overflow-scrolling:touch;padding:18px 24px 60px;max-width:1080px;margin:0 auto;
  font-family:"Manrope",-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;color:var(--txt)}
.pl-loading{padding:40px;color:var(--txt-dim);font-size:14px}

.pl-head{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;margin-bottom:16px}
.pl-daynav{display:flex;align-items:center;gap:8px;min-width:0}
.pl-nav{border:1px solid var(--bd);background:#fff;color:var(--txt-dim);width:36px;height:36px;border-radius:50%;
  font-size:18px;line-height:1;cursor:pointer;flex:0 0 auto}
.pl-nav:hover{background:var(--hover);color:var(--txt)}
.pl-daytitle{display:flex;flex-direction:column;line-height:1.25;min-width:0}
.pl-daytitle b{font:600 19px/1.2 "Unbounded",sans-serif;letter-spacing:-.2px;white-space:nowrap}
.pl-daytitle span{font-size:12px;color:var(--txt-dim)}
.pl-today{border:1px solid var(--bd);background:#fff;border-radius:18px;padding:7px 14px;font-size:13px;cursor:pointer;
  color:var(--txt);font-family:inherit;min-height:36px}
.pl-today:hover{background:var(--hover)}
.pl-viewsw{display:flex;border:1px solid var(--bd);border-radius:20px;overflow:hidden;flex:0 0 auto}
.pl-viewsw button{border:0;background:#fff;color:var(--txt-dim);padding:9px 16px;font-size:13px;cursor:pointer;
  font-family:inherit;min-height:38px}
.pl-viewsw button.on{background:var(--blue);color:#fff;font-weight:600}

.pl-warn{background:#fef7e0;border:1px solid #fbd48a;color:#7a5300;border-radius:8px;padding:10px 14px;
  font-size:12.5px;line-height:1.5;margin-bottom:14px}
.pl-flash{background:#e6f4ea;border:1px solid #b7e1c5;color:#0b6b3a;border-radius:8px;padding:10px 14px;
  font-size:12.5px;line-height:1.5;margin-bottom:14px}

.pl-steps{display:flex;gap:6px;margin-bottom:16px;flex-wrap:nowrap;overflow-x:auto;padding-bottom:2px}
.pl-step{display:flex;align-items:center;gap:7px;padding:7px 12px;border-radius:20px;background:#f1f3f4;
  font-size:12.5px;color:var(--txt-dim);white-space:nowrap;flex:0 0 auto}
.pl-step.now{background:var(--blue);color:#fff;font-weight:600}
.pl-step.done{background:#e6f4ea;color:#0b6b3a}
.pl-step-n{display:inline-flex;align-items:center;justify-content:center;width:19px;height:19px;border-radius:50%;
  background:rgba(0,0,0,.08);font-size:11px;font-weight:600;flex:0 0 auto}
.pl-step.now .pl-step-n{background:rgba(255,255,255,.28)}

.pl-card{border:1px solid var(--bd);border-radius:12px;background:#fff;padding:18px 20px;margin-bottom:14px}
.pl-card h2{font:600 18px/1.3 "Unbounded",sans-serif;margin:0 0 8px;letter-spacing:-.2px}
.pl-card h3{font:600 14.5px/1.3 "Unbounded",sans-serif;margin:0 0 6px;letter-spacing:-.1px}
.pl-cardhead{display:flex;align-items:baseline;justify-content:space-between;gap:12px;flex-wrap:wrap;margin-bottom:8px}
.pl-cardhead h3{margin:0}
.pl-sub{font-size:12.5px;color:var(--txt-dim);line-height:1.5;margin:0 0 10px}
.pl-sub.pl-alert{color:#b06000}
.pl-card.pl-danger{border-color:#f7c9c5;background:#fff8f7}
.pl-card.pl-done{border-color:#b7e1c5;background:#f6fbf8}
.pl-card.pl-invite{background:#fbfcff;border-color:#c6dafc}
.pl-load{font-size:12.5px;color:var(--txt-dim)}
.pl-load.over{color:var(--red);font-weight:600}

.pl-metrics{display:flex;gap:12px;flex-wrap:wrap;margin:12px 0}
.pl-metric{flex:1 1 140px;min-width:130px;border:1px solid var(--bd-soft);border-radius:9px;padding:10px 12px;background:#fafbfc}
.pl-metric b{display:block;font:600 19px/1.25 "Unbounded",sans-serif;letter-spacing:-.3px}
.pl-metric span{display:block;font-size:11.5px;color:var(--txt-dim);margin-top:3px;line-height:1.35}

.pl-list{display:flex;flex-direction:column;gap:6px;margin-top:10px}
.pl-row{display:flex;align-items:center;gap:10px;padding:10px 12px;border:1px solid var(--bd-soft);border-radius:9px;
  background:#fff;font-size:13.5px;min-height:44px}
.pl-row.is-done{opacity:.6}
.pl-row.is-done .pl-title{text-decoration:line-through}
.pl-row.is-out{opacity:.5;background:#fafafa}
.pl-row.is-in{border-color:#b7e1c5;background:#f6fbf8}
.pl-row.pl-row-wide{flex-wrap:wrap;align-items:flex-start}
.pl-row.is-wait{border-color:#fbd48a;background:#fffdf6}
.pl-row.is-ok{border-color:#b7e1c5}
.pl-list.pl-thin .pl-row{padding:7px 10px;min-height:36px;font-size:13px}
.pl-time{font-variant-numeric:tabular-nums;color:var(--txt-dim);font-size:12.5px;width:44px;flex:0 0 auto}
.pl-mark{width:14px;flex:0 0 auto;color:var(--green);text-align:center}
.pl-title{flex:1 1 220px;min-width:0;line-height:1.4}
.pl-min{font-size:12px;color:var(--txt-dim);white-space:nowrap;flex:0 0 auto}
.pl-dot{display:inline-block;width:9px;height:9px;border-radius:2px;margin-right:7px;vertical-align:0}
.pl-tag{display:inline-block;font-size:11px;color:var(--txt-dim);background:#f1f3f4;border-radius:10px;
  padding:2px 8px;margin-left:7px;white-space:nowrap}
.pl-tag-red{background:#fce8e6;color:#b3261e}
.pl-acts-inline{display:flex;gap:6px;flex-wrap:wrap;align-items:center;flex:0 0 auto}
.pl-acts{display:flex;gap:8px;flex-wrap:wrap;margin-top:14px}

.pl-btn{border:1px solid var(--bd);background:#fff;color:var(--txt);border-radius:8px;padding:10px 16px;
  font-size:13.5px;font-family:inherit;cursor:pointer;min-height:44px;line-height:1.2}
.pl-btn:hover{background:var(--hover)}
.pl-btn[disabled]{opacity:.45;cursor:default}
.pl-btn.pl-sm{padding:8px 11px;font-size:12.5px;min-height:38px}
.pl-btn.on{background:var(--blue);border-color:var(--blue);color:#fff;font-weight:600}
.pl-btn.pl-rm.on{background:var(--red);border-color:var(--red)}
.pl-btn.pl-ok{background:var(--blue);border-color:var(--blue);color:#fff;font-weight:600}
.pl-btn.pl-ok:hover{filter:brightness(1.07)}
.pl-btn.pl-go{background:var(--green);border-color:var(--green);color:#fff;font-weight:600;padding:12px 24px}
.pl-btn.pl-go:hover{filter:brightness(1.07)}
.pl-btn.pl-ghost{color:var(--txt-dim)}
.pl-btn.pl-star{min-width:40px;font-size:15px;line-height:1}
.pl-btn.pl-star.on{background:#fef7e0;border-color:#f4b400;color:#a06800}

.pl-cap{border:1px solid var(--bd);border-radius:10px;padding:12px 14px;margin:12px 0}
.pl-cap-top{font-size:13.5px;display:flex;align-items:baseline;gap:8px;flex-wrap:wrap}
.pl-cap-top b{font:600 16px/1.2 "Unbounded",sans-serif}
.pl-cap-sub{font-size:11.5px;color:var(--txt-dim)}
.pl-cap-bar{height:8px;border-radius:4px;background:#e8eaed;margin:9px 0 7px;overflow:hidden}
.pl-cap-fill{height:100%;border-radius:4px;background:currentColor}
.pl-cap-msg{font-size:12.5px;line-height:1.45}
.pl-cap-green{border-color:#b7e1c5;background:#f6fbf8;color:#0b6b3a}
.pl-cap-yellow{border-color:#fbd48a;background:#fffdf6;color:#7a5300}
.pl-cap-red{border-color:#f7c9c5;background:#fff8f7;color:#b3261e}
.pl-cap-none{color:var(--txt-dim);font-size:12.5px}
.pl-suggest{border:1px dashed #f4b400;border-radius:9px;padding:10px 13px;font-size:12.5px;line-height:1.5;
  background:#fffdf6;color:#7a5300;margin:10px 0}

.pl-row-est .pl-estbox{display:flex;align-items:center;gap:5px;flex-wrap:wrap}
.pl-num{width:74px;border:1px solid var(--bd);border-radius:7px;padding:9px 8px;font-size:13.5px;font-family:inherit;
  color:var(--txt);min-height:40px}
.pl-unit{font-size:12px;color:var(--txt-dim);margin-right:4px}
.pl-chip{border:1px solid var(--bd-soft);background:#f8f9fa;color:var(--txt-dim);border-radius:14px;padding:6px 10px;
  font-size:12px;cursor:pointer;font-family:inherit;min-height:32px}
.pl-chip:hover{background:var(--hover);color:var(--txt)}

/* --- честный учёт переездов и границы рабочего окна --- */
.pl-metric.pl-metric-warn{border-color:#fbd48a;background:#fffdf6}
.pl-metric.pl-metric-warn b{color:#7a5300}
.pl-row.pl-row-gone{background:#fafbfc;border-style:dashed}
.pl-row.pl-row-gone .pl-title{color:var(--txt-dim)}
.pl-card.pl-card-move{border-color:#fbd48a;background:#fffdf6}
.pl-tag.pl-tag-move{background:#fef7e0;color:#7a5300}
.pl-row.is-nofit{border-color:#f7c9c5;background:#fff8f7}
.pl-row.is-kept{border-left:3px solid #c6dafc}
.pl-row.is-frozen{opacity:.75;background:#fafbfc}
.pl-note{margin:8px 0 0;font-style:italic}
.pl-slot{display:block;font-size:11.5px;color:#0b6b3a;margin-top:4px}
.pl-slot.pl-slot-bad{color:#b3261e}
.pl-btn.pl-fix{border-color:#f4b400;background:#fef7e0;color:#7a5300}
.pl-suggest.pl-suggest-red{border-color:#f7c9c5;background:#fff8f7;color:#b3261e}
.pl-ask{border:1px solid #f7c9c5;background:#fff8f7;border-radius:10px;padding:12px 14px;margin:10px 0}
.pl-ask h4{font:600 14px/1.35 "Unbounded",sans-serif;margin:0 0 6px;color:#b3261e;letter-spacing:-.1px}
.pl-ask .pl-row{background:#fff}

.pl-row-sort{cursor:grab}
.pl-row-sort.is-drag{opacity:.4}
.pl-row-sort.is-over{border-color:var(--blue);box-shadow:inset 0 2px 0 var(--blue)}
.pl-grab{color:#bdc1c6;font-size:14px;flex:0 0 auto;cursor:grab}
.pl-textarea{width:100%;border:1px solid var(--bd);border-radius:9px;padding:11px 12px;font-size:13.5px;
  font-family:inherit;color:var(--txt);resize:vertical;line-height:1.5}
.pl-textarea:focus{outline:1px solid var(--blue);border-color:var(--blue)}
.pl-date{border:1px solid var(--bd);border-radius:7px;padding:8px;font-size:12.5px;font-family:inherit;min-height:38px}

.pl-big3{margin:12px 0}
.pl-lbl{display:block;font-size:11px;text-transform:uppercase;letter-spacing:.7px;color:var(--txt-dim);margin-bottom:6px}
.pl-big3 ol{margin:0;padding-left:20px;font-size:13.5px;line-height:1.7}
.pl-obst{margin:12px 0;border-left:3px solid #f4b400;padding-left:12px}
.pl-obst p{margin:0;font-size:13.5px;line-height:1.5}
.pl-reflect{margin:10px 0 0;font-size:13.5px;line-height:1.6;color:var(--txt);font-style:italic}
.pl-card.pl-final{border-color:#c6dafc;background:#fbfcff}

.pl-foot{display:flex;gap:10px;justify-content:flex-end;flex-wrap:wrap;margin-top:16px;padding-bottom:8px}

.pl-calm{text-align:center;padding:44px 24px}
.pl-calm-ico{font-size:38px;color:#bdc1c6;line-height:1;margin-bottom:12px}
.pl-calm h2{font:600 20px/1.3 "Unbounded",sans-serif;margin:0 0 10px}
.pl-calm p{font-size:14px;color:var(--txt-dim);line-height:1.6;max-width:520px;margin:0 auto 8px}
.pl-calm-sub{font-size:12.5px !important}
.pl-calm .pl-btn{margin-top:16px}

.pl-tablewrap{overflow-x:auto}
.pl-table{width:100%;border-collapse:collapse;font-size:13px;min-width:520px}
.pl-table th{text-align:left;font-size:11px;text-transform:uppercase;letter-spacing:.6px;color:var(--txt-dim);
  font-weight:500;padding:6px 10px 6px 0;border-bottom:1px solid var(--bd-soft)}
.pl-table td{padding:9px 10px 9px 0;border-bottom:1px solid var(--bd-soft);vertical-align:middle}
.pl-table tr.pl-total td{border-bottom:0;border-top:2px solid var(--bd);font-weight:600}
.pl-none{color:#bdc1c6}
.pl-bad{color:var(--red)}
.pl-good{color:var(--green)}
.pl-verdict{font-size:12px;color:var(--txt-dim)}

@media (max-width:760px){
  .pl-root{padding:14px 14px 72px}
  .pl-head{gap:10px}
  .pl-viewsw{width:100%}
  .pl-viewsw button{flex:1}
  .pl-card{padding:15px 14px}
  .pl-card h2{font-size:16.5px}
  .pl-metric{flex:1 1 calc(50% - 6px);min-width:0}
  .pl-row{flex-wrap:wrap}
  .pl-title{flex:1 1 100%}
  .pl-acts-inline{width:100%}
  .pl-acts-inline .pl-btn{flex:1 1 auto}
  .pl-row-est .pl-estbox{width:100%}
  .pl-num{flex:0 0 74px}
  .pl-foot{position:sticky;bottom:0;background:var(--bg);padding:10px 0;margin-top:14px;
    border-top:1px solid var(--bd-soft);z-index:3}
  .pl-foot .pl-btn{flex:1 1 auto}
  .pl-step-t{display:none}
  .pl-step{padding:8px 10px}
  .pl-steps{gap:5px}
  .pl-time{width:40px}
}
@media (max-width:430px){
  .pl-daytitle b{font-size:16px}
  .pl-metric{flex:1 1 100%}
  .pl-chip{padding:6px 9px}
}`;
    document.head.appendChild(st);
  }

  window.TABS = window.TABS || {};
  window.TABS.plan = renderPlan;
})();

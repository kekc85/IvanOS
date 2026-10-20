/* Вкладка «Цикл»: трекер целей 12 Week Year.
   Три цели цикла (lag-метрика, необязательная вторая метрика lag2 той же формы -
   цель вида «100 учеников И $200к» - + lead measures по неделям), execution score
   с тепловой картой по 12 неделям (источник - sprint.json events), стоп-лист
   отвергнутых направлений. Данные - goals-cycle.json через GET/POST /api/goals.
   Всё в своей IIFE (как app.js), чтобы top-level имена не конфликтовали с
   tab-week.js (там `let DATA` и т.п. на верхнем уровне скрипта). Свои стили -
   инжект <style id="cy-style"> при первом рендере, классы с префиксом cy-. */

(function(){
  const {iso, parseISO} = App.utils;
  const MON = ['января','февраля','марта','апреля','мая','июня','июля','августа','сентября','октября','ноября','декабря'];
  const DAY_MS = 86400000;

  const fmtDate = s => { if(!s) return '-'; const d = parseISO(s); return `${d.getDate()} ${MON[d.getMonth()]} ${d.getFullYear()}`; };
  const today0 = () => { const d = new Date(); d.setHours(0,0,0,0); return d; };
  const rid = () => 'x' + Math.random().toString(36).slice(2, 9);
  const esc = s => String(s == null ? '' : s).replace(/&/g,'&amp;').replace(/"/g,'&quot;').replace(/</g,'&lt;').replace(/>/g,'&gt;');

  let DATA = null, EVENTS = [], cont = null, gen = 0, saveTimer = null;

  /* ---------- загрузка / нормализация / сохранение ---------- */

  function renderCycle(container){
    injectStyle();
    cont = container;
    const myGen = ++gen;
    container.innerHTML = '<div class="cy-loading" id="cy-marker">Загрузка цикла...</div>';
    Promise.all([App.api.get('/api/goals'), App.api.get('/api/data')]).then(([goals, data])=>{
      if(myGen !== gen) return; // пока грузилось, переключили вкладку
      DATA = normalize(goals);
      EVENTS = (data && Array.isArray(data.events)) ? data.events : [];
      draw();
    }).catch(err=>{
      if(myGen !== gen) return;
      container.innerHTML = `<div class="cy-loading">Не удалось загрузить цикл: ${esc(err.message)}</div>`;
    });
  }

  function normalize(raw){
    const g = raw || {};
    const cycle = Object.assign({name:'Цикл', start: iso(today0()), end: iso(today0()), weeks: 12}, g.cycle || {});
    const weeks = cycle.weeks || 12;
    const padWeeks = (arr, filler) => {
      const w = Array.isArray(arr) ? arr.slice(0, weeks) : [];
      while(w.length < weeks) w.push(filler);
      return w;
    };
    const goals = (g.goals || []).map(goal=>{
      const lag = Object.assign({metric:'', target:null, current:0, unit:'', due: cycle.end}, goal.lag || {});
      const leads = (goal.leads || []).map(l=>Object.assign(
        {id: l.id || rid(), title:'', weeklyTarget:0}, l, {weeks: padWeeks(l.weeks, false)}
      ));
      const out = Object.assign({id: goal.id || rid(), title:'', note:''}, goal, {lag, leads});
      /* Вторая метрика НЕобязательна: нет ключа - нет блока и нет места под него.
         Дефолт тут не подставляем (в отличие от lag), иначе у каждой цели вырос
         бы пустой второй слой, которого владелец не заводил. */
      if(goal.lag2) out.lag2 = Object.assign({metric:'', target:null, current:0, unit:'', due: cycle.end}, goal.lag2);
      else delete out.lag2;
      return out;
    });
    const execution = {weeks: padWeeks(g.execution && g.execution.weeks, null)};
    const stopList = (g.stopList || []).map(s=>Object.assign({id: s.id || rid(), title:'', reason:''}, s));
    return {cycle, goals, execution, stopList};
  }

  function save(){
    clearTimeout(saveTimer);
    saveTimer = setTimeout(async()=>{
      await App.api.post('/api/goals', DATA);
      App.flashSaved();
    }, 400);
  }

  /* ---------- лид/лаг эвристика и расчёт execution score ---------- */

  /* однословные фразы матчим ТОЛЬКО как целое слово (сплит по не-буквам), не
     подстрокой: «стать» подстрокой ловила «переСТАТЬ листать ленту» и
     «раССТАТЬся с прокрастинацией» - глаголы действия (то есть годный lead),
     а не результата (lag). Многословные («выйти на/к») подстрокой безопасны -
     пробел внутри почти исключает случайное совпадение внутри слова. */
  const LAG_PHRASES_MULTI = ['выйти на','выйти к'];
  const LAG_PHRASES_WORD = ['получить','достичь','стать','набрать','привлечь','достигнуть','заработать'];
  const LAG_NOUNS = ['подписчик','выручка','доход','прибыль','клиент','продажа','просмотр','охват','участник','ученик','конверсия','рейтинг','лид','заявка','деньги','капитал','прирост'];
  function looksLikeLag(title){
    const t = (title || '').trim().toLowerCase();
    if(!t) return false;
    if(LAG_PHRASES_MULTI.some(p => t.includes(p))) return true;
    const words = t.split(/[^a-zа-яё0-9]+/i).filter(Boolean);
    if(words.some(w => LAG_PHRASES_WORD.includes(w))) return true;
    const firstWord = words[0] || '';
    return LAG_NOUNS.some(n => firstWord.startsWith(n));
  }

  function weekRange(i){ // i - 1-based номер недели цикла
    const start = parseISO(DATA.cycle.start);
    start.setDate(start.getDate() + (i - 1) * 7);
    const end = new Date(start);
    end.setDate(end.getDate() + 6);
    return {start, end};
  }

  function currentWeekIndex(){
    const start = parseISO(DATA.cycle.start);
    const diff = Math.round((today0() - start) / DAY_MS);
    if(diff < 0) return 0;
    return Math.min(Math.floor(diff / 7) + 1, DATA.cycle.weeks);
  }

  /* доля done:true среди активных задач недели (kind не launch и не auto) */
  function liveWeekScore(i){
    const {start, end} = weekRange(i);
    const s = iso(start), e = iso(end);
    const rel = EVENTS.filter(ev => ev.kind !== 'launch' && ev.kind !== 'auto' && ev.date >= s && ev.date <= e);
    if(!rel.length) return null;
    const done = rel.filter(ev => ev.done).length;
    return Math.round(done / rel.length * 100);
  }

  /* живой расчёт + кэш в goals-cycle.json: если sprint.json позже перезапишут
     свежей неделей, старые недели цикла не должны молча обнуляться в "нет данных" */
  function weekScore(i){
    const live = liveWeekScore(i);
    if(live !== null){
      DATA.execution.weeks[i - 1] = live;
      return live;
    }
    const cached = DATA.execution.weeks[i - 1];
    return (cached === undefined || cached === null) ? null : cached;
  }

  function scoreClass(s){ return s >= 85 ? 'good' : s >= 70 ? 'mid' : 'bad'; }

  function twoWeeksWarning(scores, cur){
    if(cur < 2) return null;
    for(let i = cur - 1; i >= 1; i--){
      const a = scores[i - 1], b = scores[i];
      if(a != null && b != null && a < 85 && b < 85) return {a: i, b: i + 1};
    }
    return null;
  }

  /* 'lag2.target' -> 'lag2', 'lag.due' -> 'lag'. Слой цели живёт в имени поля,
     отдельного data-атрибута для него не заводим */
  function lagScope(field){
    const f = String(field || '');
    const dot = f.indexOf('.');
    const scope = dot === -1 ? f : f.slice(0, dot);
    return scope === 'lag2' ? 'lag2' : 'lag';
  }

  function lagPct(lag){
    if(lag.target == null || lag.target === 0 || lag.current == null) return null;
    return Math.max(0, Math.min(100, Math.round(lag.current / lag.target * 100)));
  }

  /* ---------- рендер ---------- */

  function draw(){
    if(!cont) return;
    const cur = currentWeekIndex();

    const before = JSON.stringify(DATA.execution.weeks);
    const scores = [];
    for(let i = 1; i <= DATA.cycle.weeks; i++) scores.push(weekScore(i));
    const dirty = before !== JSON.stringify(DATA.execution.weeks);

    const scored = scores.filter(s => s != null);
    const cycleAvg = scored.length ? Math.round(scored.reduce((a, b) => a + b, 0) / scored.length) : null;
    DATA.goals.forEach(g => {
      if(g.lag.auto) g.lag.current = cycleAvg;
      if(g.lag2 && g.lag2.auto) g.lag2.current = cycleAvg;
    });

    cont.innerHTML = `
      <div class="cy-root">
        ${renderHeader(cur)}
        <div class="cy-goals">${DATA.goals.map(g => renderGoalCard(g, cur)).join('')}</div>
        <button type="button" class="cy-goal-add" id="cy-goal-add">+ Добавить цель</button>
        ${renderExecution(cur, scores)}
        ${renderStopList()}
      </div>`;

    wire();
    if(dirty) save();
  }

  function renderHeader(cur){
    const c = DATA.cycle;
    const start = parseISO(c.start), end = parseISO(c.end), today = today0();
    const daysToStart = Math.round((start - today) / DAY_MS);
    const daysToEnd = Math.round((end - today) / DAY_MS);
    const notStarted = daysToStart > 0;
    const finished = daysToEnd < 0;
    const weekLabel = notStarted ? `старт через ${daysToStart} дн.` : finished ? 'цикл завершён' : `неделя ${cur} из ${c.weeks}`;
    const daysLabel = notStarted ? `начало ${fmtDate(c.start)}` : finished ? `финиш был ${fmtDate(c.end)}` : `${daysToEnd} дн. до финиша`;
    const segs = [...Array(c.weeks)].map((_, idx)=>{
      const wi = idx + 1;
      const cls = notStarted ? '' : wi < cur ? 'done' : wi === cur ? 'now' : '';
      return `<span class="cy-wk-seg ${cls}" title="Неделя ${wi}"></span>`;
    }).join('');
    return `
      <div class="cy-header">
        <div class="cy-header-top">
          <div>
            <input class="cy-cycle-name" id="cy-cycle-name" value="${esc(c.name)}">
            <div class="cy-header-dates">
              старт <input type="date" class="cy-cycle-start-input" id="cy-cycle-start" value="${c.start}" title="Дата старта цикла - двигай, если нужно">
              - ${fmtDate(c.end)} · ${weekLabel}
            </div>
          </div>
          <div class="cy-header-days">${daysLabel}</div>
        </div>
        <div class="cy-weekbar">${segs}</div>
        ${notStarted ? `<div class="cy-prep-week">Цикл ещё не начался (старт ${fmtDate(c.start)}). Эта неделя - подготовительная: в score цикла она не попадает, но именно на ней закрывается текущий долг. Если она должна входить в цикл - подвинь дату старта выше.</div>` : ''}
        <p class="cy-draft-hint">Черновик цикла - формулировки, цифры и даты правь прямо в карточках, сохраняется автоматически.</p>
      </div>`;
  }

  /* Один и тот же блок метрики для обоих слоёв цели: scope - 'lag' или 'lag2'.
     Вторая метрика ведёт себя ровно как первая (подпись, число из цели, единица,
     своя полоса, своя дата), отличается только именем поля в data-field. */
  function renderLagBlock(g, scope){
    const lag = g[scope];
    const isAuto = lag.auto === true;
    const pct = lagPct(lag);
    return `
        <div class="cy-lag" data-lag="${scope}">
          <input class="cy-lag-metric" data-field="${scope}.metric" data-goal="${g.id}" value="${esc(lag.metric)}" placeholder="что меряем">
          <div class="cy-lag-numbers">
            ${isAuto
              ? `<span class="cy-lag-auto-current">${lag.current == null ? 'нет данных' : fmtNum(lag.current) + esc(lag.unit)}</span>`
              : `<input type="text" inputmode="numeric" class="cy-lag-current" data-field="${scope}.current" data-goal="${g.id}" value="${lag.current == null ? '' : fmtNum(lag.current)}">`}
            <span class="cy-lag-sep">из</span>
            <input type="text" inputmode="numeric" class="cy-lag-target" data-field="${scope}.target" data-goal="${g.id}" value="${lag.target == null ? '' : fmtNum(lag.target)}" placeholder="цель">
            <input class="cy-lag-unit" data-field="${scope}.unit" data-goal="${g.id}" value="${esc(lag.unit)}" placeholder="ед.">
          </div>
          <div class="cy-lag-bar"><div class="cy-lag-fill" style="width:${pct == null ? 0 : pct}%"></div></div>
          <div class="cy-lag-foot">
            <span>${lagFootText(lag, pct)}</span>
            <span class="cy-lag-due">до <input type="date" class="cy-lag-due-input" data-field="${scope}.due" data-goal="${g.id}" value="${lag.due || ''}"></span>
          </div>
        </div>`;
  }

  function lagFootText(lag, pct){
    if(lag.target == null) return 'цель ещё не зафиксирована - полоса появится после первого замера';
    if(lag.current == null) return 'нет данных за период';
    return pct == null ? 'цель не может быть нулевой' : pct + '%';
  }

  function renderGoalCard(g, cur){
    return `
      <div class="cy-card" data-goal="${g.id}">
        <input class="cy-goal-title" data-field="title" data-goal="${g.id}" value="${esc(g.title)}">
        <textarea class="cy-goal-note" data-field="note" data-goal="${g.id}" rows="2" placeholder="Заметка к цели (необязательно)">${esc(g.note)}</textarea>
${renderLagBlock(g, 'lag')}
${g.lag2
  ? renderLagBlock(g, 'lag2')
  : `        <button type="button" class="cy-lag2-add" data-goal="${g.id}">+ вторая метрика</button>`}

        <div class="cy-tasks">
          <div class="cy-tasks-label">Задачи<span class="cy-tasks-hint">цель → задача → действия в неделе</span></div>
          ${(g.tasks || []).map(t => renderTask(g.id, t, cur)).join('')}
          <button type="button" class="cy-task-add" data-goal="${g.id}">+ задача</button>
        </div>

        ${g.leads.length ? `
        <div class="cy-leads">
          <div class="cy-leads-label">Lead measures</div>
          ${g.leads.map(l => renderLead(g.id, l, cur)).join('')}
          <button type="button" class="cy-lead-add" data-goal="${g.id}">+ lead measure</button>
        </div>` : ''}
      </div>`;
  }

  /* Недели задачи хранятся числами, а человек пишет их как «1-4, 7».
     Разбор терпимый к пробелам и к любому тире; мусор молча отбрасывается,
     чтобы кривой ввод не запирал сохранение всего документа. */
  function parseWeeks(str, maxW){
    const out = new Set();
    String(str || '').split(',').forEach(part=>{
      const m = part.trim().match(/^(\d+)\s*[-–—]\s*(\d+)$/);
      if(m){
        const a = +m[1], b = +m[2];
        for(let i = Math.min(a,b); i <= Math.max(a,b); i++) if(i >= 1 && i <= maxW) out.add(i);
        return;
      }
      const n = parseInt(part, 10);
      if(!isNaN(n) && n >= 1 && n <= maxW) out.add(n);
    });
    return [...out].sort((a,b)=>a-b);
  }

  function weeksToStr(weeks){
    const w = (weeks || []).slice().sort((a,b)=>a-b);
    if(!w.length) return '';
    const parts = []; let s = w[0], p = w[0];
    for(let i = 1; i <= w.length; i++){
      if(w[i] === p + 1){ p = w[i]; continue; }
      parts.push(s === p ? String(s) : `${s}-${p}`);
      s = p = w[i];
    }
    return parts.join(', ');
  }

  function renderTask(goalId, t, cur){
    const weeks = t.weeks || [];
    const now = weeks.includes(cur);
    return `
      <div class="cy-task${t.done ? ' done' : ''}${now ? ' now' : ''}">
        <button type="button" class="cy-task-check" data-goal="${goalId}" data-task="${t.id}" title="${t.done ? 'Задача закрыта' : 'Отметить закрытой'}">${t.done ? '✓' : ''}</button>
        <input class="cy-task-title" data-goal="${goalId}" data-task="${t.id}" data-field="title" value="${esc(t.title)}" placeholder="Что сделать, чтобы цель сдвинулась">
        <input class="cy-task-weeks" data-goal="${goalId}" data-task="${t.id}" data-field="weeks" value="${esc(weeksToStr(weeks))}" placeholder="недели" title="В каких неделях цикла живёт задача. Пиши «1-4, 7»">
        <button type="button" class="cy-task-del" data-goal="${goalId}" data-task="${t.id}" title="Убрать задачу">×</button>
      </div>`;
  }

  function renderLead(goalId, l, cur){
    const warn = looksLikeLag(l.title);
    const cells = l.weeks.map((done, idx)=>{
      const wi = idx + 1;
      const cls = [done ? 'on' : '', wi === cur ? 'now' : ''].filter(Boolean).join(' ');
      return `<button type="button" class="cy-wcell ${cls}" data-goal="${goalId}" data-lead="${l.id}" data-week="${idx}" title="Неделя ${wi}${done ? ' - отмечено' : ''}">${wi}</button>`;
    }).join('');
    return `
      <div class="cy-lead">
        <div class="cy-lead-head">
          <input class="cy-lead-title" data-field="lead.title" data-goal="${goalId}" data-lead="${l.id}" value="${esc(l.title)}">
          <span class="cy-lead-freq">×<input type="number" min="0" class="cy-lead-weekly" data-field="lead.weeklyTarget" data-goal="${goalId}" data-lead="${l.id}" value="${l.weeklyTarget}"><small>/нед</small></span>
          <button type="button" class="cy-lead-del" data-goal="${goalId}" data-lead="${l.id}" title="Удалить lead measure">×</button>
        </div>
        ${warn ? '<div class="cy-lead-warn">Похоже на результат (lag), а не на действие. Переформулируй как «сделать X раз в неделю».</div>' : ''}
        <div class="cy-wcells">${cells}</div>
      </div>`;
  }

  function renderExecution(cur, scores){
    const curScore = cur >= 1 ? scores[cur - 1] : null;
    const bigText = cur === 0 ? 'цикл не начался' : (curScore == null ? 'нет данных за эту неделю' : curScore + '%');
    const bigClass = curScore == null ? '' : scoreClass(curScore);
    const heat = scores.map((s, idx)=>{
      const wi = idx + 1;
      const cls = s == null ? 'empty' : scoreClass(s);
      const label = s == null ? 'нет данных' : s + '%';
      return `<div class="cy-heat-cell ${cls} ${wi === cur ? 'now' : ''}" title="Неделя ${wi}: ${label}"><span>${wi}</span></div>`;
    }).join('');
    const warn = twoWeeksWarning(scores, cur);
    return `
      <div class="cy-exec">
        <h2>Execution score</h2>
        <p class="cy-exec-intro">Доля выполненных запланированных активных задач недели (без точек запуска и потоков «идёт само») - главная метрика 12WY, цели меряются отдельно по lag.</p>
        <div class="cy-exec-big ${bigClass}">${bigText}</div>
        <div class="cy-heatmap">${heat}</div>
        ${warn ? `<div class="cy-exec-warn">Две недели подряд ниже 85% (неделя ${warn.a} и неделя ${warn.b}). Пора пересматривать план, а не стараться сильнее.</div>` : ''}
      </div>`;
  }

  function renderStopList(){
    const items = DATA.stopList.map(it => `
      <div class="cy-stop-item">
        <div class="cy-stop-body">
          <div class="cy-stop-title">${esc(it.title)}</div>
          <div class="cy-stop-reason">${esc(it.reason)}</div>
        </div>
        <button type="button" class="cy-stop-del" data-id="${it.id}">Убрать</button>
      </div>`).join('');
    return `
      <div class="cy-stop">
        <h2>Стоп-лист цикла</h2>
        <p class="cy-stop-intro">Отвергнутые цели и направления. Держим видимыми, чтобы не возвращались.</p>
        <div class="cy-stop-list">${items || '<div class="cy-stop-empty">пусто</div>'}</div>
        <form class="cy-stop-add" id="cy-stop-add">
          <input name="title" placeholder="Направление" required>
          <input name="reason" placeholder="Почему не берём" required>
          <button type="submit">Добавить</button>
        </form>
      </div>`;
  }

  /* ---------- взаимодействие ---------- */

  /* поля цифр/юнита - фиксированная ширина обрезала бы длинные значения
     (20000000 не влезает в 84px), поэтому ширина подстраивается под текст */
  function autosize(el){
    const len = (el.value || el.placeholder || '').length;
    el.style.width = (Math.max(len, 2) + 1.5) + 'ch';
  }

  /* ---------- форматирование больших чисел + защита от мусора в цели ----------
     Поля «текущее»/«цель» были <input type=number> без разрядов - 20000000
     читался по цифрам. Хуже: Number('abc') и Number('1e999') давали NaN/Infinity,
     JSON тихо сериализует их в null - прежнее значение (20 000 000) терялось без
     единого предупреждения. Теперь: type=text + inputmode=numeric, отображение с
     пробелами-разрядами когда поле не в фокусе (fmtNum), при фокусе - голые цифры
     для нормального редактирования курсором (wire()), при commit - строгий
     regex на целое/дробное неотрицательное число (никакой научной нотации,
     никакого минуса, никаких букв); мусор откатывается к прежнему значению с
     видимой вспышкой (flashRejected), а не тихо. */
  function fmtNum(n){ return n == null ? '' : Number(n).toLocaleString('ru-RU'); }
  function parsePlainInt(raw){
    const cleaned = String(raw == null ? '' : raw).replace(/\s/g, '');
    if(cleaned === '') return {ok: true, value: null};
    if(!/^\d+(\.\d+)?$/.test(cleaned)) return {ok: false, value: null};
    return {ok: true, value: Number(cleaned)};
  }
  function flashRejected(el){
    el.classList.add('cy-field-rejected');
    setTimeout(()=>el.classList.remove('cy-field-rejected'), 900);
  }

  /* точечные патчи вместо draw() - см. onFieldChange для причины */
  function patchLagDisplay(goalId, scope){
    scope = scope || 'lag';
    const g = DATA.goals.find(x => x.id === goalId); if(!g) return;
    const lag = g[scope]; if(!lag) return;
    const card = cont.querySelector(`.cy-card[data-goal="${goalId}"]`); if(!card) return;
    /* именно свой блок, иначе правка второй метрики двигала бы полосу первой */
    const block = card.querySelector(`.cy-lag[data-lag="${scope}"]`); if(!block) return;
    const pct = lagPct(lag);
    const fill = block.querySelector('.cy-lag-fill');
    if(fill) fill.style.width = (pct == null ? 0 : pct) + '%';
    const footSpan = block.querySelector('.cy-lag-foot span:first-child');
    if(footSpan) footSpan.textContent = lagFootText(lag, pct);
  }
  function patchLeadWarn(goalId, leadId){
    const g = DATA.goals.find(x => x.id === goalId); if(!g) return;
    const l = g.leads.find(x => x.id === leadId); if(!l) return;
    const titleInput = cont.querySelector(`.cy-lead-title[data-goal="${goalId}"][data-lead="${leadId}"]`);
    const leadDiv = titleInput && titleInput.closest('.cy-lead'); if(!leadDiv) return;
    let warnEl = leadDiv.querySelector('.cy-lead-warn');
    const warn = looksLikeLag(l.title);
    if(warn && !warnEl){
      warnEl = document.createElement('div');
      warnEl.className = 'cy-lead-warn';
      warnEl.textContent = 'Похоже на результат (lag), а не на действие. Переформулируй как «сделать X раз в неделю».';
      leadDiv.insertBefore(warnEl, leadDiv.querySelector('.cy-wcells'));
    } else if(!warn && warnEl){
      warnEl.remove();
    }
  }
  /* scrollHeight не включает border (только padding+контент), а box-sizing тут
     border-box (глобально в app.css) - без поправки высота выходила на 2px
     (1px верх + 1px низ рамки) короче нужного, и последняя строка текста
     обрезалась ровно на волосок */
  function autoGrow(el){
    el.style.height = 'auto';
    const border = el.offsetHeight - el.clientHeight;
    el.style.height = (el.scrollHeight + border) + 'px';
  }

  function wire(){
    const nameInput = document.getElementById('cy-cycle-name');
    if(nameInput) nameInput.addEventListener('change', ()=>{ DATA.cycle.name = nameInput.value; save(); });

    /* дата старта цикла - двигается вручную (F.2 из реестра: неделя до старта
       не попадает ни в один score, а долг закрывается именно на ней). Конец
       пересчитываем от неё же, чтобы не сломать проверенный факт «84 дня = 12
       недель». */
    const startInput = document.getElementById('cy-cycle-start');
    if(startInput) startInput.addEventListener('change', ()=>{
      const v = startInput.value; if(!v) return;
      DATA.cycle.start = v;
      const s = parseISO(v);
      const e = new Date(s); e.setDate(e.getDate() + DATA.cycle.weeks * 7 - 1);
      DATA.cycle.end = iso(e);
      save(); draw();
    });

    cont.querySelectorAll('[data-field]').forEach(el=>{
      el.addEventListener('change', onFieldChange);
    });

    cont.querySelectorAll('.cy-lag-current, .cy-lag-target, .cy-lag-unit').forEach(el=>{
      autosize(el);
      el.addEventListener('input', ()=>autosize(el));
    });
    /* при фокусе - голые цифры без пробелов-разрядов, иначе курсор скачет мимо
       вставленных разделителей при попытке отредактировать число. Если правки
       не было (зашёл и вышел без набора), 'change' не прилетит - blur сам
       возвращает форматированный вид, чтобы поле не осталось «голым». */
    cont.querySelectorAll('.cy-lag-current, .cy-lag-target').forEach(el=>{
      el.addEventListener('focus', ()=>{ el.value = el.value.replace(/\s/g, ''); autosize(el); });
      el.addEventListener('blur', ()=>{
        const g = DATA.goals.find(x => x.id === el.dataset.goal); if(!g) return;
        const lag = g[lagScope(el.dataset.field)]; if(!lag) return;
        const key = el.classList.contains('cy-lag-current') ? 'current' : 'target';
        el.value = lag[key] == null ? '' : fmtNum(lag[key]);
        autosize(el);
      });
    });

    cont.querySelectorAll('.cy-goal-note').forEach(el=>{
      autoGrow(el);
      el.addEventListener('input', ()=>autoGrow(el));
    });

    cont.querySelectorAll('.cy-wcell').forEach(btn=>{
      btn.addEventListener('click', ()=>{
        const {goal, lead, week} = btn.dataset;
        const g = DATA.goals.find(x => x.id === goal); if(!g) return;
        const l = g.leads.find(x => x.id === lead); if(!l) return;
        l.weeks[parseInt(week, 10)] = !l.weeks[parseInt(week, 10)];
        save();
        draw();
      });
    });

    const goalAddBtn = document.getElementById('cy-goal-add');
    if(goalAddBtn) goalAddBtn.addEventListener('click', ()=>{
      DATA.goals.push({
        id: rid(), title: 'Новая цель', note: '',
        lag: {metric: '', target: null, current: 0, unit: '', due: DATA.cycle.end},
        leads: [],
      });
      save(); draw();
    });

    /* без этой кнопки поле lag2 было бы только в данных и недостижимо руками */
    cont.querySelectorAll('.cy-lag2-add').forEach(btn=>{
      btn.addEventListener('click', ()=>{
        const g = DATA.goals.find(x => x.id === btn.dataset.goal); if(!g) return;
        if(g.lag2) return;
        g.lag2 = {metric: '', target: null, current: 0, unit: '', due: g.lag.due || DATA.cycle.end};
        save(); draw();
      });
    });

    cont.querySelectorAll('.cy-task-add').forEach(btn=>{
      btn.addEventListener('click', ()=>{
        const g = DATA.goals.find(x => x.id === btn.dataset.goal); if(!g) return;
        if(!Array.isArray(g.tasks)) g.tasks = [];
        g.tasks.push({id: rid(), title: '', note: '', done: false, weeks: []});
        save(); draw();
      });
    });

    cont.querySelectorAll('.cy-task-check').forEach(btn=>{
      btn.addEventListener('click', ()=>{
        const g = DATA.goals.find(x => x.id === btn.dataset.goal); if(!g) return;
        const t = (g.tasks || []).find(x => x.id === btn.dataset.task); if(!t) return;
        t.done = !t.done;
        save(); draw();
      });
    });

    cont.querySelectorAll('.cy-task-title, .cy-task-weeks').forEach(inp=>{
      inp.addEventListener('change', ()=>{
        const g = DATA.goals.find(x => x.id === inp.dataset.goal); if(!g) return;
        const t = (g.tasks || []).find(x => x.id === inp.dataset.task); if(!t) return;
        if(inp.dataset.field === 'weeks'){
          t.weeks = parseWeeks(inp.value, DATA.cycle.weeks || 53);
          save(); draw();
        } else {
          t.title = inp.value;
          save();
        }
      });
    });

    cont.querySelectorAll('.cy-task-del').forEach(btn=>{
      btn.addEventListener('click', ()=>{
        const g = DATA.goals.find(x => x.id === btn.dataset.goal); if(!g) return;
        const t = (g.tasks || []).find(x => x.id === btn.dataset.task);
        if(!confirm(`Убрать задачу «${t ? (t.title || '(без названия)') : ''}» из цели?`)) return;
        g.tasks = (g.tasks || []).filter(x => x.id !== btn.dataset.task);
        save(); draw();
      });
    });

    cont.querySelectorAll('.cy-lead-add').forEach(btn=>{
      btn.addEventListener('click', ()=>{
        const g = DATA.goals.find(x => x.id === btn.dataset.goal); if(!g) return;
        g.leads.push({id: rid(), title: '', weeklyTarget: 0, weeks: Array(DATA.cycle.weeks).fill(false)});
        save(); draw();
      });
    });

    cont.querySelectorAll('.cy-lead-del').forEach(btn=>{
      btn.addEventListener('click', ()=>{
        const g = DATA.goals.find(x => x.id === btn.dataset.goal); if(!g) return;
        const l = g.leads.find(x => x.id === btn.dataset.lead);
        if(!confirm(`Удалить lead measure «${l ? (l.title || '(без названия)') : ''}»? Отметки по неделям пропадут.`)) return;
        g.leads = g.leads.filter(x => x.id !== btn.dataset.lead);
        save(); draw();
      });
    });

    const stopForm = document.getElementById('cy-stop-add');
    if(stopForm){
      stopForm.addEventListener('submit', e=>{
        e.preventDefault();
        const title = stopForm.title.value.trim();
        const reason = stopForm.reason.value.trim();
        if(!title || !reason) return;
        DATA.stopList.push({id: rid(), title, reason});
        save();
        draw();
      });
    }

    cont.querySelectorAll('.cy-stop-del').forEach(btn=>{
      btn.addEventListener('click', ()=>{
        DATA.stopList = DATA.stopList.filter(x => x.id !== btn.dataset.id);
        save();
        draw();
      });
    });
  }

  /* Точечное обновление вместо draw(): 'change' на текстовом поле прилетает
     ПОСЛЕ того, как фокус ушёл на следующее (Tab) - полная перерисовка
     (cont.innerHTML = ...) убивала DOM-узел, на который браузер только что
     перевёл фокус, и владелец не мог печатать по полям подряд. Большинству
     полей (title/note/metric/unit/due/freq) новый рендер вообще не нужен -
     инпут и так показывает то, что ввели. Патчим точечно только там, где есть
     производный вывод: полоса+% цели (patchLagDisplay) и предупреждение
     lag/lead (patchLeadWarn). */
  function onFieldChange(e){
    const el = e.target;
    const field = el.dataset.field;
    const g = DATA.goals.find(x => x.id === el.dataset.goal);
    if(!g) return;
    const val = el.value;
    if(field === 'title') g.title = val;
    else if(field === 'note') g.note = val;
    else if(field.startsWith('lag.') || field.startsWith('lag2.')){
      const scope = lagScope(field);
      const key = field.slice(scope.length + 1);
      const lag = g[scope];
      if(!lag) return;
      if(key === 'current' || key === 'target'){
        const parsed = parsePlainInt(val);
        if(!parsed.ok){
          el.value = lag[key] == null ? '' : fmtNum(lag[key]);
          autosize(el); flashRejected(el);
          return;
        }
        lag[key] = parsed.value;
        el.value = parsed.value == null ? '' : fmtNum(parsed.value);
        autosize(el);
        patchLagDisplay(g.id, scope);
      } else {
        lag[key] = val;
      }
    } else if(field.startsWith('lead.')){
      const l = g.leads.find(x => x.id === el.dataset.lead);
      if(!l) return;
      const key = field.slice(5);
      if(key === 'weeklyTarget'){
        const parsed = parsePlainInt(val);
        if(!parsed.ok){
          el.value = l.weeklyTarget;
          flashRejected(el);
          return;
        }
        l.weeklyTarget = parsed.value == null ? 0 : Math.round(parsed.value);
        el.value = l.weeklyTarget;
      } else {
        l[key] = val;
        if(key === 'title') patchLeadWarn(g.id, l.id);
      }
    }
    save();
  }

  /* ---------- стили ---------- */

  function injectStyle(){
    if(document.getElementById('cy-style')) return;
    const st = document.createElement('style');
    st.id = 'cy-style';
    st.textContent = `
.cy-root{height:100%;overflow-y:auto;padding:22px 28px 40px;font-family:"Manrope",-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;color:var(--txt);max-width:1180px;margin:0 auto}
.cy-loading{padding:40px;color:var(--txt-dim);font-size:14px}

.cy-header{margin-bottom:22px}
.cy-header-top{display:flex;align-items:flex-start;justify-content:space-between;gap:16px}
.cy-cycle-name{font:600 22px/1.25 "Unbounded",sans-serif;border:0;background:transparent;color:var(--txt);padding:2px 0;width:100%;letter-spacing:-.2px}
.cy-cycle-name:focus{outline:1px solid var(--bd);border-radius:4px}
.cy-header-dates{font-size:13px;color:var(--txt-dim);margin-top:4px;display:flex;align-items:center;flex-wrap:wrap;gap:4px}
.cy-cycle-start-input{border:0;background:transparent;color:var(--txt-dim);font-size:13px;font-family:inherit;padding:1px 2px}
.cy-cycle-start-input:focus{outline:1px solid var(--bd);border-radius:4px}
.cy-header-days{font-size:13px;color:var(--txt-dim);white-space:nowrap;padding-top:6px}
.cy-weekbar{display:flex;gap:4px;margin-top:14px}
.cy-wk-seg{flex:1;height:6px;border-radius:3px;background:var(--bd-soft)}
.cy-wk-seg.done{background:var(--blue);opacity:.55}
.cy-wk-seg.now{background:var(--blue)}
.cy-prep-week{margin-top:12px;background:#e8f0fe;border:1px solid #c6dafc;color:#1a4c96;border-radius:7px;padding:10px 14px;font-size:12.5px;line-height:1.5}
.cy-draft-hint{font-size:12px;color:var(--txt-dim);margin:10px 0 0;line-height:1.4}

.cy-goals{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin-bottom:14px}
@media (max-width:980px){.cy-goals{grid-template-columns:1fr}}
.cy-goal-add{display:block;width:100%;margin:0 0 24px;border:1px dashed var(--bd);background:#fff;color:var(--txt-dim);border-radius:8px;padding:10px 16px;font-size:13px;cursor:pointer;font-family:inherit}
.cy-goal-add:hover{background:var(--hover);color:var(--txt)}

.cy-card{border:1px solid var(--bd);border-radius:10px;padding:16px;background:#fff;display:flex;flex-direction:column;gap:12px}
.cy-goal-title{font:600 15px/1.3 "Unbounded",sans-serif;border:0;background:transparent;color:var(--txt);padding:2px 0;width:100%}
.cy-goal-title:focus{outline:1px solid var(--bd);border-radius:4px}
.cy-goal-note{font-size:12.5px;color:var(--txt-dim);border:1px solid transparent;background:transparent;resize:none;font-family:inherit;padding:2px 0;line-height:1.4;min-height:34px;overflow-y:hidden}
.cy-goal-note:focus{outline:1px solid var(--bd);border-radius:4px;background:var(--hover)}

.cy-lag{border-top:1px solid var(--bd-soft);padding-top:10px}
.cy-lag-metric{font-size:12px;font-weight:600;color:var(--txt-dim);text-transform:uppercase;letter-spacing:.4px;border:0;background:transparent;width:100%;padding:1px 0}
.cy-lag-metric:focus{outline:1px solid var(--bd);border-radius:4px}
.cy-lag-numbers{display:flex;align-items:baseline;gap:6px;margin-top:4px;flex-wrap:wrap}
.cy-lag-current,.cy-lag-target{font:600 20px/1.1 "Unbounded",sans-serif;border:0;background:transparent;color:var(--txt);min-width:56px;max-width:100%;padding:2px 0}
.cy-lag-current:focus,.cy-lag-target:focus{outline:1px solid var(--bd);border-radius:4px}
.cy-lag-sep{font-size:13px;color:var(--txt-dim)}
.cy-lag-unit{font-size:12px;color:var(--txt-dim);border:0;background:transparent;min-width:40px;max-width:100%}
.cy-lag-unit:focus{outline:1px solid var(--bd);border-radius:4px}
.cy-field-rejected{outline:2px solid var(--red) !important;background:#fdecea !important;border-radius:4px;transition:background-color .6s ease,outline-color .6s ease}
.cy-lag-auto-current{font:600 20px/1.1 "Unbounded",sans-serif;color:var(--txt)}
.cy-lag-bar{height:7px;border-radius:4px;background:var(--bd-soft);margin-top:8px;overflow:hidden}
.cy-lag-fill{height:100%;border-radius:4px;background:var(--blue);transition:width .3s}
.cy-lag-foot{display:flex;justify-content:space-between;align-items:center;margin-top:5px;font-size:11.5px;color:var(--txt-dim);gap:8px}
.cy-lag-due-input{border:0;background:transparent;color:var(--txt-dim);font-size:11.5px;font-family:inherit}
.cy-lag-due-input:focus{outline:1px solid var(--bd);border-radius:4px}

.cy-tasks{display:flex;flex-direction:column;gap:6px;margin-top:14px;padding-top:12px;border-top:1px solid var(--bd)}
.cy-tasks-label{font-size:11px;letter-spacing:.06em;text-transform:uppercase;color:var(--txt-dim);display:flex;align-items:baseline;gap:8px;flex-wrap:wrap}
.cy-tasks-hint{text-transform:none;letter-spacing:0;font-size:11px;opacity:.65}
.cy-task{display:flex;align-items:center;gap:6px}
.cy-task-check{flex:0 0 auto;width:18px;height:18px;border:1px solid var(--bd);border-radius:4px;background:none;color:var(--txt);cursor:pointer;font-size:11px;line-height:1;padding:0;font-family:inherit}
.cy-task.done .cy-task-check{background:var(--ok,#2e7d32);border-color:var(--ok,#2e7d32);color:#fff}
.cy-task.done .cy-task-title{text-decoration:line-through;opacity:.55}
.cy-task.now .cy-task-title{font-weight:600}
.cy-task-title{flex:1 1 auto;min-width:0;border:1px solid transparent;background:none;color:var(--txt);font-family:inherit;font-size:13px;padding:3px 4px;border-radius:4px}
.cy-task-title:focus,.cy-task-weeks:focus{border-color:var(--bd);outline:none;background:var(--hover)}
.cy-task-weeks{flex:0 0 74px;width:74px;border:1px solid transparent;background:none;color:var(--txt-dim);font-family:inherit;font-size:11px;padding:3px 4px;border-radius:4px;text-align:right}
.cy-task-del{flex:0 0 auto;border:none;background:none;color:var(--txt-dim);cursor:pointer;font-size:14px;line-height:1;padding:0 4px;font-family:inherit}
.cy-task-del:hover{color:var(--txt)}
.cy-task-add{align-self:flex-start;border:1px dashed var(--bd);background:none;color:var(--txt-dim);border-radius:5px;padding:4px 10px;font-size:11px;cursor:pointer;font-family:inherit}
.cy-task-add:hover{background:var(--hover);color:var(--txt)}
.cy-lag2-add{align-self:flex-start;border:1px dashed var(--bd);background:none;color:var(--txt-dim);border-radius:5px;padding:4px 10px;font-size:11px;cursor:pointer;font-family:inherit}
.cy-lag2-add:hover{background:var(--hover);color:var(--txt)}

.cy-leads{border-top:1px solid var(--bd-soft);padding-top:10px;display:flex;flex-direction:column;gap:12px}
.cy-leads-label{font-size:11px;text-transform:uppercase;letter-spacing:.5px;color:var(--txt-dim);font-weight:600}
.cy-lead{display:flex;flex-direction:column;gap:5px}
.cy-lead-head{display:flex;align-items:center;gap:8px}
.cy-lead-title{flex:1;font-size:12.5px;border:0;background:transparent;color:var(--txt);padding:2px 0;min-width:0}
.cy-lead-title:focus{outline:1px solid var(--bd);border-radius:4px}
.cy-lead-freq{font-size:11px;color:var(--txt-dim);white-space:nowrap;display:flex;align-items:center;gap:2px}
.cy-lead-weekly{width:32px;border:0;background:transparent;color:var(--txt-dim);font-size:11px;text-align:right;padding:1px}
.cy-lead-weekly:focus{outline:1px solid var(--bd);border-radius:4px}
.cy-lead-del{border:0;background:none;color:var(--txt-dim);font-size:14px;cursor:pointer;font-family:inherit;padding:0 2px;line-height:1;flex:0 0 auto}
.cy-lead-del:hover{color:var(--red)}
.cy-lead-warn{font-size:11px;color:#a35a00;background:#fff3e0;border:1px solid #ffdca8;border-radius:5px;padding:5px 8px;line-height:1.4}
.cy-wcells{display:grid;grid-template-columns:repeat(12,1fr);gap:3px}
.cy-wcell{border:1px solid var(--bd);background:#fff;color:var(--txt-dim);font-size:10px;border-radius:4px;height:22px;cursor:pointer;padding:0;font-family:inherit}
.cy-wcell:hover{background:var(--hover)}
.cy-wcell.now{border-color:var(--blue);color:var(--blue);font-weight:700}
.cy-wcell.on{background:var(--green);border-color:var(--green);color:#fff;font-weight:600}
.cy-lead-add{align-self:flex-start;border:1px dashed var(--bd);background:none;color:var(--txt-dim);border-radius:5px;padding:4px 10px;font-size:11px;cursor:pointer;font-family:inherit}
.cy-lead-add:hover{background:var(--hover);color:var(--txt)}

.cy-exec{border:1px solid var(--bd);border-radius:10px;padding:18px 20px;margin-bottom:20px;background:#fff}
.cy-exec h2{font:600 16px/1.3 "Unbounded",sans-serif;margin:0 0 4px}
.cy-exec-intro{font-size:12px;color:var(--txt-dim);margin:0 0 14px;line-height:1.45;max-width:640px}
.cy-exec-big{font:700 40px/1 "Unbounded",sans-serif;color:var(--txt-dim);margin-bottom:14px}
.cy-exec-big.good{color:var(--green)}
.cy-exec-big.mid{color:#b06000}
.cy-exec-big.bad{color:var(--red)}
.cy-heatmap{display:grid;grid-template-columns:repeat(12,1fr);gap:5px;max-width:640px}
.cy-heat-cell{aspect-ratio:1;border-radius:5px;display:flex;align-items:center;justify-content:center;font-size:11px;color:#fff;font-weight:600;background:var(--bd-soft)}
.cy-heat-cell.empty{background:var(--bd-soft);color:var(--txt-dim)}
.cy-heat-cell.good{background:var(--green)}
.cy-heat-cell.mid{background:#e8a400}
.cy-heat-cell.bad{background:var(--red)}
.cy-heat-cell.now{box-shadow:0 0 0 2px var(--blue)}
.cy-exec-warn{margin-top:14px;background:#fdecea;border:1px solid #f6c6c1;color:#8a1f11;border-radius:7px;padding:10px 14px;font-size:13px;line-height:1.45;font-weight:600}

.cy-stop{border:1px solid var(--bd);border-radius:10px;padding:18px 20px;background:#fafafa}
.cy-stop h2{font:600 16px/1.3 "Unbounded",sans-serif;margin:0 0 4px}
.cy-stop-intro{font-size:12px;color:var(--txt-dim);margin:0 0 12px}
.cy-stop-list{display:flex;flex-direction:column;gap:8px;margin-bottom:14px}
.cy-stop-empty{font-size:12px;color:var(--txt-dim)}
.cy-stop-item{display:flex;align-items:center;justify-content:space-between;gap:10px;background:#fff;border:1px solid var(--bd-soft);border-radius:7px;padding:9px 12px}
.cy-stop-title{font-size:13px;font-weight:600;color:var(--txt)}
.cy-stop-reason{font-size:12px;color:var(--txt-dim);margin-top:2px}
.cy-stop-del{border:1px solid var(--bd);background:#fff;color:var(--red);border-radius:4px;padding:5px 10px;font-size:12px;cursor:pointer;font-family:inherit;white-space:nowrap}
.cy-stop-del:hover{background:#fdecea}
.cy-stop-add{display:flex;gap:8px;flex-wrap:wrap}
.cy-stop-add input{flex:1;min-width:160px;border:1px solid var(--bd);border-radius:4px;padding:8px 10px;font-size:13px;font-family:inherit}
.cy-stop-add button{border:0;background:var(--blue);color:#fff;border-radius:4px;padding:8px 16px;font-size:13px;cursor:pointer;font-family:inherit;font-weight:600}
.cy-stop-add button:hover{opacity:.9}
`;
    document.head.appendChild(st);
  }

  window.TABS = window.TABS || {};
  window.TABS.cycle = renderCycle;
})();

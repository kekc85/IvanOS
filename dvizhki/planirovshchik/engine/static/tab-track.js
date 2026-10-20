/* Вкладка «Трекеры»: ежедневные привычки + вечерний чек по контурам
   + месячный смотр по сферам жизни.
   GET/POST /api/track <-> tasks/tracker.json (см. server.py RESOURCES.track).

   Обёрнуто в IIFE намеренно: tab-week.js и tab-settings.js держат свои DATA/render/save
   как плоские top-level переменные общего скрипт-скоупа страницы - совпадение имён дало бы
   SyntaxError на всю вкладку. Наружу торчит только window.TABS.track. Стили - свой <style>
   с префиксом .tr-, в app.css не лезем. */
(function(){
  const {pad, iso, parseISO} = App.utils;

  const WD = ['ПН','ВТ','СР','ЧТ','ПТ','СБ','ВС'];
  const MON_ABBR = ['янв','фев','мар','апр','май','июн','июл','авг','сен','окт','ноя','дек'];

  const BENCHMARK_CONTOURS = [
    /* Список вопросов вечернего чека ПУСТ намеренно: вопросы у каждого свои,
       готовыми они не поставляются. Впиши свои строками вида
       {id:'1', name:'Короткое имя', question:'Вопрос?', anchor:''}.
       Пока список пуст, привычка вечернего чека не закрывается сама. */
  ];

  /* ---------- состояние модуля ---------- */
  let DATA = null, ROOT = null;
  let editingHabitId = null, editingSphereId = null;
  let showArchivedHabits = false, showArchivedSpheres = false;
  let saveTimer = null;
  let viewYear = null, viewMonth = null; // просматриваемый месяц сетки привычек - НЕ обязан совпадать с реальным «сегодня»
  /* На телефоне (<=600px) месячная сетка привычек уступает место списку «сегодня» с
     крупными кнопками (см. renderHabits). mobileGridMode=true - владелец сам попросил
     полную сетку текущего месяца (ссылка «весь месяц», нужна для бэкафилла прошлых дней
     этого месяца). Сброс в false - при возврате на вкладку и при «сегодня». */
  let mobileGridMode = false;
  let resizeHandler = null; // см. renderTrack(): один активный слушатель на монтирование, снимается перед новым
  /* Связка с блоком «Вечерний чек», см. syncBenchmarkHabit(). с этой версии      id новый: прежний evening_benchmark ушёл в архив вместе со всеми старыми записями,
     и без этой правки блок вечернего чека перестал бы закрывать привычку вовсе. Прежний id
     оставлен вторым: на нём висит история отметок, стирать её нельзя. */
  const BENCHMARK_HABIT_ID = 'lichnaya_privychka_4';
  const BENCHMARK_HABIT_ID_OLD = 'evening_benchmark';

  /* Блоки жизни для привычек (поле habit.group, схема в server.py SCHEMAS.track).
     Порядок здесь = порядок отрисовки. Привычка без группы или с незнакомой падает
     в «Прочее» последним блоком - список не теряет строк, даже если группу переименуют. */
  /* Восемь групп - ровно те, что несёт новый список привычек (_spisok-privychek.md).
     Тот же набор и в том же порядке продублирован ещё на ДВУХ поверхностях, и они
     обязаны меняться вместе, иначе привычка падает в «Прочее» именно в том
     инструменте, которым день отмечается диктовкой:
       tools/habits.py  -> GROUP_TITLES и GROUP_ORDER
       кит ученикам     -> собирается скриптом из этого же файла, build.sh */
  const HABIT_GROUPS = [
    {id:'sleep',          title:'Сон',        note:'один и тот же час отбоя - рычаг сильнее длительности'},
    {id:'light',          title:'Свет',       note:'утро на улице, вечер без верхнего света'},
    {id:'body',           title:'Тело',       note:'движение каждый день, тренировка шесть дней'},
    {id:'food',           title:'Питание',    note:'кофе до 11:00, последняя еда за четыре часа до сна'},
    {id:'focus',          title:'Фокус',      note:'вход в день, выход из работы, ноль ссор вечером'},
    {id:'health_metrics', title:'Показатели', note:'то, что меряется, а не ощущается'},
    {id:'supplements',    title:'Добавки',    note:'протокол добавок, второй и третий круг'},
    {id:'spirit',         title:'Дух',        note:'первый плод дня и вечер вместе'},
  ];
  /* Откуда берётся галочка. Смысл метки: чего владельцу НЕ надо делать руками. */
  const SOURCE_META = {
    auto:   {label:'сама',   title:'Ставится движком, руками отмечать не нужно'},
    ask:    {label:'спрошу', title:'Спрашиваю вечером одним заходом, ты диктуешь - я отмечаю'},
    device: {label:'трекер', title:'Считает носимый трекер или телефон. Пока не подключён - ставится со слов'},
    device:  {label:'Прибор',  title:'Снимает прибор. Руками не отмечается никогда'},
    engine: {label:'движок', title:'Считает сам движок по другим данным. Руками не отмечается'},
  };
  /* Источники, где галочку ставит МАШИНА, а не владелец. Держим одним списком:
     от него зависят и запрет клика, и знаменатель дня, и три состояния ниже. */
  const MACHINE_SOURCES = ['auto', 'device', 'device', 'engine'];
  const isMachine = h => MACHINE_SOURCES.indexOf(h && h.source) >= 0;

  /* ТРИ состояния машинной привычки, а не два. Пустая галочка у привычки прибора
     до первого входа владельца в Прибор читалась бы как «не сделал», а зелёная - как
     «сделал»: и то и другое враньё, потому что данных нет вообще. Поэтому третье
     состояние явное, и в знаменатель дня такая строка НЕ входит.
       'нет данных'  - забора не было ни разу (владелец ещё не вошёл в Прибор)
       'протухли'    - забор был, но последний успешный старше суток
       'ok'          - данные свежие
     Состояние приезжает из /api/track (поле deviceSync документа) - его пишет
     tools/device_sync.py. Нет поля вовсе = забора не было ни разу. */
  /* Строки источника `engine` перечислены ПОИМЁННО, а не пропускаются оптом:
     «движок считает сам» верно ровно там, где есть код, который ставит отметку.
     Зеркало таблицы - ENGINE_MARKS в rituals/_common.py, и чекер требует, чтобы
     каждая активная строка с source=engine стояла ключом в этой таблице. Строка
     с engine вне перечня получает «нет данных», а не молчаливое зелёное 'ok'. */
  /* Значение в СТРОГОМ формате «путь#якорь · человеческий адрес», один в один с
     rituals/_common.py#ENGINE_MARKS. Чекер резолвит обе таблицы: открывает файл
     по пути и ищет якорь буквально. Свободный текст сюда больше не кладём -
     именно на нём фиктивная строка с нулём кода проходила зелёной */
  const ENGINE_MARKS = {
    'adherence_85': 'rituals/_common.py#def write_adherence_mark · вечерний ритуал, считается сам по доступным единицам'
  };
  function machineState(h, doc){
    if(!isMachine(h)) return 'ok';
    const s = (doc && doc.deviceSync) || null;
    if(h.source === 'engine') return ENGINE_MARKS[h.id] ? 'ok' : 'нет данных';
    if(!s || !s.lastOkAt) return 'нет данных';
    const age = (Date.now() - Date.parse(s.lastOkAt)) / 36e5;
    return (isFinite(age) && age <= 26) ? 'ok' : 'протухли';
  }

  /* ЕДИНЫЙ знаменатель дня для всех поверхностей вкладки. Зеркало
     rituals/_common.py#available_habits: мета-порог сам себя не считает, строка
     без данных прибора в знаменатель не входит, неежедневная тоже. Раньше шапка
     печатала «0 из 23» там, где ритуал печатал «0 из 17 доступных», и владелец
     читал число, которого физически не мог достичь. */
  /* Знаменатель дня. Один в один с rituals/_common.py#available_habits, включая
     частоту по дням недели: строка с daily:false и полем days доступна ровно в
     свои дни, без days - не доступна никогда (так стоят парковки и мета-порог).
     Разъедься эти два множества - и шапка вкладки покажет одно число, а
     вечерний отчёт другое, ровно как было до этого круга */
  const WD_CODES = ['mon','tue','wed','thu','fri','sat','sun'];
  function availableHabits(doc, dateKey){
    const d = doc || DATA;
    const dt = dateKey ? parseISO(dateKey) : new Date();
    const wd = WD_CODES[(dt.getDay() + 6) % 7];
    return (d.habits || []).filter(h => !h.archived
      && h.id !== 'adherence_85'
      && (h.daily !== false || (h.days || []).indexOf(wd) >= 0)
      && machineState(h, d) === 'ok');
  }

  function groupHabits(active){
    const buckets = new Map(HABIT_GROUPS.map(g => [g.id, []]));
    const rest = [];
    active.forEach(h => {
      const bucket = buckets.get(h.group);
      if(bucket) bucket.push(h); else rest.push(h);
    });
    const out = HABIT_GROUPS
      .filter(g => buckets.get(g.id).length)
      .map(g => ({id:g.id, title:g.title, note:g.note, habits:buckets.get(g.id)}));
    if(rest.length) out.push({id:'other', title:'Прочее', note:'', habits:rest});
    return out;
  }

  /* подпись под именем: почему привычка в списке (механизм + автор) */
  const habitHint = h => h.hint ? ` title="${esc(h.hint)}"` : '';

  /* ВИДИМОЕ обоснование, не всплывающее. Тултип работает только под мышью, а
     владелец смотрит трекер и с телефона, где наведения не существует вовсе:
     порог, автор и ссылка обязаны читаться глазами. Строка раскрывается по клику
     на само название через <details>, чтобы 23 карточки не превратились в простыню. */
  function habitWhy(h){
    if(!h.hint && !h.threshold && !h.quote) return '';
    const cls = {protocol:'порог автора', owner_requirement:'ТРЕБОВАНИЕ ВЛАДЕЛЬЦА',
                 owner_canon:'ЛИЧНЫЙ КАНОН ВЛАДЕЛЬЦА'}[h.class] || '';
    const parts = [];
    if(h.hint) parts.push(`<div class="tr-why-hint">${esc(h.hint)}</div>`);
    const sm = SOURCE_META[h.source];
    if(sm) parts.push(`<div class="tr-why-row"><b>Как отмечается:</b> ` +
      `<span class="tr-src tr-src-${esc(h.source)}">${esc(sm.label)}</span> ${esc(sm.title)}</div>`);
    if(h.daily === false && h.frequency)
      parts.push(`<div class="tr-why-row tr-why-note">Не ежедневная: процент за месяц по ней не считается</div>`);
    if(h.threshold) parts.push(`<div class="tr-why-row"><b>Порог:</b> ${esc(h.threshold)}</div>`);
    if(h.whose_protocol) parts.push(`<div class="tr-why-row"><b>Автор:</b> ${esc(h.whose_protocol)}${cls?` · ${esc(cls)}`:''}</div>`);
    if(h.quote) parts.push(`<div class="tr-why-quote">«${esc(h.quote)}»</div>`);
    if(h.quote_note) parts.push(`<div class="tr-why-row tr-why-note">${esc(h.quote_note)}</div>`);
    if(h.frequency) parts.push(`<div class="tr-why-row"><b>Частота:</b> ${esc(h.frequency)}</div>`);
    if(h.conflict_note) parts.push(`<div class="tr-why-row tr-why-note"><b>Конфликт:</b> ${esc(h.conflict_note)}</div>`);
    if(h.porogi_row_id) parts.push(`<div class="tr-why-row"><b>Строка канона:</b> <code>${esc(h.porogi_row_id)}</code> в твоём файле канона порогов</div>`);
    if(h.source_url) parts.push(`<div class="tr-why-row"><a href="${esc(h.source_url)}" target="_blank" rel="noopener">источник</a></div>`);
    return `<details class="tr-why"><summary>почему это в списке</summary>${parts.join('')}</details>`;
  }

  /* Метка состояния машинной привычки рядом с именем: владелец видит, что прибор
     молчит, а не думает, что не выполнил */
  function stateChip(h, doc){
    const st = machineState(h, doc);
    if(st === 'ok') return '';
    const title = st === 'нет данных'
      ? 'Прибор ещё не подключён: данных не было ни разу. В счёт дня строка не идёт'
      : 'Последний успешный забор старше суток. Данные протухли, в счёт дня строка не идёт';
    return ` <small class="tr-src tr-src-nodata" title="${esc(title)}">${st}</small>`;
  }
  /* Чип рисуем ТОЛЬКО там, где владельцу руками делать нечего (auto, device).
     Первая живая проверка показала, почему: 'спрошу' стоит у 16 привычек из 23
     (замерпо живому tracker.json, прежнее число 13 из 17 относилось к
     старому списку и с данными уже не сходилось),
     в колонке 230px он съедал ширину и резал названия многоточием («Час без экрана
     до сн...»). Метка у большинства = шум; ценность несёт исключение. */
  function sourceChip(h){
    if(!isMachine(h)) return '';
    const meta = SOURCE_META[h.source];
    if(!meta) return '';
    return ` <small class="tr-src tr-src-${h.source}" title="${esc(meta.title)}">${meta.label}</small>`;
  }

  /* Класс авторства ВИДЕН БЕЗ КЛИКА. Раньше он печатался только внутри
     раскрывающегося блока «почему это в списке», и нераскрытая строка личного
     канона владельца выглядела ровно как порог автора с цитатой и ссылкой. Это
     бьёт по главному смыслу захода: владелец обязан видеть, что перед ним НЕ
     вывод ресёрча, не делая ни одного клика. Метка рисуется прямо из поля class,
     отдельного поля данных для неё не заводится. */
  const CLASS_CHIP = {
    owner_canon: {label: 'личный канон',
                  title: 'ЛИЧНЫЙ КАНОН ВЛАДЕЛЬЦА: строка не выведена из ресёрча и цитатой автора не подкрепляется'},
    owner_requirement: {label: 'требование владельца',
                  title: 'ТРЕБОВАНИЕ ВЛАДЕЛЬЦА: сказано им прямо, чужой фамилией не подписано'}
  };
  function classChip(h){
    const meta = CLASS_CHIP[h && h.class];
    if(!meta) return '';
    return ` <small class="tr-class tr-class-${h.class}" title="${esc(meta.title)}">${meta.label}</small>`;
  }
  const MON_FULL = ['Январь','Февраль','Март','Апрель','Май','Июнь','Июль','Август','Сентябрь','Октябрь','Ноябрь','Декабрь'];

  /* ---------- утилиты дат/чисел ---------- */
  const esc = s => String(s==null?'':s).replace(/[&<>"']/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const daysInMonth = (y,m) => new Date(y, m+1, 0).getDate();
  const isMobileViewport = () => !!(window.matchMedia && window.matchMedia('(max-width:600px)').matches);
  const monthKey = d => `${d.getFullYear()}-${pad(d.getMonth()+1)}`;
  const mMonthLabel = mk => { const [y,m]=mk.split('-').map(Number); return `${MON_ABBR[m-1]} ${String(y).slice(2)}`; };
  const scoreColor = score => { const s=Math.max(1,Math.min(10,score)); return `hsl(${((s-1)/9*120).toFixed(0)},60%,90%)`; };
  const scoreColorText = score => { const s=Math.max(1,Math.min(10,score)); return `hsl(${((s-1)/9*120).toFixed(0)},55%,30%)`; };

  /* СКОЛЬКО ДНЕЙ ПОДРЯД, буквально. Считается назад от сегодня (а если сегодня ещё
     не отмечено - от вчера) и обрывается на первом же пропуске.

     Что здесь было и почему переписано. Прежняя версия шла ВПЕРЁД от createdAt,
     складывала все отмеченные дни и обнуляла счётчик только после трёх пропусков
     подряд, то есть на логе «каждый третий день месяца, 10 отметок из 30» печатала
     10 - и подписывала это словом «стрик». Подряд там не было ни одной пары. Правило
     трёх пропусков было к тому же приписано исследованию Lally, которое про длину
     формирования привычки, а не про правила обнуления счётчика. Оба места убраны:
     функция считает то, что написано на подписи, а подпись больше не обещает
     чужого исследования. Само название колонки тоже сменилось со «Стрик» на «Подряд». */
  function computeStreak(habit, log, todayISO){
    const doneOn = key => !!(log[key] && log[key][habit.id]);
    let d = parseISO(todayISO);
    if(!doneOn(iso(d))) d.setDate(d.getDate()-1);   // вечер ещё не наступил - счёт от вчера
    let n = 0;
    const floor = habit.createdAt || '0000-01-01';
    while(iso(d) >= floor && doneOn(iso(d))){
      n += 1;
      d.setDate(d.getDate()-1);
    }
    return n;
  }
  const STREAK_TITLE = 'Сколько дней ПОДРЯД, считая назад от сегодня. Любой пропуск обрывает счёт';

  /* Процент за месяц имеет смысл ТОЛЬКО у ежедневной привычки. У строки с
     расписанием («шесть дней в неделю», «на каждой тренировке») знаменатель - не
     все дни месяца, а дни, когда она была должна, и движок этого расписания не
     знает. Печатать в такой строке 86 процентов значит врать числом, поэтому
     возвращаем null и рисуем прочерк. */
  function computeMonthPct(habit, log, year, month, now){
    if(habit.daily === false) return null;
    /* будущий месяц (просматривается вперёд через навигацию) ещё не наступил -
       без этой проверки isCur=false отдаёт lastDay=dim, месяц целиком считается
       «прожитым», и 0 сделанных из 0 возможных дней превращается в лживые «0%» */
    const isFuture = (year > now.getFullYear()) || (year === now.getFullYear() && month > now.getMonth());
    if(isFuture) return null;
    const dim = daysInMonth(year, month);
    const isCur = (now.getFullYear()===year && now.getMonth()===month);
    const lastDay = isCur ? now.getDate() : dim;
    let total=0, done=0;
    for(let d=1; d<=lastDay; d++){
      const key = iso(new Date(year, month, d));
      if(habit.createdAt && key < habit.createdAt) continue;
      total += 1;
      if(log[key] && log[key][habit.id]) done += 1;
    }
    return total ? Math.round(done/total*100) : 0;
  }

  function latestSphereScore(sphereId){
    const months = Object.keys(DATA.monthly||{}).sort();
    for(let i=months.length-1; i>=0; i--){
      const rec = DATA.monthly[months[i]][sphereId];
      if(rec && typeof rec.score === 'number') return {month:months[i], score:rec.score};
    }
    return null;
  }

  /* ---------- сеть ---------- */
  function normalize(data){
    const d = (data && typeof data==='object') ? data : {};
    d.habits = Array.isArray(d.habits) ? d.habits : [];
    d.spheres = Array.isArray(d.spheres) ? d.spheres : [];
    d.log = (d.log && typeof d.log==='object') ? d.log : {};
    d.benchmark = (d.benchmark && typeof d.benchmark==='object') ? d.benchmark : {};
    d.monthly = (d.monthly && typeof d.monthly==='object') ? d.monthly : {};
    return d;
  }
  /* Запись документа. Приём тот же, что у соседей по движку (tab-plan.js
     commit/saveDay, command.js commit): правка приходит ФУНКЦИЕЙ и применяется к
     ТОЛЬКО ЧТО прочитанному с сервера документу, и лишь потом уходит POST. Значит
     чужая правка - вечерний ритуал, tools/habits.py, вторая вкладка - остаётся на
     месте. На 409 ровно один повтор с новым чтением, дальше видимая ошибка.

     Раньше здесь был «отправил и забыл»: POST всего DATA из памяти, без
     перечитывания, без повтора и без catch. однажды две записи подряд
     вернули документ к прежней версии и стёрли отметки за предыдущий день. */
  let pending = [];        // правки, накопленные за окно дебаунса
  let saving = false;

  /* Правка применяется дважды: сразу к DATA (вкладка отвечает мгновенно) и потом
     к свежему документу внутри flush. Поэтому она обязана быть идемпотентной и не
     тащить в документ общих ссылок - объекты создаём внутри функции. */
  function apply(mutate){
    mutate(DATA);
    pending.push(mutate);
    clearTimeout(saveTimer);
    saveTimer = setTimeout(flush, 400);
  }

  async function flush(){
    clearTimeout(saveTimer); saveTimer = null;
    if(!pending.length) return;
    if(saving){ saveTimer = setTimeout(flush, 250); return; }  // две записи внахлёст не гоняем, как flush в tab-week.js
    saving = true;
    const batch = pending;
    pending = [];
    const attempt = async ()=>{
      const doc = normalize(await App.api.get('/api/track'));
      batch.forEach(fn => fn(doc));
      await App.api.post('/api/track', doc);
      pending.forEach(fn => fn(doc));   // клики, набежавшие пока шла запись, уже в DATA - держим память в одном состоянии с диском
      DATA = doc;
    };
    try{
      await attempt();
      App.flashSaved();
    }catch(err){
      if(err && err.conflict){
        try{
          await attempt();
          App.notify('Трекер меняли в другом окне. Перечитал и сохранил со второй попытки, отметка на месте');
          App.flashSaved();
          return;
        }catch(e){}
      }
      pending = batch.concat(pending);   // ничего не выбрасываем: уйдёт со следующей записью
      App.notify('Отметка не сохранилась: ' + ((err && err.message) || 'сервер не ответил') +
                 '. Она живёт только в этой вкладке - обнови страницу и повтори');
    }finally{
      saving = false;
    }
  }

  /* ---------- мутации данных (только меняют DATA + запись, рендер - на вызывающей стороне) ---------- */
  /* BLOCKER, закрыт. Привычка, заведённая владельцем из интерфейса,
     уезжала в файл БЕЗ source и БЕЗ group. Последствия были две штуки и обе тихие:
     вечерний ритуал и tools/habits.py спрашивают только строки с source ask, значит
     про новую привычку не спрашивали НИКОГДА; а без group она падала в блок «Прочее».
     Теперь оба поля проставляются явно, и группа берётся ВАЛИДНАЯ из HABIT_GROUPS
     (значение 'other' грепу нравится, а привычка всё равно теряет блок).
     Группа по умолчанию - выбранная в селекторе над полем ввода, иначе первая из
     восьми. daily ставим true: заведённая руками привычка по умолчанию ежедневная,
     иначе она не попадёт ни в один вечерний вопрос. */
  function newHabitGroup(){
    const sel = document.getElementById('tr-habit-new-group');
    const v = sel && sel.value;
    return HABIT_GROUPS.some(g=>g.id===v) ? v : HABIT_GROUPS[0].id;
  }
  function addHabit(name){
    const v=(name||'').trim(); if(!v) return false;
    const id='h'+Date.now().toString(36)+Math.random().toString(36).slice(2,6);
    const createdAt=iso(new Date());
    const group=newHabitGroup();
    apply(doc=>{
      if(doc.habits.some(x=>x.id===id)) return;
      doc.habits.push({id, name:v, archived:false, createdAt,
        group, source:'ask', daily:true, class:'owner_canon',
        hint:'ЛИЧНЫЙ КАНОН ВЛАДЕЛЬЦА, не вывод ресёрча: привычка заведена владельцем из интерфейса'});
    });
    return true;
  }
  function renameHabit(id, name){
    const h=DATA.habits.find(x=>x.id===id); if(!h) return false;
    const v=(name||'').trim(); if(!v) return false;
    apply(doc=>{ const t=doc.habits.find(x=>x.id===id); if(t) t.name=v; });
    return true;
  }
  function archiveHabit(id){
    const h=DATA.habits.find(x=>x.id===id); if(!h) return;
    if(!confirm(`Архивировать привычку «${h.name}»?`)) return;
    apply(doc=>{ const t=doc.habits.find(x=>x.id===id); if(t) t.archived=true; });
  }
  function restoreHabit(id){
    const h=DATA.habits.find(x=>x.id===id); if(!h) return;
    apply(doc=>{ const t=doc.habits.find(x=>x.id===id); if(t) t.archived=false; });
  }
  function toggleHabitDay(habitId, dateKey){
    /* целевое состояние считаем СЕЙЧАС и записываем именно его: «переключить»
       на перечитанном документе дало бы обратное, если ту же галочку успел
       поставить кто-то ещё (ритуал, habits.py, вторая вкладка) */
    const on = !(DATA.log[dateKey] && DATA.log[dateKey][habitId]);
    apply(doc=>{
      if(!doc.log[dateKey]) doc.log[dateKey]={};
      /* снятая галочка пишется явным false, ключ из журнала НЕ изымается:
         тот же класс закрыт в device_sync.apply_marks и dinner_intake.apply_marks.
         Все читатели журнала смотрят truthiness, поведение прежнее, история цела */
      doc.log[dateKey][habitId] = on;
    });
  }

  function addSphere(name){
    const v=(name||'').trim(); if(!v) return false;
    const id='s'+Date.now().toString(36)+Math.random().toString(36).slice(2,6);
    apply(doc=>{
      if(doc.spheres.some(x=>x.id===id)) return;
      doc.spheres.push({id, name:v, archived:false});
    });
    return true;
  }
  function renameSphere(id, name){
    const s=DATA.spheres.find(x=>x.id===id); if(!s) return false;
    const v=(name||'').trim(); if(!v) return false;
    apply(doc=>{ const t=doc.spheres.find(x=>x.id===id); if(t) t.name=v; });
    return true;
  }
  function archiveSphere(id){
    const s=DATA.spheres.find(x=>x.id===id); if(!s) return;
    if(!confirm(`Архивировать сферу «${s.name}»?`)) return;
    apply(doc=>{ const t=doc.spheres.find(x=>x.id===id); if(t) t.archived=true; });
  }
  function restoreSphere(id){
    const s=DATA.spheres.find(x=>x.id===id); if(!s) return;
    apply(doc=>{ const t=doc.spheres.find(x=>x.id===id); if(t) t.archived=false; });
  }

  /* «Вечерний вечерний чек» жил и как отдельная привычка в списке, и как блок из
     восьми вопросов ниже - владелец отмечал дважды. Теперь привычка - зеркало
     блока: ответил хоть на один контур сегодня -> привычка закрыта, снял все
     ответы -> открыта обратно. Клик по самой привычке в сетке отключён (см.
     renderHabits), чтобы не завести второй, расходящийся источник правды. */
  /* 🔴 Пустой список контуров НЕ считается закрытым днём. Array.every на пустом
     массиве возвращает true, и без этого гарда движок со стёртым списком (так
     он и уезжает ученикам: контуры личные, каркас общий) закрывал бы привычку
     зелёной каждый день, ни о чём не спросив. Это ровно «трекер врёт зелёным» */
  function benchmarkAnswered(rec){
    return BENCHMARK_CONTOURS.length > 0 && BENCHMARK_CONTOURS.every(c=>rec[c.id]);
  }
  /* документ параметром: та же правка ложится и на DATA, и на перечитанный с
     сервера документ внутри flush (см. apply) */
  function syncBenchmarkHabit(doc, dateKey){
    if(!doc.habits.find(h=>h.id===BENCHMARK_HABIT_ID)) return;
    const rec = (doc.benchmark && doc.benchmark[dateKey]) || {};
    /* ВСЕ восемь, а не любой один. Подсказка привычки обещает пройденный БЛОК,
       а не первый ответ: зелёная галочка после одного контура из восьми - это
       ровно тот случай, когда трекер врёт зелёным */
    const answered = benchmarkAnswered(rec);
    if(!doc.log[dateKey]) doc.log[dateKey] = {};
    doc.log[dateKey][BENCHMARK_HABIT_ID] = answered;   // явный false вместо delete
  }
  /* разовый проход по истории при загрузке - подчищает случаи, когда лог и
     реальные ответы вечернего чека разошлись (например данные правили руками) */
  function backfillBenchmarkHabit(){
    if(!DATA.habits.find(h=>h.id===BENCHMARK_HABIT_ID)) return;
    const needed = Object.keys(DATA.benchmark).some(dateKey=>{
      const rec = DATA.benchmark[dateKey] || {};
      const answered = benchmarkAnswered(rec);
      return answered !== !!(DATA.log[dateKey] && DATA.log[dateKey][BENCHMARK_HABIT_ID]);
    });
    if(!needed) return;
    /* пересчёт идёт ПО САМОМУ документу, а не по заранее снятому списку дат:
       на перечитанном документе ответы вечернего чека могут быть уже другие */
    apply(doc=>{
      if(!doc.habits.find(h=>h.id===BENCHMARK_HABIT_ID)) return;
      Object.keys(doc.benchmark || {}).forEach(dateKey=>{
        const rec = doc.benchmark[dateKey] || {};
        const answered = benchmarkAnswered(rec);
        const cur = !!(doc.log[dateKey] && doc.log[dateKey][BENCHMARK_HABIT_ID]);
        if(answered === cur) return;
        if(!doc.log[dateKey]) doc.log[dateKey] = {};
        doc.log[dateKey][BENCHMARK_HABIT_ID] = answered;   // явный false вместо delete
      });
    });
  }
  function setBenchmark(dateKey, contourId, state){
    /* повторный клик по тому же ответу снимает его - решение принимаем СЕЙЧАС,
       иначе на перечитанном документе оно перевернулось бы */
    const clear = !!(DATA.benchmark[dateKey] && DATA.benchmark[dateKey][contourId]===state);
    apply(doc=>{
      if(!doc.benchmark[dateKey]) doc.benchmark[dateKey]={};
      /* 🔴 снятие ответа пишет пустую строку, а НЕ изымает ключ: тот же класс,
         что снятие отметки в habits.py и в журнале дня. Пустая строка ложна для
         всех читателей (кнопка гаснет, точка тренда становится «нет данных»),
         поэтому поведение прежнее, а факт «здесь отвечали и ответ сняли» цел */
      if(clear) doc.benchmark[dateKey][contourId]='';
      else doc.benchmark[dateKey][contourId]=state;
      syncBenchmarkHabit(doc, dateKey);
    });
  }
  function setSphereMonthly(sphereId, mk, field, value){
    apply(doc=>{
      if(!doc.monthly[mk]) doc.monthly[mk]={};
      if(!doc.monthly[mk][sphereId]) doc.monthly[mk][sphereId]={};
      doc.monthly[mk][sphereId][field]=value;
    });
  }

  /* ---------- рендер: сводка сверху ---------- */
  function renderSummary(){
    const el = document.getElementById('tr-summary');
    if(!el) return;
    const todayISO = iso(new Date());
    const activeHabits = (DATA.habits||[]).filter(h=>!h.archived);
    const availToday = availableHabits(DATA, todayISO);
    const doneToday = availToday.filter(h => DATA.log[todayISO] && DATA.log[todayISO][h.id]).length;

    const activeSpheres = (DATA.spheres||[]).filter(s=>!s.archived);
    const pairs = activeSpheres.map(s=>({sphere:s, rec:latestSphereScore(s.id)})).filter(p=>p.rec);
    let sphereTxt;
    if(pairs.length){
      const avg = pairs.reduce((a,p)=>a+p.rec.score,0)/pairs.length;
      let worst = pairs[0];
      pairs.forEach(p=>{ if(p.rec.score < worst.rec.score) worst = p; });
      sphereTxt = `сферы за месяц: средний балл ${avg.toFixed(1)} из 10 · просядает «${esc(worst.sphere.name)}» (${worst.rec.score})`;
    } else {
      sphereTxt = 'сферы: оценок пока нет, заполни смотр ниже';
    }

    /* Два числа с ЯВНО названной популяцией: сколько закрыто из доступных сегодня
       и сколько всего активных строк в списке. Одно число «из 23» врало: шесть
       строк владелец физически закрыть не может до входа в Прибор */
    const availTip = `Доступные сегодня - это активные строки без мета-порога, без неежедневных ` +
      `и без строк прибора в состоянии «нет данных». Всего активных в списке: ${activeHabits.length}`;
    el.innerHTML = `<span class="tr-summary-item" title="${esc(availTip)}"><b>${doneToday}</b> из ` +
      `<b>${availToday.length}</b> доступных сегодня привычек закрыто ` +
      `<small>(активных в списке ${activeHabits.length})</small></span>
      <span class="tr-summary-sep">·</span>
      <span class="tr-summary-item">${sphereTxt}</span>`;
  }

  /* ---------- рендер: блок 1, ежедневные привычки ---------- */
  function renderHabits(){
    const wrap = document.getElementById('tr-habits-wrap');
    if(!wrap) return;
    const now = new Date();                    // реальное «сегодня» - для счёта «подряд» и метки future, навигацией не двигается
    const todayISO = iso(now);
    const year = viewYear, month = viewMonth;   // просматриваемый месяц - двигается кнопками ‹ › и «сегодня»
    const active = (DATA.habits||[]).filter(h=>!h.archived);
    const mobile = isMobileViewport();
    const isCurMonth = (year===now.getFullYear() && month===now.getMonth());
    /* На телефоне месячная сетка (26x32px клетки, 31 колонка) физически непригодна для
       пальца - дефект живой проверки владельца («попадаешь через раз»). Для ТЕКУЩЕГО
       месяца дефолтный мобильный вид - список с одной крупной кнопкой-переключателем
       «сегодня» (то самое ежедневное вечернее действие) + «подряд» и % рядом текстом; это и
       есть compact history, полную сетку заменять не нужно - она доступна по ссылке
       «весь месяц» специально для бэкафилла прошлых дней. Просмотр НЕ текущего месяца
       (кнопки ‹ ›) всегда показывает сетку - там «сегодня» не существует - но с клетками
       укрупнёнными до 44px и горизонтальным скроллом вместо утончения (тот же паттерн,
       что уже работает у вкладки «Неделя»: закреплённая колонка названий). */
    const showToday = mobile && isCurMonth && !mobileGridMode;

    const label = document.getElementById('tr-month-label');
    if(label) label.textContent = `${MON_FULL[month]} ${year}`;

    const modeToggle = document.getElementById('tr-mode-toggle');
    if(modeToggle){
      if(!mobile || !isCurMonth){
        modeToggle.style.display = 'none';
      } else {
        modeToggle.style.display = '';
        modeToggle.textContent = showToday ? 'весь месяц' : 'к сегодня';
      }
    }

    if(!active.length){
      wrap.innerHTML = '<div class="tr-empty">Привычек пока нет. Добавь первую строкой ниже.</div>';
    } else if(showToday){
      wrap.innerHTML = `<div class="tr-quick-list">${groupHabits(active).map(grp=>
        `<div class="tr-group-head">${esc(grp.title)}${grp.note?` <small>${esc(grp.note)}</small>`:''}</div>` +
        grp.habits.map(h=>{
        const streak = computeStreak(h, DATA.log, todayISO);
        const pctRaw = computeMonthPct(h, DATA.log, year, month, now);
        const pct = pctRaw===null ? '-' : pctRaw+'%';
        const isLinked = h.id === BENCHMARK_HABIT_ID || isMachine(h);
        const done = !!(DATA.log[todayISO] && DATA.log[todayISO][h.id]);
        const nameCell = editingHabitId===h.id
          ? `<input type="text" class="tr-inline-input" id="tr-habit-name-input" value="${esc(h.name)}" data-id="${h.id}">`
          : `<span class="tr-quick-name" data-action="rename-habit" data-id="${h.id}"${habitHint(h)}>${esc(h.name)}${sourceChip(h)}${classChip(h)}${h.id===BENCHMARK_HABIT_ID?' <small class="tr-linked-note">· из вечернего чека</small>':''}${stateChip(h, DATA)}</span>`;
        const toggleAttrs = isLinked ? 'disabled' : `data-action="toggle-habit" data-habit="${h.id}" data-date="${todayISO}"`;
        const toggleTitle = h.id===BENCHMARK_HABIT_ID
          ? 'Управляется блоком «Вечерний чек» ниже'
          : isMachine(h)
            ? 'Ставит ' + (SOURCE_META[h.source]||{}).label + '. Руками не отмечается: ' + machineState(h, DATA)
            : (done ? 'Сделано сегодня - нажми, чтобы отменить' : 'Нажми, когда сделаешь сегодня');
        return `<div class="tr-quick-row">
            <div class="tr-quick-info">
              ${nameCell}
              <span class="tr-quick-meta" title="${STREAK_TITLE}">подряд ${streak} · ${pct} за месяц</span>
              ${habitWhy(h)}
            </div>
            <button type="button" class="tr-quick-toggle${done?' tr-done':''}${isLinked?' tr-locked':''}" ${toggleAttrs} title="${toggleTitle}">${done?'✓':''}</button>
            <button type="button" class="tr-icon-btn tr-quick-archive" data-action="archive-habit" data-id="${h.id}" title="Архивировать">×</button>
          </div>`;
        }).join('')
      ).join('')}</div>`;
      if(editingHabitId){
        const input = document.getElementById('tr-habit-name-input');
        if(input){ input.focus(); input.select(); }
      }
    } else if(mobile){
      /* Мобильная сетка (просмотр другого месяца или «весь месяц» из списка «сегодня»):
         первая попытка закрепить колонку названий через position:sticky ВНУТРИ общего
         CSS Grid не выдержала живой проверки - playwright показал, что sticky-грид-айтем
         «отлипает» и уезжает за экран уже после ~150px горизонтального скролла (грид
         конструирует containing block для sticky-элемента из его собственной ячейки, а
         не из всей грид-таблицы - на широких таблицах это ломает закрепление). Поэтому
         колонка названий здесь - ОТДЕЛЬНЫЙ несворачивающийся блок (tr-grid-names) рядом
         со скроллящейся сеткой клеток (tr-grid-scroll), а не sticky-элемент внутри неё.
         Оба блока - соседи во flex-строке с одинаковой высотой ряда (44px), выравнивание
         получается бесплатно без JS-подгонки. Колонки Подряд/% тут не нужны - они уже
         показаны в списке «сегодня». */
      const dim = daysInMonth(year, month);
      const dayNums = [...Array(dim)].map((_,i)=>i+1);

      /* Названия и клетки - два отдельных блока, значит строка-заголовок группы обязана
         иметь ПАРНУЮ строку той же высоты в сетке клеток, иначе ряды разъедутся.
         Обе стороны строим из одного и того же groupHabits(), в одном порядке. */
      const mGroups = groupHabits(active);
      const namesRows = `<div class="tr-grid-name-row tr-grid-name-head"><span>Привычка</span></div>` +
        mGroups.map(grp =>
          `<div class="tr-grid-name-row tr-grid-group-row">${esc(grp.title)}</div>` +
          grp.habits.map(h=>{
          const isLinked = h.id === BENCHMARK_HABIT_ID || isMachine(h);
          const nameCell = editingHabitId===h.id
            ? `<input type="text" class="tr-inline-input" id="tr-habit-name-input" value="${esc(h.name)}" data-id="${h.id}">`
            : `<span class="tr-habit-name" data-action="rename-habit" data-id="${h.id}"${habitHint(h)}>${esc(h.name)}${h.id===BENCHMARK_HABIT_ID?' <small class="tr-linked-note">· из вечернего чека</small>':''}${stateChip(h, DATA)}</span>`;
          return `<div class="tr-grid-name-row">
              ${nameCell}
              <button type="button" class="tr-icon-btn" data-action="archive-habit" data-id="${h.id}" title="Архивировать">×</button>
            </div>`;
          }).join('')
        ).join('');

      const cellsHeader = dayNums.map(d=>{
        const dateObj = new Date(year, month, d);
        const key = iso(dateObj);
        const wd = WD[(dateObj.getDay()+6)%7];
        const cls = key===todayISO ? ' tr-today-col' : '';
        return `<div class="tr-day-head${cls}"><span class="tr-day-wd">${wd}</span><span class="tr-day-num">${d}</span></div>`;
      }).join('');

      const cellsRows = mGroups.map(grp =>
        `<div class="tr-cells-group-row" style="grid-column:1/-1"></div>` +
        grp.habits.map(h=>{
        const isLinked = h.id === BENCHMARK_HABIT_ID || isMachine(h);
        return dayNums.map(d=>{
          const dateObj = new Date(year, month, d);
          const key = iso(dateObj);
          const future = key > todayISO;
          const done = !!(DATA.log[key] && DATA.log[key][h.id]);
          const cls = ['tr-cell'];
          if(done) cls.push('tr-done');
          if(key===todayISO) cls.push('tr-today-col');
          if(future) cls.push('tr-future');
          if(isLinked) cls.push('tr-linked');
          const act = (future || isLinked) ? '' : `data-action="toggle-habit" data-habit="${h.id}" data-date="${key}"`;
          const title = h.id===BENCHMARK_HABIT_ID ? `${key} - управляется блоком «Вечерний чек» ниже`
            : isMachine(h) ? `${key} - ставит ${(SOURCE_META[h.source]||{}).label}, руками не отмечается` : key;
          return `<div class="${cls.join(' ')}" ${act} title="${title}"></div>`;
        }).join('');
        }).join('')
      ).join('');

      wrap.innerHTML = `<div class="tr-grid-split">
          <div class="tr-grid-names">${namesRows}</div>
          <div class="tr-grid-scroll" id="tr-grid-scroll">
            <div class="tr-cells-grid" style="grid-template-columns:repeat(${dim}, 44px)">${cellsHeader}${cellsRows}</div>
          </div>
        </div>`;

      if(editingHabitId){
        const input = document.getElementById('tr-habit-name-input');
        if(input){ input.focus(); input.select(); }
      }
      // сразу подскроллить к сегодняшней колонке - иначе искать вручную среди ~30 колонок
      requestAnimationFrame(()=>{
        const scrollBox = document.getElementById('tr-grid-scroll');
        const col = scrollBox && scrollBox.querySelector('.tr-today-col');
        if(col && col.scrollIntoView) col.scrollIntoView({block:'nearest', inline:'center'});
      });
    } else {
      // ---------- десктоп: оригинальная единая сетка без изменений (26px клетки, sticky-колонка
      // названий работает штатно, потому что при ширине >=980px .tr-habit-table обычно не
      // требует горизонтального скролла вовсе - см. gridCols ниже) ----------
      const dim = daysInMonth(year, month);
      const dayNums = [...Array(dim)].map((_,i)=>i+1);
      // 280, а не 230: после блоков жизни имена стали длиннее («Писание вечером с женой»),
      // на 230 они резались многоточием - проверено скриншотом
      const gridCols = `280px repeat(${dim}, 26px)`;

      const header = `<div class="tr-habit-info tr-habit-info-head"><span>Привычка</span><span>Подряд</span><span>%</span></div>` +
        dayNums.map(d=>{
          const dateObj = new Date(year, month, d);
          const key = iso(dateObj);
          const wd = WD[(dateObj.getDay()+6)%7];
          const cls = key===todayISO ? ' tr-today-col' : '';
          return `<div class="tr-day-head${cls}"><span class="tr-day-wd">${wd}</span><span class="tr-day-num">${d}</span></div>`;
        }).join('');

      const rows = groupHabits(active).map(grp =>
        `<div class="tr-group-row" style="grid-column:1/-1">${esc(grp.title)}${grp.note?` <small>${esc(grp.note)}</small>`:''}</div>` +
        grp.habits.map(h=>{
        const streak = computeStreak(h, DATA.log, todayISO);
        const pctRaw = computeMonthPct(h, DATA.log, year, month, now);
        const pct = pctRaw===null ? '-' : pctRaw+'%';
        const isLinked = h.id === BENCHMARK_HABIT_ID || isMachine(h);
        const nameCell = editingHabitId===h.id
          ? `<input type="text" class="tr-inline-input" id="tr-habit-name-input" value="${esc(h.name)}" data-id="${h.id}">`
          : `<span class="tr-habit-name" data-action="rename-habit" data-id="${h.id}"${habitHint(h)}>${esc(h.name)}${sourceChip(h)}${classChip(h)}${h.id===BENCHMARK_HABIT_ID?' <small class="tr-linked-note">· из вечернего чека</small>':''}${stateChip(h, DATA)}</span>`;
        const cells = dayNums.map(d=>{
          const dateObj = new Date(year, month, d);
          const key = iso(dateObj);
          const future = key > todayISO;
          const done = !!(DATA.log[key] && DATA.log[key][h.id]);
          const cls = ['tr-cell'];
          if(done) cls.push('tr-done');
          if(key===todayISO) cls.push('tr-today-col');
          if(future) cls.push('tr-future');
          if(isLinked) cls.push('tr-linked');
          const act = (future || isLinked) ? '' : `data-action="toggle-habit" data-habit="${h.id}" data-date="${key}"`;
          const title = h.id===BENCHMARK_HABIT_ID ? `${key} - управляется блоком «Вечерний чек» ниже`
            : isMachine(h) ? `${key} - ставит ${(SOURCE_META[h.source]||{}).label}, руками не отмечается` : key;
          return `<div class="${cls.join(' ')}" ${act} title="${title}"></div>`;
        }).join('');
        return `<div class="tr-habit-info">
            <span class="tr-habit-name-box">${nameCell}${habitWhy(h)}</span>
            <span class="tr-habit-streak" title="${STREAK_TITLE}">${streak}</span>
            <span class="tr-habit-pct">${pct}</span>
            <button type="button" class="tr-icon-btn" data-action="archive-habit" data-id="${h.id}" title="Архивировать">×</button>
          </div>${cells}`;
        }).join('')
      ).join('');

      wrap.innerHTML = `<div class="tr-habit-table" style="grid-template-columns:${gridCols}">${header}${rows}</div>`;

      if(editingHabitId){
        const input = document.getElementById('tr-habit-name-input');
        if(input){ input.focus(); input.select(); }
      }
    }

    const archived = (DATA.habits||[]).filter(h=>h.archived);
    const toggleBtn = document.getElementById('tr-habits-archive-toggle');
    if(toggleBtn){
      toggleBtn.textContent = archived.length ? (showArchivedHabits ? 'скрыть архив' : `архив (${archived.length})`) : '';
      toggleBtn.style.display = archived.length ? '' : 'none';
    }
    const archList = document.getElementById('tr-habits-archive-list');
    if(archList){
      archList.innerHTML = (showArchivedHabits && archived.length)
        ? archived.map(h=>`<span class="tr-archived-chip">${esc(h.name)} <button type="button" class="tr-icon-btn" data-action="restore-habit" data-id="${h.id}" title="Вернуть">↺</button></span>`).join('')
        : '';
    }
  }

  /* ---------- рендер: блок 2, вечерний чек ---------- */
  function renderBenchmark(){
    const wrap = document.getElementById('tr-benchmark-wrap');
    if(!wrap) return;
    const todayISO = iso(new Date());
    const todayRec = DATA.benchmark[todayISO] || {};

    /* Каркас без контуров - штатное состояние свежей копии движка: список
       вопросов у каждого свой, готовым он не поставляется. Показываем, что
       делать, вместо пустого прямоугольника и вместо зелёной галочки ни о чём */
    if(!BENCHMARK_CONTOURS.length){
      wrap.innerHTML = `<div class="tr-bm-empty">Список вопросов вечернего чека пуст.
        Впиши свои в <code>static/tab-track.js</code>, массив <code>BENCHMARK_CONTOURS</code>:
        у каждой строки <code>id</code>, короткое имя и сам вопрос.
        Пока список пуст, привычка «вечерний чек» не закрывается автоматически</div>`;
      return;
    }

    const todayRows = BENCHMARK_CONTOURS.map(c=>{
      const val = todayRec[c.id];
      const btn = (state, label) => `<button type="button" class="tr-bm-btn tr-bm-${state}${val===state?' tr-active':''}"
        data-action="set-benchmark" data-contour="${c.id}" data-state="${state}">${label}</button>`;
      return `<div class="tr-bm-row">
        <div class="tr-bm-text"><b>${c.id}. ${esc(c.name)}.</b> ${esc(c.question)} <span class="tr-bm-anchor">${esc(c.anchor)}</span></div>
        <div class="tr-bm-buttons">${btn('yes','Да')}${btn('partial','Частично')}${btn('no','Нет')}</div>
      </div>`;
    }).join('');

    const days = [];
    const base = new Date();
    for(let i=29; i>=0; i--){ const d=new Date(base); d.setDate(d.getDate()-i); days.push(iso(d)); }

    const trendRows = BENCHMARK_CONTOURS.map(c=>{
      const dots = days.map(dk=>{
        const st = (DATA.benchmark[dk]||{})[c.id];
        const cls = st ? `tr-dot-${st}` : 'tr-dot-empty';
        return `<span class="tr-bm-dot ${cls}" title="${dk}: ${st?esc(c.name):'нет данных'}"></span>`;
      }).join('');
      return `<div class="tr-bm-trend-row"><span class="tr-bm-trend-label" title="${esc(c.name)} · ${esc(c.anchor)}">${c.id}</span><span class="tr-bm-trend-dots">${dots}</span></div>`;
    }).join('');

    wrap.innerHTML = `
      <div class="tr-bm-today">${todayRows}</div>
      <div class="tr-bm-trend">
        <div class="tr-bm-trend-caption">Тренд за 30 дней · зелёный да · жёлтый частично · красный нет</div>
        ${trendRows}
      </div>`;
  }

  /* ---------- рендер: блок 3, месячный смотр по сферам ---------- */
  function renderSpheres(){
    const wrap = document.getElementById('tr-spheres-wrap');
    if(!wrap) return;
    const now = new Date();
    const curKey = monthKey(now);
    const active = (DATA.spheres||[]).filter(s=>!s.archived);

    const allMonths = Object.keys(DATA.monthly||{}).sort();
    const pastMonths = allMonths.filter(m=>m!==curKey).slice(-5);

    const header = `<div class="tr-sphere-row tr-sphere-head">
      <span class="tr-sphere-name-col">Сфера</span>
      <span class="tr-sphere-hist-col">История</span>
      <span class="tr-sphere-cur-col">Этот месяц: балл 1-10 · было · меняю</span>
    </div>`;

    let rows;
    if(!active.length){
      rows = '<div class="tr-empty">Сфер пока нет. Добавь первую строкой ниже.</div>';
    } else {
      rows = active.map(s=>{
        const histChips = pastMonths.map(mk=>{
          const rec = (DATA.monthly[mk]||{})[s.id];
          if(!rec || typeof rec.score!=='number'){
            return `<span class="tr-hist-chip tr-hist-empty" title="${mMonthLabel(mk)}: нет оценки">-</span>`;
          }
          const title = `${mMonthLabel(mk)}: ${rec.score} из 10${rec.was?(' · было: '+esc(rec.was)):''}${rec.change?(' · меняю: '+esc(rec.change)):''}`;
          return `<span class="tr-hist-chip" style="background:${scoreColor(rec.score)};color:${scoreColorText(rec.score)}" title="${title}">${rec.score}</span>`;
        }).join('');
        const cur = (DATA.monthly[curKey]||{})[s.id] || {};
        const nameCell = editingSphereId===s.id
          ? `<input type="text" class="tr-inline-input" id="tr-sphere-name-input" value="${esc(s.name)}" data-id="${s.id}">`
          : `<span class="tr-sphere-name" data-action="rename-sphere" data-id="${s.id}" title="Нажми, чтобы переименовать">${esc(s.name)}</span>`;
        return `<div class="tr-sphere-row">
          <span class="tr-sphere-name-col">${nameCell}
            <button type="button" class="tr-icon-btn" data-action="archive-sphere" data-id="${s.id}" title="Архивировать">×</button>
          </span>
          <span class="tr-sphere-hist-col">${histChips || '<span class="tr-hist-empty-note">-</span>'}</span>
          <span class="tr-sphere-cur-col">
            <input type="number" class="tr-score-input" min="1" max="10" step="1" placeholder="-"
              value="${typeof cur.score==='number'?cur.score:''}"
              data-action="set-sphere-field" data-sphere="${s.id}" data-field="score">
            <input type="text" class="tr-note-input" placeholder="что было" maxlength="140"
              value="${esc(cur.was||'')}" data-action="set-sphere-field" data-sphere="${s.id}" data-field="was">
            <input type="text" class="tr-note-input" placeholder="что меняю" maxlength="140"
              value="${esc(cur.change||'')}" data-action="set-sphere-field" data-sphere="${s.id}" data-field="change">
          </span>
        </div>`;
      }).join('');
    }

    wrap.innerHTML = header + rows;

    if(editingSphereId){
      const input = document.getElementById('tr-sphere-name-input');
      if(input){ input.focus(); input.select(); }
    }

    const archived = (DATA.spheres||[]).filter(s=>s.archived);
    const toggleBtn = document.getElementById('tr-spheres-archive-toggle');
    if(toggleBtn){
      toggleBtn.textContent = archived.length ? (showArchivedSpheres ? 'скрыть архив' : `архив (${archived.length})`) : '';
      toggleBtn.style.display = archived.length ? '' : 'none';
    }
    const archList = document.getElementById('tr-spheres-archive-list');
    if(archList){
      archList.innerHTML = (showArchivedSpheres && archived.length)
        ? archived.map(s=>`<span class="tr-archived-chip">${esc(s.name)} <button type="button" class="tr-icon-btn" data-action="restore-sphere" data-id="${s.id}" title="Вернуть">↺</button></span>`).join('')
        : '';
    }
  }

  function renderAll(){
    renderSummary(); renderHabits(); renderBenchmark(); renderSpheres();
  }

  /* ---------- события (делегирование на .tr-body, один раз на монтирование) ---------- */
  function onBodyClick(e){
    const t = e.target.closest('[data-action]');
    if(!t) return;
    const action = t.dataset.action;
    if(action==='toggle-habit'){
      toggleHabitDay(t.dataset.habit, t.dataset.date); renderSummary(); renderHabits();
    } else if(action==='rename-habit'){
      editingHabitId = t.dataset.id; renderHabits();
    } else if(action==='archive-habit'){
      archiveHabit(t.dataset.id); renderSummary(); renderHabits();
    } else if(action==='restore-habit'){
      restoreHabit(t.dataset.id); renderSummary(); renderHabits();
    } else if(action==='add-habit'){
      const inp = document.getElementById('tr-habit-new');
      if(addHabit(inp.value)){ inp.value=''; renderSummary(); renderHabits(); }
      inp.focus();
    } else if(action==='month-prev'){
      viewMonth -= 1; if(viewMonth < 0){ viewMonth = 11; viewYear -= 1; }
      renderHabits();
    } else if(action==='month-next'){
      viewMonth += 1; if(viewMonth > 11){ viewMonth = 0; viewYear += 1; }
      renderHabits();
    } else if(action==='month-today'){
      const n = new Date(); viewYear = n.getFullYear(); viewMonth = n.getMonth();
      mobileGridMode = false; // «сегодня» - это и есть выход из режима полной сетки обратно в быстрый список
      renderHabits();
    } else if(action==='toggle-grid-mode'){
      mobileGridMode = !mobileGridMode; renderHabits();
    } else if(action==='set-benchmark'){
      setBenchmark(iso(new Date()), t.dataset.contour, t.dataset.state); renderBenchmark(); renderHabits(); renderSummary();
    } else if(action==='rename-sphere'){
      editingSphereId = t.dataset.id; renderSpheres();
    } else if(action==='archive-sphere'){
      archiveSphere(t.dataset.id); renderSummary(); renderSpheres();
    } else if(action==='restore-sphere'){
      restoreSphere(t.dataset.id); renderSummary(); renderSpheres();
    } else if(action==='add-sphere'){
      const inp = document.getElementById('tr-sphere-new');
      if(addSphere(inp.value)){ inp.value=''; renderSummary(); renderSpheres(); }
      inp.focus();
    } else if(action==='toggle-archive-view'){
      if(t.dataset.kind==='habits'){ showArchivedHabits=!showArchivedHabits; renderHabits(); }
      else if(t.dataset.kind==='spheres'){ showArchivedSpheres=!showArchivedSpheres; renderSpheres(); }
    }
  }

  function onBodyChange(e){
    const t = e.target.closest('[data-action="set-sphere-field"]');
    if(!t) return;
    const field = t.dataset.field;
    let value = t.value;
    if(field==='score'){
      value = value===''? null : Math.max(1, Math.min(10, parseInt(value,10)||1));
      t.value = value===null ? '' : value;
    } else {
      value = value.trim();
    }
    setSphereMonthly(t.dataset.sphere, monthKey(new Date()), field, value);
    /* renderSpheres() тут намеренно НЕ вызываем: три поля строки (балл/было/меняю)
       заполняются подряд, и пересборка DOM на change одного поля рвёт Tab-переход
       к следующему - соседний ещё не сохранённый инпут исчезает вместе со значением.
       История показывает только ПРОШЛые месяцы, текущий месяц её не трогает - рендер
       не нужен, поле и так показывает то, что ввёл пользователь. */
    renderSummary();
  }

  function onBodyFocusout(e){
    if(e.target.id==='tr-habit-name-input' && editingHabitId===e.target.dataset.id){
      const id = e.target.dataset.id;
      renameHabit(id, e.target.value);
      editingHabitId = null;
      renderHabits();
    } else if(e.target.id==='tr-sphere-name-input' && editingSphereId===e.target.dataset.id){
      const id = e.target.dataset.id;
      renameSphere(id, e.target.value);
      editingSphereId = null;
      renderSpheres();
    }
  }

  function onBodyKeydown(e){
    if(e.target.id==='tr-habit-new' && e.key==='Enter'){
      e.preventDefault(); document.getElementById('tr-habit-add-btn').click();
    } else if(e.target.id==='tr-sphere-new' && e.key==='Enter'){
      e.preventDefault(); document.getElementById('tr-sphere-add-btn').click();
    } else if(e.target.id==='tr-habit-name-input'){
      if(e.key==='Enter'){ e.preventDefault(); e.target.blur(); }
      else if(e.key==='Escape'){ editingHabitId=null; renderHabits(); }
    } else if(e.target.id==='tr-sphere-name-input'){
      if(e.key==='Enter'){ e.preventDefault(); e.target.blur(); }
      else if(e.key==='Escape'){ editingSphereId=null; renderSpheres(); }
    }
  }

  function wireOnce(){
    const body = ROOT.querySelector('.tr-body');
    body.addEventListener('click', onBodyClick);
    body.addEventListener('change', onBodyChange);
    body.addEventListener('focusout', onBodyFocusout);
    body.addEventListener('keydown', onBodyKeydown);
  }

  /* ---------- разметка + монтирование ---------- */
  const SKELETON = `
    <div class="tr-root">
      <div class="tr-summary" id="tr-summary"></div>
      <div class="tr-body">
        <section class="tr-block tr-habits-block">
          <div class="tr-block-head">
            <h2>Ежедневные привычки</h2>
            <div class="tr-month-nav">
              <button type="button" class="tr-month-btn" data-action="month-prev" title="Предыдущий месяц">‹</button>
              <span class="tr-month-label" id="tr-month-label"></span>
              <button type="button" class="tr-month-btn" data-action="month-next" title="Следующий месяц">›</button>
              <button type="button" class="tr-month-today" data-action="month-today">сегодня</button>
            </div>
            <button type="button" class="tr-mode-toggle" id="tr-mode-toggle" data-action="toggle-grid-mode" style="display:none"></button>
            <span class="tr-hint">Колонка «Подряд» - сколько дней подряд, считая назад от сегодня. Любой пропуск обрывает счёт</span>
          </div>
          <div class="tr-habits-wrap" id="tr-habits-wrap"></div>
          <div class="tr-add-row">
            <input type="text" id="tr-habit-new" class="tr-input" placeholder="Новая привычка" maxlength="60">
            <select id="tr-habit-new-group" class="tr-input tr-select-group" title="Блок жизни новой привычки. Без него привычка падает в «Прочее» и вечером про неё не спрашивают">${HABIT_GROUPS.map(g=>`<option value="${g.id}">${esc(g.title)}</option>`).join('')}</select>
            <button type="button" id="tr-habit-add-btn" class="tr-btn-add" data-action="add-habit">Добавить</button>
            <button type="button" id="tr-habits-archive-toggle" class="tr-link-btn" data-action="toggle-archive-view" data-kind="habits"></button>
          </div>
          <div class="tr-archive-list" id="tr-habits-archive-list"></div>
        </section>

        <div class="tr-row2">
          <section class="tr-block tr-benchmark-block">
            <div class="tr-block-head"><h2>Вечерний чек</h2></div>
            <div class="tr-benchmark-wrap" id="tr-benchmark-wrap"></div>
          </section>

          <section class="tr-block tr-spheres-block">
            <div class="tr-block-head">
              <h2>Месячный смотр по сферам</h2>
              <span class="tr-hint">Заполняй ближе к концу месяца: балл 1-10, что было, что меняю на следующий. История ниже - последние 5 месяцев.</span>
            </div>
            <div class="tr-spheres-wrap" id="tr-spheres-wrap"></div>
            <div class="tr-add-row">
              <input type="text" id="tr-sphere-new" class="tr-input" placeholder="Новая сфера" maxlength="40">
              <button type="button" id="tr-sphere-add-btn" class="tr-btn-add" data-action="add-sphere">Добавить</button>
              <button type="button" id="tr-spheres-archive-toggle" class="tr-link-btn" data-action="toggle-archive-view" data-kind="spheres"></button>
            </div>
            <div class="tr-archive-list" id="tr-spheres-archive-list"></div>
          </section>
        </div>
      </div>
    </div>`;

  const CSS_TEXT = `
    .tr-root{--tr-amber:#f9ab00;height:100%;display:flex;flex-direction:column;overflow:hidden;font-family:"Manrope",-apple-system,sans-serif}
    .tr-summary{flex:0 0 auto;display:flex;align-items:center;gap:10px;padding:9px 16px;border-bottom:1px solid var(--bd-soft);font-size:12.5px;color:var(--txt);background:#fafbfc;flex-wrap:wrap}
    .tr-summary-item b{color:var(--blue);font-weight:700}
    .tr-summary-sep{color:var(--bd)}
    .tr-body{flex:1 1 auto;min-height:0;display:flex;flex-direction:column;gap:10px;padding:10px 16px 12px;overflow:hidden}
    .tr-block{display:flex;flex-direction:column;min-height:0}
    .tr-block-head{display:flex;align-items:baseline;gap:10px;margin-bottom:6px;flex:0 0 auto;flex-wrap:wrap}
    .tr-block-head h2{font:600 13.5px/1.2 "Unbounded",sans-serif;margin:0;color:var(--txt)}
    .tr-hint{font-size:10.5px;color:var(--txt-dim)}
    .tr-month-nav{display:flex;align-items:center;gap:4px}
    .tr-month-btn{border:1px solid var(--bd);background:#fff;border-radius:4px;width:22px;height:22px;font-size:13px;cursor:pointer;color:var(--txt-dim);line-height:1;padding:0;font-family:inherit}
    .tr-month-btn:hover{background:var(--hover);color:var(--txt)}
    .tr-month-label{font-size:11.5px;font-weight:600;color:var(--txt);min-width:92px;text-align:center}
    .tr-month-today{border:0;background:none;color:var(--blue);font-size:10.5px;cursor:pointer;font-family:inherit;text-decoration:underline;padding:0}
    /* 66, а не 54: с блоками жизни строк стало 30 вместо 10 (23 привычки + 7 заголовков
       живых групп, замерпо tracker.json),
       на 54% половина списка уезжала под скролл и «Фокус» не был виден вовсе */
    .tr-habits-block{flex:1 1 66%;max-height:66%}
    .tr-habits-wrap{flex:1 1 auto;min-height:0;overflow:auto;border-radius:6px;border:1px solid var(--bd-soft)}
    .tr-add-row{flex:0 0 auto;display:flex;align-items:center;gap:8px;margin-top:7px}
    .tr-input{border:1px solid var(--bd);border-radius:4px;padding:6px 9px;font-size:12.5px;font-family:inherit;width:190px}
    .tr-btn-add{border:0;background:var(--blue);color:#fff;border-radius:4px;padding:6px 14px;font-size:12.5px;cursor:pointer;font-family:inherit;font-weight:600}
    .tr-btn-add:hover{opacity:.9}
    .tr-link-btn{border:0;background:none;color:var(--txt-dim);font-size:11px;cursor:pointer;font-family:inherit;text-decoration:underline;margin-left:auto}
    .tr-archive-list{display:flex;flex-wrap:wrap;gap:6px;margin-top:6px;flex:0 0 auto}
    .tr-archived-chip{display:inline-flex;align-items:center;gap:5px;background:var(--hover);border-radius:12px;padding:3px 9px;font-size:11px;color:var(--txt-dim)}
    .tr-icon-btn{border:0;background:none;color:var(--txt-dim);cursor:pointer;font-size:13px;padding:0 3px;line-height:1;font-family:inherit}
    .tr-icon-btn:hover{color:var(--red)}
    .tr-empty{padding:16px;color:var(--txt-dim);font-size:12.5px;text-align:center}

    .tr-habit-table{display:grid;grid-auto-rows:32px}
    .tr-habit-info{display:flex;align-items:center;gap:6px;padding:0 8px;border-right:1px solid var(--bd-soft);border-bottom:1px solid var(--bd-soft);background:#fff;overflow:hidden;position:sticky;left:0;z-index:2}
    .tr-habit-info-head{background:#fafafa;font-size:9.5px;text-transform:uppercase;letter-spacing:.4px;color:var(--txt-dim);font-weight:700;position:sticky;left:0;top:0;z-index:3}
    .tr-habit-info-head span{flex:0 0 auto}
    .tr-habit-info-head span:first-child{flex:1}
    .tr-habit-name{flex:1;font-size:12.5px;cursor:pointer;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
    .tr-habit-name:hover{color:var(--blue)}
    .tr-linked-note{color:var(--txt-dim);font-weight:400;font-size:10px}

    /* ---------- блоки жизни (habit.group) и метка источника галочки (habit.source) ----------
       Строка-заголовок в десктопной сетке занимает всю ширину (grid-column:1/-1) и залипает
       по левому краю - иначе при горизонтальном скролле названия блоков уезжают из вида. */
    .tr-group-row{display:flex;align-items:center;gap:8px;padding:0 8px;background:#f4f6f8;
      border-bottom:1px solid var(--bd-soft);font-size:9.5px;text-transform:uppercase;
      letter-spacing:.5px;color:var(--txt-dim);font-weight:700;position:sticky;left:0;z-index:2}
    .tr-group-row small{text-transform:none;letter-spacing:0;font-weight:400;font-size:10.5px;opacity:.8}
    .tr-group-head{padding:12px 4px 5px;font-size:10px;text-transform:uppercase;letter-spacing:.5px;
      color:var(--txt-dim);font-weight:700;border-bottom:1px solid var(--bd-soft)}
    .tr-group-head small{display:block;text-transform:none;letter-spacing:0;font-weight:400;
      font-size:11px;margin-top:2px;opacity:.8}
    .tr-grid-group-row{background:#f4f6f8;font-size:9.5px;text-transform:uppercase;letter-spacing:.4px;
      color:var(--txt-dim);font-weight:700}
    .tr-cells-group-row{background:#f4f6f8;border-bottom:1px solid var(--bd-soft)}
    /* чип «сама / спрошу / трекер»: чего владельцу НЕ надо делать руками */
    .tr-src{font-weight:400;font-size:10px;padding:1px 5px;border-radius:8px;margin-left:5px;
      white-space:nowrap;cursor:help;vertical-align:middle}
    .tr-src-auto{background:#e6f4ea;color:#1e7e34}
    .tr-src-ask{background:#eef1f5;color:var(--txt-dim)}
    .tr-src-device{background:#fff3e0;color:#9a6200}
    .tr-src-device{background:#e8f0fe;color:#174ea6}
    .tr-src-engine{background:#e6f4ea;color:#1e7e34}
    /* метка КЛАССА АВТОРСТВА: видна в самой строке, без раскрытия блока «почему
       это в списке». Без неё личный канон владельца и порог автора с цитатой
       выглядят одинаково, пока не кликнешь */
    .tr-class{font-weight:600;font-size:10px;padding:1px 5px;border-radius:8px;margin-left:5px;
      white-space:nowrap;cursor:help;vertical-align:middle;letter-spacing:.02em}
    .tr-class-owner_canon{background:#f3e8fd;color:#6b21a8}
    .tr-class-owner_requirement{background:#fff8e1;color:#8a6100}
    /* «нет данных» и «протухли»: строка прибора до первого входа владельца НЕ зелёная
       и НЕ пустая - у неё своё третье состояние, и в знаменатель дня она не идёт */
    .tr-src-nodata{background:#fdecea;color:#a50e0e}
    /* ВИДИМОЕ обоснование привычки: раскрывается кликом, а не наведением мыши -
       на телефоне наведения не существует, и тултип там недоступен вовсе */
    .tr-why{margin-top:3px;font-size:10.5px;color:var(--txt-dim)}
    .tr-why>summary{cursor:pointer;color:var(--blue);list-style:none;font-size:10.5px;user-select:none}
    .tr-why>summary::-webkit-details-marker{display:none}
    .tr-why>summary::before{content:'ⓘ ';opacity:.7}
    .tr-why[open]>summary{margin-bottom:4px}
    .tr-why-hint{color:var(--txt);margin-bottom:3px}
    .tr-why-row{margin:2px 0;line-height:1.45}
    .tr-why-row code{font:11px/1 "JetBrains Mono",monospace;background:#f2f4f7;padding:1px 4px;border-radius:3px}
    .tr-why-quote{margin:3px 0;padding-left:7px;border-left:2px solid var(--bd);font-style:italic;line-height:1.45}
    .tr-why-note{color:#9a6200}
    .tr-habit-name-box{display:flex;flex-direction:column;min-width:0}
    .tr-select-group{max-width:150px}
    .tr-habit-streak{font-size:10.5px;color:var(--txt-dim);white-space:nowrap;cursor:help;width:16px;text-align:right}
    .tr-habit-pct{font-size:10.5px;color:var(--txt-dim);width:28px;text-align:right}
    .tr-day-head{display:flex;flex-direction:column;align-items:center;justify-content:center;font-size:9px;color:var(--txt-dim);border-bottom:1px solid var(--bd-soft);border-left:1px solid var(--bd-soft);background:#fafafa;position:sticky;top:0;z-index:1}
    .tr-day-head .tr-day-wd{font-size:7.5px;text-transform:uppercase;opacity:.65}
    .tr-day-head.tr-today-col{background:#e8f0fe;color:var(--blue);font-weight:700}
    .tr-cell{border-bottom:1px solid var(--bd-soft);border-left:1px solid var(--bd-soft);cursor:pointer;position:relative;background:#fff}
    .tr-cell:hover{background:var(--hover)}
    .tr-cell.tr-done::after{content:"";position:absolute;inset:6px;background:var(--green);border-radius:3px}
    .tr-cell.tr-today-col{background:#f8fafe}
    .tr-cell.tr-future{cursor:default;background:#fbfbfb}
    .tr-cell.tr-future:hover{background:#fbfbfb}
    .tr-cell.tr-linked{cursor:help}
    .tr-cell.tr-linked:not(.tr-done){background:repeating-linear-gradient(45deg,#fff,#fff 5px,#fafafa 5px,#fafafa 10px)}

    .tr-row2{flex:1 1 46%;display:flex;gap:14px;min-height:0;overflow:hidden}
    .tr-benchmark-block,.tr-spheres-block{flex:1 1 50%;display:flex;flex-direction:column;min-height:0;overflow:hidden;border:1px solid var(--bd-soft);border-radius:6px;padding:9px 11px}
    .tr-benchmark-wrap,.tr-spheres-wrap{flex:1 1 auto;min-height:0;overflow:auto}

    .tr-bm-empty{font-size:12px;color:var(--txt-dim);line-height:1.5;padding:8px}
    .tr-bm-today{display:flex;flex-direction:column;gap:2px;margin-bottom:8px}
    .tr-bm-row{display:flex;align-items:center;gap:8px;padding:3px 5px;border-radius:5px}
    .tr-bm-row:hover{background:var(--hover)}
    .tr-bm-text{flex:1;font-size:11px;line-height:1.3;color:var(--txt)}
    .tr-bm-text b{font-weight:600}
    .tr-bm-anchor{color:var(--txt-dim);font-size:9.5px;font-style:italic;white-space:nowrap;margin-left:2px}
    .tr-bm-buttons{display:flex;gap:4px;flex:0 0 auto}
    .tr-bm-btn{border:1px solid var(--bd);background:#fff;border-radius:12px;padding:3px 8px;font-size:10px;cursor:pointer;color:var(--txt-dim);font-family:inherit}
    .tr-bm-btn:hover{background:var(--hover)}
    .tr-bm-btn.tr-active.tr-bm-yes{background:var(--green);border-color:var(--green);color:#fff}
    .tr-bm-btn.tr-active.tr-bm-partial{background:var(--tr-amber);border-color:var(--tr-amber);color:#fff}
    .tr-bm-btn.tr-active.tr-bm-no{background:var(--red);border-color:var(--red);color:#fff}
    .tr-bm-trend{border-top:1px solid var(--bd-soft);padding-top:7px}
    .tr-bm-trend-caption{font-size:10px;color:var(--txt-dim);margin-bottom:4px}
    .tr-bm-trend-row{display:flex;align-items:center;gap:6px;height:15px}
    .tr-bm-trend-label{width:14px;font-size:9.5px;color:var(--txt-dim);text-align:right;cursor:help}
    .tr-bm-trend-dots{display:flex;gap:2px}
    .tr-bm-dot{width:8px;height:8px;border-radius:2px;display:inline-block}
    .tr-dot-yes{background:var(--green)}
    .tr-dot-partial{background:var(--tr-amber)}
    .tr-dot-no{background:var(--red)}
    .tr-dot-empty{background:var(--bd-soft)}

    .tr-sphere-row{display:flex;align-items:center;gap:8px;padding:4px 2px;border-bottom:1px solid var(--bd-soft);min-height:28px}
    .tr-sphere-head{font-size:9.5px;text-transform:uppercase;letter-spacing:.4px;color:var(--txt-dim);font-weight:700;position:sticky;top:0;background:#fafafa;z-index:1}
    .tr-sphere-name-col{flex:0 0 112px;display:flex;align-items:center;gap:3px;overflow:hidden}
    .tr-sphere-name{font-size:12px;cursor:pointer;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;flex:1}
    .tr-sphere-name:hover{color:var(--blue)}
    .tr-sphere-hist-col{flex:0 0 150px;display:flex;gap:3px;flex-wrap:wrap}
    .tr-hist-chip{display:inline-flex;align-items:center;justify-content:center;width:22px;height:18px;border-radius:4px;font-size:10px;font-weight:600;cursor:help}
    .tr-hist-empty{background:var(--bd-soft);color:var(--txt-dim)}
    .tr-hist-empty-note{font-size:10.5px;color:var(--txt-dim)}
    .tr-sphere-cur-col{flex:1 1 auto;display:flex;gap:5px;min-width:0}
    .tr-score-input{width:36px;border:1px solid var(--bd);border-radius:4px;padding:4px 2px;font-size:11.5px;font-family:inherit;text-align:center}
    .tr-note-input{flex:1;min-width:0;border:1px solid var(--bd);border-radius:4px;padding:4px 6px;font-size:11px;font-family:inherit}
    .tr-inline-input{flex:1;border:1px solid var(--blue);border-radius:4px;padding:3px 6px;font-size:12px;font-family:inherit}

    /* ---------- мобильный список «сегодня» (замена месячной сетки на <=600px, см. renderHabits) ----------
       Единственный настоящий тап-таргет здесь - крупная кнопка-переключатель tr-quick-toggle,
       48x48 (с запасом над стандартом касания 44x44). «Подряд» и % - текст, не действие, дублирует
       то, что раньше показывала сетка - это и есть «компактная история отдельно». */
    .tr-quick-list{display:flex;flex-direction:column}
    .tr-quick-row{display:flex;align-items:center;gap:10px;padding:10px 4px;border-bottom:1px solid var(--bd-soft)}
    .tr-quick-row:last-child{border-bottom:0}
    .tr-quick-info{flex:1;min-width:0;display:flex;flex-direction:column;gap:2px}
    .tr-quick-name{font-size:14px;color:var(--txt);cursor:pointer;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;padding:4px 0;display:inline-block}
    .tr-quick-name:hover{color:var(--blue)}
    .tr-quick-meta{font-size:11px;color:var(--txt-dim)}
    .tr-quick-toggle{flex:0 0 auto;width:48px;height:48px;border-radius:10px;border:2px solid var(--bd);background:#fff;font-size:20px;line-height:1;color:var(--green);cursor:pointer;font-family:inherit;display:flex;align-items:center;justify-content:center}
    .tr-quick-toggle.tr-done{background:var(--green);border-color:var(--green);color:#fff}
    /* :not(.tr-done) - зеркало правила .tr-cell.tr-linked:not(.tr-done) в исходной сетке:
       залоченная (управляется вечерним чеком) кнопка штрихуется, только пока не сделана;
       как только вечерний чек отмечен - показываем обычный зелёный «сделано», а не штриховку */
    .tr-quick-toggle.tr-locked:not(.tr-done){cursor:help;color:var(--bd);background:repeating-linear-gradient(45deg,#fff,#fff 5px,#fafafa 5px,#fafafa 10px)}
    .tr-quick-archive{flex:0 0 auto;width:44px;height:44px;font-size:17px;display:flex;align-items:center;justify-content:center}
    .tr-mode-toggle{border:1px solid var(--bd);background:#fff;color:var(--txt-dim);border-radius:14px;padding:7px 13px;font-size:11.5px;cursor:pointer;font-family:inherit}
    .tr-mode-toggle:hover{background:var(--hover);color:var(--txt)}

    /* ---------- та же сетка на мобильном (просмотр другого месяца или «весь месяц» из
       списка «сегодня»): клетки укрупнены с 26x32 до стандарта касания 44x44. Колонка
       названий - ОТДЕЛЬНЫЙ несворачивающийся блок рядом со скроллящейся сеткой клеток
       (см. комментарий в renderHabits про поломку sticky-грид-айтема), а не sticky-
       элемент внутри той же таблицы. Классы включаются только из JS-ветки mobile
       (renderHabits), на desktop не появляются вовсе - медиа-запрос не нужен. ---------- */
    .tr-grid-split{display:flex;align-items:flex-start}
    /* width+overflow:hidden - не только flex:0 0 108px: у flex-элемента без явной ширины
       автоматический min-width равен min-content его содержимого (длинное название
       привычки типа «заметки от руки от руки» без этого раздувает колонку до 252px вместо
       108px - проверено живьём) */
    .tr-grid-names{flex:0 0 108px;width:108px;overflow:hidden;display:flex;flex-direction:column}
    .tr-grid-name-row{height:44px;display:flex;align-items:center;gap:6px;padding:0 6px;
      border-right:1px solid var(--bd-soft);border-bottom:1px solid var(--bd-soft);background:#fff;overflow:hidden}
    .tr-grid-name-head{background:#fafafa;font-size:9.5px;text-transform:uppercase;letter-spacing:.4px;color:var(--txt-dim);font-weight:700}
    .tr-grid-name-row .tr-habit-name{font-size:13.5px;flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;cursor:pointer}
    .tr-grid-name-row .tr-habit-name:hover{color:var(--blue)}
    .tr-grid-name-row .tr-icon-btn{width:32px;height:32px;font-size:16px;display:flex;align-items:center;justify-content:center;flex:0 0 auto}
    .tr-grid-scroll{flex:1 1 auto;min-width:0;overflow-x:auto;-webkit-overflow-scrolling:touch}
    .tr-cells-grid{display:grid;grid-auto-rows:44px}
    .tr-cells-grid .tr-day-head{font-size:11px}
    .tr-cells-grid .tr-day-head .tr-day-wd{font-size:8.5px}

    @media (max-width:600px){
      /* ---------- навигация по месяцам и добавление привычки/сферы - тоже цели касания,
         было 22x22 у ‹ › - тапалось так же неточно, как и клетки ---------- */
      .tr-month-btn{width:44px;height:44px;font-size:18px}
      .tr-month-today{padding:8px 10px;font-size:12.5px}
      .tr-add-row{flex-wrap:wrap}
      .tr-input{flex:1 1 100%;min-height:42px;font-size:14px}
      .tr-btn-add{min-height:42px;padding:8px 16px;font-size:13px}

      /* ---------- вечерний вечерний чек: три кнопки Да/Частично/Нет в строке были 3px/8px
         паддинга при 10px шрифте - фактическая цель касания ~20px высотой. Текст вопроса
         и кнопки идут друг под другом, кнопки - равная треть ширины, не ниже 44px. Текст
         восьми контуров и якоря НЕ меняю, только раскладку. ---------- */
      .tr-bm-row{flex-direction:column;align-items:stretch;gap:7px;padding:9px 6px;border-bottom:1px solid var(--bd-soft)}
      .tr-bm-text{font-size:12.5px}
      .tr-bm-buttons{display:grid;grid-template-columns:repeat(3,1fr);gap:6px}
      .tr-bm-btn{padding:0;min-height:44px;font-size:12.5px;border-radius:8px;display:flex;align-items:center;justify-content:center}

      /* ---------- месячный смотр по сферам: было 112px+150px колонок в ~336px доступной
         ширины - «Этот месяц» (балл + было + меняю) получал ~70px на три поля. Строка
         сферы превращается в карточку, каждое под-поле - на всю ширину, заголовки колонок
         (нужны только для табличной раскладки) скрываются - подписи есть в placeholder. ---------- */
      .tr-sphere-head{display:none}
      .tr-sphere-row{flex-direction:column;align-items:stretch;gap:7px;padding:10px 8px;border:1px solid var(--bd-soft);border-radius:8px;margin-bottom:8px}
      .tr-sphere-name-col{flex:none;width:100%}
      .tr-sphere-hist-col{flex:none;width:100%}
      .tr-hist-chip,.tr-hist-empty{width:30px;height:26px;font-size:11px}
      .tr-sphere-cur-col{flex:none;width:100%;flex-direction:column;gap:8px}
      .tr-score-input{width:72px;min-height:44px;font-size:15px}
      .tr-note-input{min-height:44px;font-size:13.5px}
    }
  `;

  function injectStyles(){
    if(document.getElementById('tr-styles')) return;
    const style = document.createElement('style');
    style.id = 'tr-styles';
    style.textContent = CSS_TEXT;
    document.head.appendChild(style);
  }

  function renderTrack(container){
    injectStyles();
    ROOT = container;
    const now = new Date();
    viewYear = now.getFullYear();
    viewMonth = now.getMonth();
    mobileGridMode = false; // каждое открытие вкладки - заново с быстрого списка «сегодня», а не там, где бросили в прошлый раз
    container.innerHTML = SKELETON;
    wireOnce();

    /* Поворот телефона / ресайз окна меняет mobile<->desktop структурно (список «сегодня»
       vs сетка), а не только визуально через CSS - поэтому нужен re-render. Слушатель на
       window переживает смену вкладки (DOM вкладки просто заменится), поэтому снимаем
       предыдущий перед установкой нового и глушим колбэк по ROOT!==container, если
       вкладку успели переключить. */
    if(resizeHandler) window.removeEventListener('resize', resizeHandler);
    let lastMobile = isMobileViewport();
    resizeHandler = () => {
      if(ROOT !== container) return;
      const nowMobile = isMobileViewport();
      if(nowMobile !== lastMobile){ lastMobile = nowMobile; renderHabits(); }
    };
    window.addEventListener('resize', resizeHandler);

    App.api.get('/api/track').then(data=>{
      if(ROOT !== container) return; // вкладку успели переключить, пока шёл fetch
      DATA = normalize(data);
      backfillBenchmarkHabit();
      renderAll();
    });
  }

  window.TABS = window.TABS || {};
  window.TABS.track = renderTrack;
})();

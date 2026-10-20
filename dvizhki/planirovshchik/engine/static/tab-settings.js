/* Вкладка «Настройки»: форма редактирования режима дня, GET/POST /api/profile.
   Поля соответствуют profile.json (см. server.py _default_profile).

   IIFE - по тому же принципу, что tab-cycle.js/tab-track.js: несколько <script>
   на одной странице делят общий скоуп, без обёртки любое новое имя здесь рискует
   столкнуться с top-level именами tab-week.js (там свои render/save/wire на
   верхнем уровне скрипта без IIFE). Наружу торчит только window.TABS.settings.
   Стили - свой <style id="stg-style"> с префиксом stg-, поверх существующих
   .settings-wrap правил в app.css (их не трогаем - за app.css отвечает другой
   исполнитель параллельно). */
(function(){
  const {mins} = App.utils;

  const DAY_LABELS = [['mon','Пн'],['tue','Вт'],['wed','Ср'],['thu','Чт'],['fri','Пт'],['sat','Сб'],['sun','Вс']];

  function daysCheckboxes(name, selected){
    return DAY_LABELS.map(([code,label])=>
      `<label><input type="checkbox" name="${name}" value="${code}" ${selected.includes(code)?'checked':''}>${label}</label>`
    ).join('');
  }

  function escapeHtml(s){
    return String(s==null?'':s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }

  const TRAINING_DEFAULTS = {days:[], start:'', dur:0};

  function normalize(p){
    const src = (p && typeof p==='object') ? p : {};
    const training = Object.assign({}, TRAINING_DEFAULTS, src.training || {});
    training.days = Array.isArray(training.days) ? training.days : [];
    return {
      wake: src.wake || '', sleep: src.sleep || '',
      workStart: src.workStart || '', workEnd: src.workEnd || '',
      peakFrom: src.peakFrom || '', peakTo: src.peakTo || '',
      training,
      windDown: src.windDown || '',
      protectedDays: Array.isArray(src.protectedDays) ? src.protectedDays : [],
      capacityPercent: typeof src.capacityPercent === 'number' ? src.capacityPercent : null,
      /* Ритм дня. У профиля, созданного до этой функции, ключей нет вовсе -
         подставляем методологические значения (блок 90, перерыв 15, обед 13:00
         на час), а не нули: нуль в deepBlockMin сервер и так отклонит, а нулевой
         блок в сетке означал бы «разметки нет» без единого объяснения. */
      deepBlockMin: typeof src.deepBlockMin === 'number' ? src.deepBlockMin : 90,
      breakMin: typeof src.breakMin === 'number' ? src.breakMin : 15,
      lunchStart: src.lunchStart || '12:00',
      lunchDur: typeof src.lunchDur === 'number' ? src.lunchDur : 60,
      dinnerStart: src.dinnerStart || '19:00',
      dinnerDur: typeof src.dinnerDur === 'number' ? src.dinnerDur : 30,
      rhythmOn: src.rhythmOn !== false,
    };
  }

  let PROFILE = null;          // текущее состояние формы - источник для save()
  let loaded = false;          // GET ещё не пришёл - не даём автосейву переписать реальный файл пустотой
  let saveTimer = null;
  let unsavedPending = false;  // есть правки, ещё не долетевшие до сервера (в дебаунсе или заблокированы валидацией)
  let beforeUnloadBound = false;

  function renderSettings(container){
    injectStyle();
    container.innerHTML = `
      <div class="settings-wrap">
        <h2>Режим дня</h2>
        <p class="settings-intro">Отсюда планировщик берёт фазы суток и норму ёмкости дня. Поправь под свой реальный ритм - недельная сетка тут же пересчитает предупреждения о перегрузе. Сохраняется автоматически при каждой правке, отдельно жать «Сохранить» не обязательно.</p>

        <div class="stg-errors" id="settings-errors"></div>

        <form id="settings-form">
          <div class="field-row">
            <div class="field">
              <label>Подъём</label>
              <input type="time" name="wake">
              <p class="hint">Все фазы суток считаются от времени подъёма. Регулярность подъёма - более сильный рычаг, чем длительность сна.</p>
            </div>
            <div class="field">
              <label>Отбой</label>
              <input type="time" name="sleep">
              <p class="hint">Фиксированный отбой семь дней в неделю, без исключений на выходные.</p>
            </div>
          </div>

          <div class="field-row">
            <div class="field">
              <label>Начало работы</label>
              <input type="time" name="workStart">
              <p class="hint">От начала и конца работы считается доступная ёмкость дня для валидатора перегруза на вкладке «Неделя».</p>
            </div>
            <div class="field">
              <label>Конец работы</label>
              <input type="time" name="workEnd">
              <p class="hint">После этого времени день не считается рабочим.</p>
            </div>
          </div>

          <div class="field-row">
            <div class="field">
              <label>Пик от</label>
              <input type="time" name="peakFrom">
              <p class="hint">Пиковое окно - сюда тяжёлая когнитивка, съёмка, решения, «лягушка».</p>
            </div>
            <div class="field">
              <label>Пик до</label>
              <input type="time" name="peakTo">
              <p class="hint">После пика - рутина, встречи, админ, ответы, без новой тяжёлой когнитивки.</p>
            </div>
          </div>

          <fieldset>
            <legend>Тренировка</legend>
            <div class="field">
              <label>Дни</label>
              <div class="days-row" id="training-days"></div>
              <p class="hint">Неотменяемый блок. Отмена требует действия, а не бездействия.</p>
            </div>
            <div class="field-row">
              <div class="field">
                <label>Начало</label>
                <input type="time" name="trainingStart">
              </div>
              <div class="field">
                <label>Длительность, мин</label>
                <input type="number" name="trainingDur" min="0" max="600" step="5">
              </div>
            </div>
          </fieldset>

          <div class="field">
            <label>Wind-down</label>
            <input type="time" name="windDown">
            <p class="hint">Экраны и яркий свет приглушить за 1-2 часа до сна, тяжёлые разговоры - не после 17:00.</p>
          </div>

          <div class="field">
            <label>Защищённые дни</label>
            <div class="days-row" id="protected-days"></div>
            <p class="hint">В эти дни планировщик не ставит задач. По умолчанию воскресенье - ноль задач.</p>
          </div>

          <div class="field">
            <label>Ёмкость планирования, %</label>
            <input type="number" name="capacityPercent" min="5" max="100" step="5">
            <p class="hint">Методология: планировать 50-60% дня, остальное съест реактив. Выше нормы - недельная сетка подсвечивает день красным. Меньше 5% или пусто не сохраняются - иначе любой день становится красным.</p>
          </div>

          <fieldset>
            <legend>Ритм дня</legend>
            <p class="hint stg-lead">Отсюда недельная сетка размечает рабочее окно: блоки, обед и ужин. Видно, куда целиться задачей и где кончается один заход работы. Клик по свободному месту блока сразу ставит задачу на его окно фокуса, при перетаскивании задача прилипает к началу ближайшего блока (в пределах 12 минут от него), а точное время всегда можно вписать руками в карточке задачи.</p>
            <div class="field">
              <label class="stg-check"><input type="checkbox" name="rhythmOn"> Показывать разметку блоков в сетке</label>
              <p class="hint">Снимешь галочку - в сетке останутся только часовые линии, зоны суток (сон, wind-down, утро) при этом никуда не денутся.</p>
            </div>
            <div class="field-row">
              <div class="field">
                <label>Длина блока, мин</label>
                <input type="number" name="deepBlockMin" min="15" max="480" step="5">
                <p class="hint">Физика фокуса: 90 минут - это ультрадианный цикл, дальше концентрация падает сама. Заход «на 3 часа» сюда вписывать не надо: это два блока по 90, сетка их так и нарисует.</p>
              </div>
              <div class="field">
                <label>Перерыв ВНУТРИ блока, мин</label>
                <input type="number" name="breakMin" min="0" max="180" step="5">
                <p class="hint">Перерыв не добавляется к блоку, а входит в него: при блоке 90 и перерыве 10 чистого фокуса 80, а следующий блок всё равно стартует ровно через 90 минут. Так день не расползается. Эти минуты нужны без экрана.</p>
              </div>
            </div>
            <div class="field-row">
              <div class="field">
                <label>Обед с</label>
                <input type="time" name="lunchStart">
                <p class="hint">Провал бдительности приходит через 6-8 часов после подъёма - это циркадный дип. Обед логично ставить прямо перед ним: блоки, попавшие в дип, сетка помечает как механику, тяжёлое туда не идёт.</p>
              </div>
              <div class="field">
                <label>Обед, мин</label>
                <input type="number" name="lunchDur" min="0" max="240" step="5">
                <p class="hint">Ноль - обеда в разметке нет, блоки идут подряд.</p>
              </div>
            </div>
            <div class="field-row">
              <div class="field">
                <label>Ужин с</label>
                <input type="time" name="dinnerStart">
              </div>
              <div class="field">
                <label>Ужин, мин</label>
                <input type="number" name="dinnerDur" min="0" max="240" step="5">
                <p class="hint">Ноль - ужин в разметке не показывать.</p>
              </div>
            </div>
            <p class="hint">Блоки внутри пикового окна сетка помечает как глубокие, но не больше двух за день: столько тяжёлой работы реально помещается. Последний блок дня помечается как буфер - его держат пустым под то, что прилетит. Сколько всего часов класть в день, решает «Ёмкость планирования» выше.</p>
          </fieldset>

          <div class="save-bar">
            <button type="submit">Сохранить</button>
            <span class="save-note" id="settings-save-note">сохранено</span>
          </div>
        </form>
      </div>`;

    document.getElementById('training-days').innerHTML = daysCheckboxes('trainingDays', []);
    document.getElementById('protected-days').innerHTML = daysCheckboxes('protectedDays', []);

    bindBeforeUnload();

    App.api.get('/api/profile').then(p=>{
      const form = document.getElementById('settings-form');
      if(!form) return; // вкладку успели переключить, пока шёл fetch
      PROFILE = normalize(p);
      loaded = true;
      fillForm(PROFILE);
      renderValidation(validate(PROFILE));
    }).catch(err=>{
      const box = document.getElementById('settings-errors');
      if(box){
        box.classList.add('on');
        box.innerHTML = `Не удалось загрузить настройки: ${escapeHtml(err.message)}. Правки не сохраняются, пока страница в этом состоянии - перезайди на вкладку.`;
      }
    });

    const form = document.getElementById('settings-form');
    form.addEventListener('change', onFieldChange);
    form.addEventListener('submit', e=>{
      e.preventDefault();
      if(!loaded) return;
      const collected = collectForm();
      revertEmptyTimeFields(collected);
      PROFILE = collected;
      const result = validate(PROFILE);
      renderValidation(result);
      if(!hasErrors(result)) flushSave();
    });
  }

  function fillForm(p){
    const form = document.getElementById('settings-form');
    if(!form) return; // вкладку успели переключить, пока шёл fetch
    form.wake.value = p.wake || '';
    form.sleep.value = p.sleep || '';
    form.workStart.value = p.workStart || '';
    form.workEnd.value = p.workEnd || '';
    form.peakFrom.value = p.peakFrom || '';
    form.peakTo.value = p.peakTo || '';
    form.trainingStart.value = (p.training && p.training.start) || '';
    form.trainingDur.value = (p.training && p.training.dur) || '';
    form.windDown.value = p.windDown || '';
    form.capacityPercent.value = typeof p.capacityPercent === 'number' ? p.capacityPercent : '';
    form.deepBlockMin.value = p.deepBlockMin || '';
    // перерыв 0 - законное значение («блоки подряд»), поэтому не через ||
    form.breakMin.value = typeof p.breakMin === 'number' ? p.breakMin : '';
    form.lunchStart.value = p.lunchStart || '';
    form.lunchDur.value = typeof p.lunchDur === 'number' ? p.lunchDur : '';
    form.dinnerStart.value = p.dinnerStart || '';
    form.dinnerDur.value = typeof p.dinnerDur === 'number' ? p.dinnerDur : '';
    form.rhythmOn.checked = p.rhythmOn !== false;

    const trainingDays = (p.training && p.training.days) || [];
    document.getElementById('training-days').innerHTML = daysCheckboxes('trainingDays', trainingDays);
    document.getElementById('protected-days').innerHTML = daysCheckboxes('protectedDays', p.protectedDays || []);
  }

  function numOrNull(v){
    const n = parseInt(v, 10);
    return Number.isFinite(n) ? n : null;
  }
  /* сервер (server.py SCHEMAS.profile) валидирует диапазоны строго: deepBlockMin
     15..480, breakMin 0..180, training.dur 0..600 - значение вне диапазона роняет
     ВЕСЬ POST 400-й (документ пишется целиком). Раньше пустое/мусорное поле тихо
     превращалось в 0 через `|| 0`, а 0 вне диапазона deepBlockMin - автосейв бы
     на ровном месте начал молча отваливаться. Теперь: невалидное - откатываем
     на последнее сохранённое значение (fallback), out-of-range - подрезаем в
     границы, а не отбрасываем правку целиком. */
  function clampOr(n, lo, hi, fallback){
    if(n == null || !Number.isFinite(n)) return fallback;
    return Math.max(lo, Math.min(hi, n));
  }

  function collectForm(){
    const form = document.getElementById('settings-form');
    const checked = name => [...form.querySelectorAll(`input[name="${name}"]:checked`)].map(el=>el.value);
    const prevDeepBlock = PROFILE ? PROFILE.deepBlockMin : 90;
    const prevBreak = PROFILE ? PROFILE.breakMin : 15;
    const prevLunchDur = PROFILE ? PROFILE.lunchDur : 60;
    const prevDinnerDur = PROFILE ? PROFILE.dinnerDur : 30;
    const prevDur = (PROFILE && PROFILE.training) ? PROFILE.training.dur : 60;
    return {
      wake: form.wake.value,
      sleep: form.sleep.value,
      workStart: form.workStart.value,
      workEnd: form.workEnd.value,
      peakFrom: form.peakFrom.value,
      peakTo: form.peakTo.value,
      training: {
        days: checked('trainingDays'),
        start: form.trainingStart.value,
        dur: clampOr(numOrNull(form.trainingDur.value), 0, 600, prevDur),
      },
      windDown: form.windDown.value,
      protectedDays: checked('protectedDays'),
      capacityPercent: numOrNull(form.capacityPercent.value),
      deepBlockMin: clampOr(numOrNull(form.deepBlockMin.value), 15, 480, prevDeepBlock),
      breakMin: clampOr(numOrNull(form.breakMin.value), 0, 180, prevBreak),
      lunchStart: form.lunchStart.value,
      lunchDur: clampOr(numOrNull(form.lunchDur.value), 0, 240, prevLunchDur),
      dinnerStart: form.dinnerStart.value,
      dinnerDur: clampOr(numOrNull(form.dinnerDur.value), 0, 240, prevDinnerDur),
      rhythmOn: !!form.rhythmOn.checked,
    };
  }

  /* Поля времени (wake/sleep/workStart/workEnd/peakFrom/peakTo/windDown,
     training.start) сервер валидирует форматом ЧЧ:ММ и требует непустыми, если
     ключ вообще присутствует в документе - а POST всегда шлёт документ целиком
     (check_no_dropped_keys), значит очистить такое поле до пустоты и сохранить
     нельзя вообще никогда. `<input type=time>` даёт очистить себя случайным
     кликом на крестик - откатываем на последнее сохранённое значение и коротко
     подсвечиваем поле, тем же приёмом, что и мусор в цели на вкладке «Цикл»,
     вместо того чтобы блокировать сохранение ВСЕЙ формы баннером из-за одного
     стёртого поля. */
  const TIME_FIELDS = ['wake','sleep','workStart','workEnd','peakFrom','peakTo','windDown','lunchStart','dinnerStart'];
  function revertEmptyTimeFields(p){
    const form = document.getElementById('settings-form');
    if(!form || !PROFILE) return;
    TIME_FIELDS.forEach(name=>{
      if(p[name] === '' && PROFILE[name]){
        p[name] = PROFILE[name];
        const el = form.querySelector(`[name="${name}"]`);
        if(el){ el.value = PROFILE[name]; flashFieldRejected(el); }
      }
    });
    if(p.training.start === '' && PROFILE.training && PROFILE.training.start){
      p.training.start = PROFILE.training.start;
      if(form.trainingStart){ form.trainingStart.value = PROFILE.training.start; flashFieldRejected(form.trainingStart); }
    }
  }
  function flashFieldRejected(el){
    el.classList.add('stg-field-rejected');
    setTimeout(()=>el.classList.remove('stg-field-rejected'), 900);
  }

  /* ---------- валидация противоречивого профиля ----------
     Раньше форма принимала конец работы раньше начала и подъём «позже» отбоя,
     а capacityPercent=0 проходила молча - из-за этого валидатор ёмкости на
     вкладке «Неделя» тихо отключался (avail<=0 -> return null, никакого
     предупреждения) и норма 0% красила в перегруз любой день. Теперь профиль
     с такими противоречиями просто не сохраняется - показываем причину и не
     даём POST улететь на сервер. */
  function validate(p){
    const errors = [];
    const bad = {};

    const ws = p.workStart ? mins(p.workStart) : null;
    const we = p.workEnd ? mins(p.workEnd) : null;
    if(ws != null && we != null && we <= ws){
      errors.push('Конец работы должен быть позже начала.');
      bad.workStart = bad.workEnd = true;
    }

    const pf = p.peakFrom ? mins(p.peakFrom) : null;
    const pt = p.peakTo ? mins(p.peakTo) : null;
    if(pf != null && pt != null && pt <= pf){
      errors.push('Пик должен заканчиваться позже, чем начинается.');
      bad.peakFrom = bad.peakTo = true;
    }

    const wa = p.wake ? mins(p.wake) : null;
    const sl = p.sleep ? mins(p.sleep) : null;
    if(wa != null && sl != null){
      if(wa === sl){
        errors.push('Подъём и отбой не могут совпадать.');
        bad.wake = bad.sleep = true;
      } else {
        /* отбой у большинства - после полуночи относительно подъёма (сон
           «наматывает круг»), поэтому сырое сравнение чисел бессмысленно:
           default wake=08:00, sleep=00:00 численно «раньше» подъёма, но это
           нормальный 16-часовой день. Настоящее противоречие - слишком мало
           часов остаётся на сон, если идти от подъёма по кругу до отбоя. */
        const awakeSpan = ((sl - wa) + 1440) % 1440;
        const impliedSleep = 1440 - awakeSpan;
        if(impliedSleep < 180){
          errors.push('Между отбоем и следующим подъёмом должно быть не меньше 3 часов - иначе подъём позже отбоя не по смыслу.');
          bad.wake = bad.sleep = true;
        }
      }
    }

    /* Обед вне рабочего окна разметка просто не нарисует, и владелец будет
       гадать, почему поле есть, а полосы нет. Ловим сразу и говорим причину.
       При нулевой длительности обеда время не важно - обеда в разметке нет. */
    const ln = p.lunchStart ? mins(p.lunchStart) : null;
    if(p.lunchDur > 0 && ln != null && ws != null && we != null && we > ws && (ln < ws || ln >= we)){
      errors.push('Начало обеда должно попадать в рабочее окно ' + p.workStart + '-' + p.workEnd + ' - иначе разметка обед не покажет.');
      bad.lunchStart = true;
    }
    const dn = p.dinnerStart ? mins(p.dinnerStart) : null;
    if(p.dinnerDur > 0 && dn != null && ws != null && we != null && we > ws && (dn < ws || dn >= we)){
      errors.push('Начало ужина должно попадать в рабочее окно ' + p.workStart + '-' + p.workEnd + ' - иначе разметка ужин не покажет.');
      bad.dinnerStart = true;
    }
    if(p.lunchDur > 0 && p.dinnerDur > 0 && ln != null && dn != null &&
       ln < dn + p.dinnerDur && dn < ln + p.lunchDur){
      errors.push('Обед и ужин наезжают друг на друга - разведи их по времени.');
      bad.lunchStart = bad.dinnerStart = true;
    }

    /* нижняя граница 5, не 0/1 - совпадает с server.py SCHEMAS.profile
       (v_int(5, 100)): меньшее значение сервер и так отклонит 400-й, честнее
       сказать причину сразу, чем сначала «сохранено», потом баннер ошибки */
    if(p.capacityPercent == null || p.capacityPercent < 5){
      errors.push('Ёмкость планирования не может быть меньше 5% или пустой - иначе любой день в недельной сетке становится красным.');
      bad.capacityPercent = true;
    }

    return {errors, bad};
  }
  function hasErrors(result){ return result.errors.length > 0; }

  function renderValidation(result){
    const box = document.getElementById('settings-errors');
    const form = document.getElementById('settings-form');
    if(!box || !form) return;
    ['workStart','workEnd','peakFrom','peakTo','wake','sleep','windDown','capacityPercent','lunchStart','dinnerStart'].forEach(name=>{
      const el = form.querySelector(`[name="${name}"]`);
      if(el) el.classList.toggle('stg-invalid', !!(result.bad && result.bad[name]));
    });
    const btn = form.querySelector('.save-bar button[type="submit"]');
    if(hasErrors(result)){
      box.classList.add('on');
      box.innerHTML = '<strong>Не сохранено, есть противоречия:</strong><ul>' +
        result.errors.map(e=>`<li>${escapeHtml(e)}</li>`).join('') + '</ul>';
      if(btn) btn.disabled = true;
    } else {
      box.classList.remove('on');
      box.innerHTML = '';
      if(btn) btn.disabled = false;
    }
  }

  /* ---------- автосохранение + предупреждение о несохранённом (F3) ----------
     Раньше сохранение шло ТОЛЬКО по клику «Сохранить»: ушёл на другую вкладку -
     введённое тихо возвращалось к прежнему при следующем открытии, без единого
     предупреждения. Теперь как в остальных вкладках - 'change' на любом поле
     (fires на blur, то есть уже ПОСЛЕ Tab на соседнее поле) обновляет профиль
     и планирует сохранение; если профиль противоречив - не сохраняем и не
     тихо, а с видимой причиной в баннере. beforeunload прикрывает случай
     реального закрытия/обновления страницы внутри окна дебаунса. */
  function onFieldChange(){
    if(!loaded) return; // GET ещё не пришёл - не даём стереть реальный профиль пустой формой
    const collected = collectForm();
    revertEmptyTimeFields(collected);
    PROFILE = collected;
    unsavedPending = true;
    const result = validate(PROFILE);
    renderValidation(result);
    if(hasErrors(result)){
      clearTimeout(saveTimer);
      return; // противоречивое не сохраняем вообще, ждём когда поправят
    }
    scheduleSave();
  }

  function scheduleSave(){
    clearTimeout(saveTimer);
    saveTimer = setTimeout(doSave, 400);
  }
  async function flushSave(){
    clearTimeout(saveTimer);
    await doSave();
  }
  async function doSave(){
    if(!loaded || !PROFILE) return;
    try{
      await App.api.post('/api/profile', PROFILE);
      unsavedPending = false;
      App.flashSaved();
      const note = document.getElementById('settings-save-note');
      if(note){ note.classList.add('on'); setTimeout(()=>note.classList.remove('on'), 1200); }
    }catch(err){
      const box = document.getElementById('settings-errors');
      if(box){
        box.classList.add('on');
        box.innerHTML += `<div class="stg-save-fail">Не удалось сохранить: ${escapeHtml(err.message)}. Правки остаются только в этой вкладке - обнови страницу позже и повтори.</div>`;
      }
    }
  }

  function bindBeforeUnload(){
    if(beforeUnloadBound) return;
    beforeUnloadBound = true;
    window.addEventListener('beforeunload', e=>{
      if(unsavedPending){
        e.preventDefault();
        e.returnValue = '';
      }
    });
  }

  /* ---------- стили ---------- */
  function injectStyle(){
    if(document.getElementById('stg-style')) return;
    const st = document.createElement('style');
    st.id = 'stg-style';
    st.textContent = `
.stg-lead{margin-top:0}
.settings-wrap .stg-check{display:flex;align-items:center;gap:8px;cursor:pointer;font-weight:500}
.settings-wrap .stg-check input{width:16px;height:16px;margin:0;flex:0 0 auto;accent-color:var(--blue);cursor:pointer}
.stg-badge{display:inline-block;font-size:9.5px;font-weight:600;color:var(--txt-dim);background:var(--hover);border:1px solid var(--bd);border-radius:9px;padding:1px 7px;margin-left:6px;letter-spacing:.2px;text-transform:none;vertical-align:1px}
.stg-errors{display:none;background:#fdecea;border:1px solid #f6c6c1;color:#8a1f11;border-radius:7px;padding:11px 14px;font-size:13px;line-height:1.5;margin:0 0 18px}
.stg-errors.on{display:block}
.stg-errors ul{margin:4px 0 0;padding-left:18px}
.stg-errors li{margin:2px 0}
.stg-save-fail{margin-top:6px;font-weight:600}
.settings-wrap .stg-invalid{border-color:var(--red) !important;background:#fdecea !important}
.settings-wrap .stg-field-rejected{outline:2px solid var(--red) !important;background:#fdecea !important;border-radius:4px;transition:background-color .6s ease,outline-color .6s ease}
.settings-wrap .save-bar button:disabled{opacity:.45;cursor:not-allowed}
`;
    document.head.appendChild(st);
  }

  window.TABS = window.TABS || {};
  window.TABS.settings = renderSettings;
})();

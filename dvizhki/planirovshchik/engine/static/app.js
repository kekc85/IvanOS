/* Оболочка приложения: переключение вкладок, общий стейт, загрузка/сохранение
   через API, утилиты дат. Модули вкладок (tab-week.js, tab-settings.js, ...)
   читают App.* и регистрируют себя в window.TABS[<имя>] = render(container).
   Если модуль вкладки ещё не подключён - показывается заглушка, не падаем. */
(function(){
  const pad = n => String(n).padStart(2, '0');
  const iso = d => `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}`;
  const parseISO = s => { const [y,m,d]=s.split('-').map(Number); return new Date(y,m-1,d); };
  const mins = t => { const [h,m]=t.split(':').map(Number); return h*60+m; };
  const hhmm = m => `${pad(Math.floor(m/60))}:${pad(m%60)}`;
  const startOfWeek = d => { const x=new Date(d); const wd=(x.getDay()+6)%7; x.setDate(x.getDate()-wd); x.setHours(0,0,0,0); return x; };

  /* Версии документов. Сервер требует rev при каждой записи и отвечает 409,
     если документ успели изменить (вторая вкладка или вечерний ритуал).
     Оболочка держит последнюю известную rev по каждому пути, чтобы модули
     вкладок про это не думали. */
  const REV = Object.create(null);

  async function apiGet(path){
    const res = await fetch(path);
    if(!res.ok) throw new Error(`GET ${path} -> ${res.status}`);
    const out = await res.json();
    const rev = (out && out.rev) || res.headers.get('ETag');
    if(rev) REV[path] = String(rev).replace(/"/g, '');
    return out;
  }

  /* Чтение БЕЗ обновления REV. Нужно ровно в одном месте - в разборе 409, где
     документ читаем ради показа конфликта, а данные вкладки при этом остаются
     старыми: принять свежую версию тут значило бы разорвать пару «данные+rev». */
  async function readDoc(path){
    const res = await fetch(path);
    if(!res.ok) return null;
    const doc = await res.json();
    const rev = (doc && doc.rev) || String(res.headers.get('ETag') || '').replace(/"/g, '');
    return {doc, rev: rev || null};
  }

  async function apiPost(path, data){
    const body = (data && typeof data === 'object' && !Array.isArray(data))
      ? Object.assign({}, data, REV[path] ? {rev: REV[path]} : {})
      : data;
    const res = await fetch(path, {
      method: 'POST',
      headers: Object.assign(
        {'Content-Type': 'application/json'},
        REV[path] ? {'If-Match': REV[path]} : {}
      ),
      body: JSON.stringify(body),
    });

    if(res.status === 409){
      /* Документ изменили под нами. Свежую версию сервера класть в REV НЕЛЬЗЯ:
         данные вкладки остались старыми, и СЛЕДУЮЩАЯ запись прошла бы If-Match
         законно и затёрла чужую правку - молчаливое затирание с отсрочкой.
         Так однажды две записи подряд вернули трекер к прежней версии
         и унесли отметки за предыдущий день.

         Правило: rev меняется ТОЛЬКО вместе с телом, то есть в apiGet. Здесь мы
         перечитываем актуальный документ с сервера и отдаём его вызывающему
         (err.current), а REV оставляем прежним - повторная запись со старыми
         данными получит честный 409, а не тихую победу. Дальше вкладка делает
         то же, что tab-plan.js и command.js: свежее чтение и повтор (App.api.get
         обновит и данные, и версию разом). */
      let fresh = null;
      try { fresh = await res.json(); } catch(e) { /* тело может быть пустым */ }
      let current = fresh && fresh.current;
      let currentRev = (fresh && fresh.rev) || null;
      try {
        const live = await readDoc(path);
        if(live){ current = live.doc; currentRev = live.rev; }
      } catch(e) { /* сервер не ответил - остаёмся с телом ответа 409 */ }
      notifyConflict(path);
      const err = new Error(`POST ${path} -> 409 conflict`);
      err.conflict = true; err.current = current; err.rev = currentRev;
      throw err;
    }
    if(!res.ok){
      let detail = '';
      try { const j = await res.json(); detail = j.error || ''; } catch(e) {}
      notifyError(`Не сохранилось: ${detail || res.status}`);
      throw new Error(`POST ${path} -> ${res.status} ${detail}`);
    }

    const out = await res.json();
    if(out && out.rev) REV[path] = out.rev;
    if(data && typeof data === 'object' && out && out.rev) data.rev = out.rev;
    return out;
  }

  /* Молчаливая потеря правки - главный дефект прошлой версии: галочка
     «сохранено» не загоралась, но и ошибки владелец не видел. */
  function notifyError(text){
    let el = document.getElementById('app-error');
    if(!el){
      el = document.createElement('div');
      el.id = 'app-error';
      el.className = 'app-error';
      // стили инлайном: app.css в этот момент правит другой исполнитель
      el.style.cssText = 'position:fixed;left:50%;bottom:24px;transform:translateX(-50%);' +
        'background:#ea4335;color:#fff;padding:12px 18px;border-radius:8px;font-size:13px;' +
        'line-height:1.4;max-width:min(560px,92vw);box-shadow:0 4px 16px rgba(0,0,0,.25);' +
        'z-index:9999;opacity:0;transition:opacity .2s;pointer-events:none';
      document.body.appendChild(el);
      const st = document.createElement('style');
      st.textContent = '#app-error.on{opacity:1 !important;pointer-events:auto !important}';
      document.head.appendChild(st);
    }
    el.textContent = text;
    el.classList.add('on');
    clearTimeout(notifyError._t);
    notifyError._t = setTimeout(()=>el.classList.remove('on'), 6000);
  }

  function notifyConflict(path){
    notifyError('Данные изменились в другом окне или вечерним ритуалом. Обновите страницу, иначе правка потеряется');
  }

  let flashTimer = null;
  function flashSaved(){
    const el = document.getElementById('saved');
    if(!el) return;
    el.classList.add('on');
    clearTimeout(flashTimer);
    flashTimer = setTimeout(()=>el.classList.remove('on'), 1200);
  }

  window.App = {
    utils: {pad, iso, parseISO, mins, hhmm, startOfWeek},
    api: {get: apiGet, post: apiPost},
    flashSaved,
    notify: notifyError,
    rev: REV,
  };

  // точки монтирования вкладок - модули дописывают сюда свои ключи:
  // window.TABS.week / .cycle / .track / .settings = render(container)
  window.TABS = window.TABS || {};

  const DEFAULT_TAB = 'week';
  let activeTab = DEFAULT_TAB;

  function renderStub(container){
    container.innerHTML = '<div class="stub">скоро</div>';
  }

  /* Вкладка адресуется хешем: localhost:8791/#cycle открывает «Цикл» сразу.
     Без этого на любую вкладку кроме «Недели» нельзя дать ссылку и нельзя
     открыть её человеку - приходится просить его кликнуть самому. */
  function tabFromHash(){
    const name = String(location.hash || '').replace(/^#/, '').trim();
    return document.querySelector(`.tabbar button[data-tab="${name}"]`) ? name : null;
  }

  function showTab(name, fromHash){
    activeTab = name;
    if(!fromHash && String(location.hash || '').replace(/^#/, '') !== name){
      try { history.replaceState(null, '', '#' + name); } catch(e) { location.hash = name; }
    }
    document.querySelectorAll('.tabbar button').forEach(b=>{
      b.classList.toggle('active', b.dataset.tab === name);
    });
    const root = document.getElementById('tab-root');
    root.innerHTML = '';
    const fn = window.TABS[name];
    if(typeof fn === 'function'){
      fn(root);
    } else {
      renderStub(root);
    }
  }

  function init(){
    document.querySelectorAll('.tabbar button').forEach(b=>{
      b.addEventListener('click', ()=> showTab(b.dataset.tab));
    });
    window.addEventListener('hashchange', ()=>{
      const name = tabFromHash();
      if(name && name !== activeTab) showTab(name, true);
    });
    showTab(tabFromHash() || activeTab, true);
  }

  if(document.readyState === 'loading'){
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();

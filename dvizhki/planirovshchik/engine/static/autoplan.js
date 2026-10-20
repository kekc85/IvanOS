/* ============================================================================
   autoplan.js - автораскладка бэклога по свободным слотам недели.

   Это ЧИСТЫЙ АЛГОРИТМ. Ноль DOM, ноль fetch, ноль записи в данные, ноль
   зависимостей. Наружу торчит ровно одна функция:

       window.AutoPlan.propose(ctx) -> {placements, skipped, notes}

   Кто зовёт: tab-week.js (кнопка «Разложить»). Он собирает ctx, показывает
   превью и сам решает, применять или нет. Мы ничего не сохраняем - решение
   владельца остаётся за владельцем.

   Козырь против Motion: слот выбирается не «первый свободный», а по
   физиологии дня. Тяжёлое - в пиковое окно, механика - в циркадный провал,
   между задачами перерыв 10 минут, за ёмкость дня не вылезаем. Если разметки
   ритма нет (тумблер выключен, пика в ctx нет) - раскладываем честно по
   ёмкости и говорим об этом вслух, а не притворяемся умными.

   Контракт входа:
     ctx = {
       dates: ["2026-08-28", ...],        // дни под раскладку, защищённых тут нет
       events: [...],                     // существующие события недели
       backlog: [{id, title, est, track, priority?, due?, energy?, when?}],
       profile: {...},
       zones: { "2026-08-28": {
           work: [540, 1260],             // рабочее окно, минуты от полуночи
           blockedRanges: [[a,b], ...],   // сон, еда, тренировка, занятые отрезки
           peak: [540, 780] | null,
           dip:  [780, 900] | null,
           capacityMin: 576
       }},
       big3: { "2026-08-28": ["eventId1", "eventId2", ...] }   // необязательно
     }

   Необязательные поля, оба обратно совместимы (нет поля - поведение как раньше):
     - backlog[i].when - свободнотекстовая пометка пользователя («10.09», «~10.09»,
       «10.09.2026», «след. неделя»). Дата за горизонтом ctx.dates или упоминание
       «след» - задача вообще не трогается, уходит в skipped с честной причиной.
     - big3 - id главных дел дня (из ctx.events), по датам. Между соседними
       главными делами одного дня раскладка не лезет, если есть куда поставить
       иначе; если весь день кроме этой щели занят - лезет, честно объяснив reason.

   Пересечение с уже стоящими событиями (ctx.events, кроме kind:"launch") -
   ЖЁСТКИЙ запрет размещения внутри самого autoplan.js, независимо от того,
   включил ли их вызывающий код в zones[date].blockedRanges: чистая функция не
   доверяет чужому покрытию, считает busy-время сама. Поле kind у события может
   отсутствовать вовсе - это не повод его игнорировать, блокируем всё кроме
   буквального kind:"launch".

   Контракт выхода:
     { placements: [{backlogId, date, start:"HH:MM", dur, reason}],
       skipped:    [{backlogId, why}],
       notes:      ["..."] }

   Детерминизм: одинаковый ctx даёт одинаковый ответ. Никакого Math.random и
   никакого обращения к текущему времени - точка отсчёта дедлайнов это первый
   день из ctx.dates, а не «сегодня» машины.

   Самотесты в конце файла. Запускаются ТОЛЬКО если в адресе есть
   `autoplan-test` (например index.html?autoplan-test). В обычной работе
   молчат и ничего не стоят.
   ========================================================================= */

(function(){
'use strict';

/* ---------- константы раскладки ---------- */
var MIN_SLOT = 15;      // отрезок короче этого бесполезен: пока сядешь, он кончится
var GAP      = 10;      // перерыв между соседними задачами прогона
var DAY_END  = 24*60;

/* ---------- мелкая арифметика ---------- */
function num(v){
  if(v === null || v === undefined || v === '' || typeof v === 'boolean') return null;
  if(typeof v === 'object') return null;
  var n = +v;
  return isFinite(n) ? n : null;
}
function pad2(n){ n = Math.floor(n); return (n < 10 ? '0' : '') + n; }
function hhmm(m){
  m = Math.max(0, Math.round(m));
  return pad2(Math.floor(m/60) % 24) + ':' + pad2(m % 60);
}
function isDateStr(s){ return typeof s === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(s); }
function tmin(s){
  var m = /^(\d{1,2}):(\d{2})$/.exec(String(s === null || s === undefined ? '' : s));
  return m ? (+m[1])*60 + (+m[2]) : null;
}
/* разница в днях между двумя ISO-датами, без часовых поясов и без «сейчас» */
function dayDiff(a, b){
  var ta = Date.UTC(+a.slice(0,4), +a.slice(5,7)-1, +a.slice(8,10));
  var tb = Date.UTC(+b.slice(0,4), +b.slice(5,7)-1, +b.slice(8,10));
  return Math.round((ta - tb) / 86400000);
}
var RU_WEEKDAYS = ['воскресенье', 'понедельник', 'вторник', 'среда', 'четверг', 'пятница', 'суббота'];
function weekdayOf(dateStr){
  var t = Date.UTC(+dateStr.slice(0,4), +dateStr.slice(5,7)-1, +dateStr.slice(8,10));
  return RU_WEEKDAYS[new Date(t).getUTCDay()];
}
function cap1(s){ return s.charAt(0).toUpperCase() + s.slice(1); }
function win2(v){
  if(!v) return null;
  var a = null, b = null;
  if(Array.isArray(v)){ a = num(v[0]); b = num(v[1]); }
  else if(typeof v === 'object'){ a = num(v.from); b = num(v.to); }   // терпим {from,to}
  if(a === null || b === null) return null;
  if(b <= a) return null;
  return [Math.max(0, a), Math.min(DAY_END, b)];
}
/* отрезки: чистим мусор, сортируем, склеиваем пересечения */
function normRanges(list){
  var raw = [];
  (Array.isArray(list) ? list : []).forEach(function(r){
    var w = win2(r);
    if(w) raw.push(w);
  });
  raw.sort(function(x, y){ return (x[0] - y[0]) || (x[1] - y[1]); });
  var out = [];
  raw.forEach(function(r){
    var last = out[out.length-1];
    if(last && r[0] <= last[1]) last[1] = Math.max(last[1], r[1]);
    else out.push([r[0], r[1]]);
  });
  return out;
}
/* свободные куски окна win после вычитания busy; огрызки короче MIN_SLOT выкидываем */
function freeSegments(win, busy){
  var segs = [], t = win[0];
  normRanges(busy).forEach(function(r){
    if(r[1] <= win[0] || r[0] >= win[1]) return;
    var a = Math.max(win[0], r[0]), b = Math.min(win[1], r[1]);
    if(a > t) segs.push([t, a]);
    t = Math.max(t, b);
  });
  if(t < win[1]) segs.push([t, win[1]]);
  return segs.filter(function(s){ return s[1] - s[0] >= MIN_SLOT; });
}

/* ---------- разбор задачи бэклога ---------- */
function prioOf(t){
  var n = num(t.priority);
  return n === null ? null : Math.max(0, Math.min(9, Math.round(n)));
}
function dueOf(t){
  return isDateStr(t.due) ? t.due : null;
}
function estOf(t){
  var n = num(t.est);
  if(n === null) n = num(t.dur);            // подстраховка: пришло событие, а не запись бэклога
  if(n === null || n <= 0) return null;
  return Math.round(n);
}
/* Класс энергии. Явное поле energy всегда сильнее вывода по цифрам:
   владелец руками сказал «это механика» - спорить не с чем. */
function energyOf(t, dur){
  var e = typeof t.energy === 'string' ? t.energy.toLowerCase().trim() : '';
  if(e === 'deep' || e === 'mid' || e === 'low') return e;
  var p = prioOf(t);
  if(dur >= 90 || (p !== null && p <= 1)) return 'deep';
  if(dur <= 30) return 'low';
  return 'mid';
}
/* Очередь: чем меньше score, тем раньше ставим.
   Вес приоритета 0-9 (0 высший) плюс близость дедлайна. Просроченный или
   завтрашний срок вытягивает задачу вперёд даже при среднем приоритете. */
function scoreOf(t, refDate){
  var p = prioOf(t), d = dueOf(t);
  var pw = (p === null) ? 5 : p;
  var dw;
  if(d === null) dw = 2.5;                               // срока нет - вперёд не лезет
  else {
    var left = dayDiff(d, refDate);
    dw = left < 0 ? -4 : (-2 + Math.min(4, left * 0.5)); // просрочен -4, дальний +2
  }
  return pw + dw;
}

/* Пометка when: свободный текст владельца, читаем ДО раскладки, спорить с ней
   не должность автомата. Понимаем «10.09», «~10.09», «10.09.2026» и «след...». */
function parseWhenDate(s){
  var m = /(\d{1,2})\.(\d{1,2})(?:\.(\d{4}))?/.exec(s);
  if(!m) return null;
  var day = +m[1], month = +m[2];
  if(day < 1 || day > 31 || month < 1 || month > 12) return null;
  return {day: day, month: month, year: m[3] ? +m[3] : null, text: pad2(day) + '.' + pad2(month)};
}
/* horizon - последний день ctx.dates (после сортировки). null, если решить нечем -
   тогда дата в when не с чем сравнивать, и мы её не трогаем (как раньше). */
function whenDecision(when, horizon){
  if(typeof when !== 'string') return null;
  var s = when.trim();
  if(!s) return null;
  if(s.toLowerCase().indexOf('след') >= 0) return 'помечено на следующую неделю';
  var pd = parseWhenDate(s);
  if(pd && horizon){
    var year = pd.year || +horizon.slice(0, 4);
    var iso = year + '-' + pad2(pd.month) + '-' + pad2(pd.day);
    if(isDateStr(iso) && dayDiff(iso, horizon) > 0) return 'отложено тобой до ' + pd.text;
  }
  return null;                         // пусто или непонятно - не наше дело, раскладываем как раньше
}

/* Щели между соседними главными делами дня (big3). ids приходит по конкретной
   дате из ctx.big3[date]; событий меньше двух с валидным временем - щелей нет,
   протекать нечему. */
function computeBig3Gaps(date, events, ids){
  if(!Array.isArray(ids) || ids.length < 2) return [];
  var idSet = {};
  ids.forEach(function(id){ if(id !== undefined && id !== null) idSet[id] = true; });
  var spans = [];
  (Array.isArray(events) ? events : []).forEach(function(e){
    if(!e || e.date !== date || !idSet[e.id]) return;
    var s = tmin(e.start), dur = num(e.dur);
    if(s === null || dur === null || dur <= 0) return;
    spans.push([s, s + dur]);
  });
  if(spans.length < 2) return [];
  spans.sort(function(a, b){ return a[0] - b[0]; });
  var gaps = [];
  for(var i = 1; i < spans.length; i++){
    var a = spans[i-1][1], b = spans[i][0];
    if(b > a) gaps.push([a, b]);
  }
  return gaps;
}

/* ---------- состояние дня на время прогона ---------- */
function buildDay(date, zone, events, big3Ids){
  var work = win2(zone && zone.work);
  var d = {
    date: date,
    ok: !!work,
    work: work || [0, 0],
    blocked: normRanges(zone && zone.blockedRanges),
    peak: win2(zone && zone.peak),
    dip:  win2(zone && zone.dip),
    cap: Infinity,
    used: 0,
    big3Gaps: computeBig3Gaps(date, events, big3Ids),
    placed: []
  };
  var cap = num(zone && zone.capacityMin);
  if(cap !== null && cap > 0) d.cap = Math.round(cap);
  /* ёмкость съедают уже стоящие события дня; запуски (kind=launch) не наши минуты.
     То же самое время дня заодно уходит в ЖЁСТКИЙ запрет размещения (d.blocked) -
     пересечение с уже стоящим событием это стена, не намёк на тесноту. Не зависим
     от того, включил ли вызывающий код события в zones.blockedRanges сам: своя
     проверка, свой busy-список. Условие фильтра то же, что и у ёмкости, поле kind
     может отсутствовать вовсе - это не повод пропустить событие. */
  var eventBusy = [];
  (Array.isArray(events) ? events : []).forEach(function(e){
    if(!e || e.date !== date || e.kind === 'launch') return;
    var s = tmin(e.start), dur = num(e.dur);
    if(s === null || dur === null || dur <= 0) return;
    var capped = Math.min(Math.round(dur), Math.max(0, DAY_END - s));
    d.used += capped;
    eventBusy.push([s, s + capped]);
  });
  if(eventBusy.length) d.blocked = normRanges(d.blocked.concat(eventBusy));
  return d;
}
function dayBusy(day){
  var busy = day.blocked.slice();
  // свои размещения расширяем на перерыв с обеих сторон - подряд не лепим
  day.placed.forEach(function(p){ busy.push([p.a - GAP, p.b + GAP]); });
  return busy;
}
function roomLeft(day, dur){
  return day.ok && (day.used + dur) <= day.cap;
}
/* Ищем самый ранний слот длиной dur. win - предпочтительное окно (пик, провал
   или null = всё рабочее), avoid - зоны, которые в этом заходе бережём. */
function findSlot(day, dur, win, avoid){
  if(!day.ok) return null;
  var w = day.work;
  if(win){
    w = [Math.max(day.work[0], win[0]), Math.min(day.work[1], win[1])];
    if(w[1] - w[0] < dur) return null;
  }
  if(w[1] - w[0] < dur) return null;
  var busy = dayBusy(day);
  if(avoid && avoid.length) busy = busy.concat(avoid);
  var segs = freeSegments(w, busy);
  for(var i = 0; i < segs.length; i++){
    if(segs[i][1] - segs[i][0] >= dur) return segs[i][0];
  }
  return null;
}
function commit(day, task, start, dur, reason){
  day.placed.push({a: start, b: start + dur});
  day.used += dur;
  return {backlogId: task.id, date: day.date, start: hhmm(start), dur: dur, reason: reason};
}

/* ---------- заходы раскладки по классам энергии ----------
   Каждый заход - функция дня, возвращает {start, reason} или null. Проходим
   заходы по очереди: сперва физиологически правильный, потом компромиссы.

   Главные дела дня (big3) - якоря, вокруг них тишина: во всех заходах кроме
   самого последнего щели между соседними big3 добавляются в avoid наравне с
   пиком/провалом. Последний заход (lastResort) щели не бережёт - если во всей
   неделе для задачи не нашлось места нигде, кроме щели между главными делами,
   честнее поставить её туда, чем не поставить вовсе. */
function avoidBig3(day, extra){
  var gaps = day.big3Gaps;
  if(!gaps || !gaps.length) return extra;
  return extra && extra.length ? gaps.concat(extra) : gaps.slice();
}
function passesFor(kind){
  var deepPeak = function(day, dur){
    if(!day.peak) return null;
    var s = findSlot(day, dur, day.peak, avoidBig3(day, null));
    return s === null ? null : {start: s, reason: 'в пик ' + hhmm(day.peak[0]) + '-' + hhmm(day.peak[1]) + ': тяжёлая задача, голова свежая'};
  };
  var deepOutsideDip = function(day, dur){
    var s = findSlot(day, dur, null, avoidBig3(day, day.dip ? [day.dip] : null));
    return s === null ? null : {start: s, reason: day.peak
      ? 'пик уже занят, поставил в свободное окно вне спада'
      : 'свободное окно вне спада: пик не размечен'};
  };
  var dipSlot = function(day, dur){
    if(!day.dip) return null;
    var s = findSlot(day, dur, day.dip, avoidBig3(day, null));
    return s === null ? null : {start: s, reason: 'в провал ' + hhmm(day.dip[0]) + '-' + hhmm(day.dip[1]) + ': механика, тяжёлое туда не ставлю'};
  };
  var savePeak = function(day, dur){
    var s = findSlot(day, dur, null, avoidBig3(day, day.peak ? [day.peak] : null));
    return s === null ? null : {start: s, reason: day.peak
      ? 'свободное окно рабочего дня, пик берегу под тяжёлое'
      : 'свободное окно рабочего дня'};
  };
  var anySlot = function(day, dur){
    var s = findSlot(day, dur, null, avoidBig3(day, null));
    return s === null ? null : {start: s, reason: 'свободное окно рабочего дня: удобные зоны уже разобраны'};
  };
  var lastResort = function(day, dur){
    if(!day.big3Gaps || !day.big3Gaps.length) return null;   // без щелей это тот же anySlot - незачем повторять
    var s = findSlot(day, dur, null, null);
    return s === null ? null : {start: s, reason: 'вставил между главными делами дня: в остальной неделе места не нашлось'};
  };
  if(kind === 'deep') return [deepPeak, deepOutsideDip, anySlot, lastResort];
  if(kind === 'low')  return [dipSlot, savePeak, anySlot, lastResort];
  return [savePeak, anySlot, lastResort];
}

/* ============================ ГЛАВНАЯ ФУНКЦИЯ ============================ */
function propose(ctx){
  var res = {placements: [], skipped: [], notes: []};
  ctx = (ctx && typeof ctx === 'object') ? ctx : {};

  var backlogAll = (Array.isArray(ctx.backlog) ? ctx.backlog : []).filter(function(t){
    return t && typeof t === 'object' && t.id !== undefined && t.id !== null;
  });

  /* дни: только валидные ISO, по возрастанию, без дублей */
  var seen = {}, dates = [];
  (Array.isArray(ctx.dates) ? ctx.dates : []).forEach(function(k){
    if(!isDateStr(k) || seen[k]) return;
    seen[k] = 1; dates.push(k);
  });
  dates.sort();
  var horizon = dates.length ? dates[dates.length - 1] : null;

  /* пометки when - воля владельца сильнее автоматики, отделяем ДО раскладки.
     Пусто/непонятно - не наше дело, идёт в обычный конвейер как раньше. */
  var backlog = [];
  backlogAll.forEach(function(t){
    var skip = whenDecision(t.when, horizon);
    if(skip) res.skipped.push({backlogId: t.id, why: skip});
    else backlog.push(t);
  });

  var zones = (ctx.zones && typeof ctx.zones === 'object') ? ctx.zones : {};
  var big3ByDay = (ctx.big3 && typeof ctx.big3 === 'object' && !Array.isArray(ctx.big3)) ? ctx.big3 : {};
  var days = [], dropped = [], overloaded = [], noCap = false;
  dates.forEach(function(k){
    var d = buildDay(k, zones[k], ctx.events, big3ByDay[k]);
    if(!d.ok){ dropped.push(k); return; }
    if(d.cap === Infinity){ noCap = true; days.push(d); return; }
    if(d.used > d.cap){ overloaded.push(d); return; }        // уже перегружен существующими событиями
    days.push(d);
  });

  overloaded.forEach(function(d){
    res.notes.push(cap1(weekdayOf(d.date)) + ' (' + d.date + ') уже перегружен (' + d.used + ' из ' + d.cap + ') - не добавляю');
  });

  if(!backlogAll.length){
    res.notes.push('В бэклоге нечего раскладывать: задач со статусом anytime нет');
    return res;
  }
  if(!backlog.length){
    // все задачи бэклога отложены пометками when - причины уже разложены по skipped выше
    res.notes.unshift('Разложил 0 из ' + backlogAll.length + ', отложено по твоим пометкам ' + res.skipped.length);
    return res;
  }
  if(!days.length){
    if(overloaded.length){
      res.notes.push('Неделя уже перегружена - разгрузи, прежде чем раскладывать');
    }else{
      res.notes.push(dropped.length
        ? 'Нет дней для раскладки: у переданных дней не размечено рабочее окно в настройках'
        : 'Нет дней для раскладки: все дни недели защищены или уже заняты целиком');
    }
    backlog.forEach(function(t){
      res.skipped.push({backlogId: t.id, why: 'не влезла: свободных дней в неделе не осталось'});
    });
    return res;
  }
  if(dropped.length){
    res.notes.push('Пропустил дни без рабочего окна: ' + dropped.join(', ') + ' - задай рабочее время в настройках');
  }
  if(noCap){
    res.notes.push('Ёмкость дня не задана, ограничиваю раскладку только рабочим окном');
  }

  var refDate = days[0].date;                       // точка отсчёта дедлайнов
  var hasPeak = days.some(function(d){ return !!d.peak; });
  var hasDip  = days.some(function(d){ return !!d.dip; });
  if(!hasPeak){
    res.notes.push('Пиковое окно недоступно - раскладываю по ёмкости, включи разметку ритма для умной раскладки');
  }else if(!hasDip){
    res.notes.push('Провал дня не размечен: механику ставлю в обычные свободные окна');
  }

  /* очередь: сначала всё, у чего есть сигнал (приоритет или срок), по score;
     остальное - хвостом в исходном порядке, как лежало в бэклоге */
  var queue = backlog.map(function(t, i){
    var p = prioOf(t), d = dueOf(t);
    return {t: t, idx: i, signal: (p !== null || d !== null), score: scoreOf(t, refDate)};
  });
  queue.sort(function(a, b){
    if(a.signal !== b.signal) return a.signal ? -1 : 1;
    if(a.signal && a.score !== b.score) return a.score - b.score;
    return a.idx - b.idx;
  });

  var lateCount = 0;
  queue.forEach(function(q){
    var t = q.t;
    var dur = estOf(t);
    if(dur === null){
      res.skipped.push({backlogId: t.id, why: 'нет оценки времени - поставь est, длительность я не выдумываю'});
      return;
    }
    var due = dueOf(t);
    var cand = days.filter(function(d){ return !due || d.date <= due; });
    if(!cand.length){
      lateCount++;
      res.skipped.push({backlogId: t.id, why: 'не успевает к сроку ' + due + ', разгрузи неделю'});
      return;
    }
    var kind = energyOf(t, dur);
    var passes = passesFor(kind);
    var done = null;
    for(var pi = 0; pi < passes.length && !done; pi++){
      for(var di = 0; di < cand.length && !done; di++){
        var day = cand[di];
        if(!roomLeft(day, dur)) continue;          // ёмкость выбрана, день закрыт
        var hit = passes[pi](day, dur);
        if(hit) done = commit(day, t, hit.start, dur, hit.reason);
      }
    }
    if(done){ res.placements.push(done); return; }
    if(due){
      lateCount++;
      res.skipped.push({backlogId: t.id, why: 'не успевает к сроку ' + due + ', разгрузи неделю'});
    }else{
      res.skipped.push({backlogId: t.id, why: 'не влезла: неделя заполнена, свободного окна под ' + dur + ' мин не осталось'});
    }
  });

  /* порядок выдачи - по времени, так превью читается как расписание */
  res.placements.sort(function(a, b){
    if(a.date !== b.date) return a.date < b.date ? -1 : 1;
    return tmin(a.start) - tmin(b.start);
  });

  res.notes.unshift('Разложил ' + res.placements.length + ' из ' + backlogAll.length +
                    (res.skipped.length ? ', не поместилось ' + res.skipped.length : ''));
  if(lateCount){
    res.notes.push('Задач с горящим сроком не поместилось: ' + lateCount + ' - сними что-то из недели или сдвинь дедлайн');
  }
  return res;
}

window.AutoPlan = {
  version: '1.1',
  propose: propose,
  MIN_SLOT: MIN_SLOT,
  GAP: GAP
};

/* ============================================================================
                                 САМОТЕСТЫ
   Работают только если в адресе есть `autoplan-test`. Каждый сценарий пишет
   PASS или FAIL в консоль. Плюс на КАЖДОМ результате прогоняются инварианты:
   не в blockedRanges, внутри рабочего окна, ёмкость не превышена, зазор
   соблюдён. Так один тест ловит поломку сразу по всем осям.
   ========================================================================= */

function testsRequested(){
  try{
    if(typeof window === 'undefined' || !window.location) return false;
    var l = window.location;
    var s = String(l.href || '') + String(l.search || '') + String(l.hash || '');
    return s.indexOf('autoplan-test') >= 0;
  }catch(e){ return false; }
}

function zone(o){
  o = o || {};
  return {
    work: o.work || [540, 1260],                                   // 09:00-21:00
    blockedRanges: o.blocked || [],
    peak: o.peak === undefined ? [540, 780] : o.peak,              // 09:00-13:00
    dip:  o.dip  === undefined ? [780, 900] : o.dip,               // 13:00-15:00
    capacityMin: o.cap === undefined ? 576 : o.cap
  };
}
function mkCtx(dates, backlog, zoneOpts, events){
  var z = {};
  dates.forEach(function(d, i){
    z[d] = zone(Array.isArray(zoneOpts) ? zoneOpts[i] : zoneOpts);
  });
  return {dates: dates.slice(), events: events || [], backlog: backlog, profile: {}, zones: z};
}
var D1 = '2026-08-28', D2 = '2026-08-29', D3 = '2026-08-30';

/* инварианты, обязательные для любого ответа */
function invariants(ctx, res){
  var bad = [];
  var byDay = {};
  res.placements.forEach(function(p){
    var z = ctx.zones[p.date];
    if(!z){ bad.push('размещение в день без зоны: ' + p.date); return; }
    var s = tmin(p.start), e = s + p.dur;
    if(p.dur <= 0) bad.push('нулевая длительность у ' + p.backlogId);
    if(s < z.work[0] || e > z.work[1]) bad.push('вне рабочего окна: ' + p.backlogId + ' ' + p.start);
    normRanges(z.blockedRanges).forEach(function(r){
      if(s < r[1] && e > r[0]) bad.push('пересекает blockedRange: ' + p.backlogId + ' ' + p.start);
    });
    // жёсткий запрет: новое размещение не смеет наезжать на уже стоящее событие,
    // независимо от того, попало оно в blockedRanges или нет (kind=launch - исключение)
    (ctx.events || []).forEach(function(ev){
      if(!ev || ev.date !== p.date || ev.kind === 'launch') return;
      var es = tmin(ev.start), ed = es === null ? null : es + (+ev.dur || 0);
      if(es === null || ed === null || ed <= es) return;
      if(s < ed && e > es) bad.push('пересекает существующее событие ' + (ev.id || '?') + ': ' + p.backlogId + ' ' + p.start);
    });
    (byDay[p.date] = byDay[p.date] || []).push([s, e, p.backlogId]);
  });
  Object.keys(byDay).forEach(function(k){
    var list = byDay[k].slice().sort(function(a, b){ return a[0] - b[0]; });
    for(var i = 1; i < list.length; i++){
      if(list[i][0] < list[i-1][1]) bad.push('наложение задач ' + list[i-1][2] + ' и ' + list[i][2]);
      else if(list[i][0] - list[i-1][1] < GAP) bad.push('зазор меньше ' + GAP + ' мин: ' + list[i-1][2] + ' и ' + list[i][2]);
    }
    var z = ctx.zones[k], cap = z.capacityMin;
    if(typeof cap === 'number' && cap > 0){
      var used = 0;
      (ctx.events || []).forEach(function(ev){
        if(ev.date === k && ev.kind !== 'launch') used += (+ev.dur || 0);
      });
      list.forEach(function(x){ used += x[1] - x[0]; });
      if(used > cap) bad.push('ёмкость дня ' + k + ' превышена: ' + used + ' > ' + cap);
    }
  });
  // каждая задача бэклога обязана получить ровно один вердикт
  var ids = {};
  res.placements.forEach(function(p){ ids[p.backlogId] = (ids[p.backlogId] || 0) + 1; });
  res.skipped.forEach(function(s){ ids[s.backlogId] = (ids[s.backlogId] || 0) + 1; });
  (ctx.backlog || []).forEach(function(t){
    if(ids[t.id] !== 1) bad.push('нет однозначного вердикта по задаче ' + t.id + ' (' + (ids[t.id] || 0) + ')');
  });
  return bad;
}

function runSelfTests(){
  var pass = 0, fail = 0;
  function check(name, fn){
    var msg;
    try{ msg = fn(); }
    catch(err){ msg = 'исключение: ' + (err && err.message ? err.message : err); }
    if(msg){ fail++; console.log('FAIL · ' + name + ' · ' + msg); }
    else { pass++; console.log('PASS · ' + name); }
  }
  function run(ctx){
    var r = window.AutoPlan.propose(ctx);
    var bad = invariants(ctx, r);
    if(bad.length) throw new Error('инварианты: ' + bad.join(' | '));
    return r;
  }
  function find(res, id){
    for(var i = 0; i < res.placements.length; i++) if(res.placements[i].backlogId === id) return res.placements[i];
    return null;
  }
  function why(res, id){
    for(var i = 0; i < res.skipped.length; i++) if(res.skipped[i].backlogId === id) return res.skipped[i].why;
    return null;
  }
  function has(list, sub){
    return list.some(function(s){ return String(s).indexOf(sub) >= 0; });
  }

  console.log('--- AutoPlan самотесты, версия ' + window.AutoPlan.version + ' ---');

  check('1. пустой бэклог: ничего не ставим, говорим почему', function(){
    var r = run(mkCtx([D1, D2], []));
    if(r.placements.length || r.skipped.length) return 'что-то разложено на пустом входе';
    if(!has(r.notes, 'нечего раскладывать')) return 'нет пояснения в notes';
  });

  check('2. задача без est: в skipped, длительность не выдумываем', function(){
    var r = run(mkCtx([D1], [{id: 'b1', title: 'Без оценки', track: 'x'}]));
    if(r.placements.length) return 'поставил задачу без оценки времени';
    if(String(why(r, 'b1')).indexOf('нет оценки времени') < 0) return 'формулировка: ' + why(r, 'b1');
  });

  check('3. глубокая задача идёт в пиковое окно', function(){
    var r = run(mkCtx([D1], [{id: 'b1', title: 'Монтаж', est: 120, energy: 'deep'}]));
    var p = find(r, 'b1');
    if(!p) return 'не разложена';
    var s = tmin(p.start);
    if(s < 540 || s + p.dur > 780) return 'вне пика: ' + p.start + ' + ' + p.dur;
    if(p.reason.indexOf('пик') < 0) return 'reason без упоминания пика: ' + p.reason;
  });

  check('4. механика идёт в провал', function(){
    var r = run(mkCtx([D1], [{id: 'b1', title: 'Разбор почты', est: 30, energy: 'low'}]));
    var p = find(r, 'b1');
    if(!p) return 'не разложена';
    var s = tmin(p.start);
    if(s < 780 || s + p.dur > 900) return 'вне провала: ' + p.start;
    if(p.reason.indexOf('провал') < 0) return 'reason без провала: ' + p.reason;
  });

  check('5. деривация энергии без поля energy: est>=90 тяжёлое, est<=30 механика', function(){
    var r = run(mkCtx([D1], [{id: 'heavy', title: 'Лонгрид', est: 150}, {id: 'mech', title: 'Инбокс', est: 20}]));
    var h = find(r, 'heavy'), m = find(r, 'mech');
    if(!h || !m) return 'не всё разложено';
    if(tmin(h.start) >= 780) return 'тяжёлая не в пике: ' + h.start;
    if(tmin(m.start) < 780 || tmin(m.start) >= 900) return 'механика не в провале: ' + m.start;
  });

  check('6. пика нет: раскладываем по ёмкости и предупреждаем', function(){
    var r = run(mkCtx([D1], [{id: 'b1', title: 'Тяжёлое', est: 120, energy: 'deep'}], {peak: null, dip: null}));
    if(!find(r, 'b1')) return 'без пика вообще ничего не разложил';
    if(!has(r.notes, 'Пиковое окно недоступно')) return 'нет ноты про недоступный пик: ' + r.notes.join(' | ');
  });

  check('7. переполненная неделя: ёмкость дня закрывает день', function(){
    var r = run(mkCtx([D1], [
      {id: 'b1', title: 'Раз', est: 60}, {id: 'b2', title: 'Два', est: 60}, {id: 'b3', title: 'Три', est: 60}
    ], {cap: 120}));
    if(r.placements.length !== 2) return 'разложено ' + r.placements.length + ', ожидалось 2';
    if(String(why(r, 'b3')).indexOf('не влезла') < 0) return 'формулировка отказа: ' + why(r, 'b3');
  });

  check('8. дедлайн в прошлом относительно недели: честный отказ', function(){
    var r = run(mkCtx([D2, D3], [{id: 'b1', title: 'Отчёт', est: 60, due: D1}]));
    if(r.placements.length) return 'поставил задачу после её срока';
    if(String(why(r, 'b1')).indexOf('не успевает к сроку ' + D1) < 0) return 'формулировка: ' + why(r, 'b1');
  });

  check('9. дедлайн внутри недели: задача встаёт не позже due', function(){
    var r = run(mkCtx([D1, D2, D3], [
      {id: 'fill', title: 'Забить первый день', est: 400},
      {id: 'due',  title: 'Со сроком', est: 60, due: D2}
    ], {cap: 480}));
    var p = find(r, 'due');
    if(!p) return 'не разложена: ' + why(r, 'due');
    if(p.date > D2) return 'встала позже срока: ' + p.date;
  });

  check('10. зазор 10 минут между соседними размещениями', function(){
    var r = run(mkCtx([D1], [
      {id: 'b1', title: 'Раз', est: 60, energy: 'deep'},
      {id: 'b2', title: 'Два', est: 60, energy: 'deep'}
    ]));
    if(r.placements.length !== 2) return 'разложено ' + r.placements.length;
    var a = r.placements[0], b = r.placements[1];
    var d = tmin(b.start) - (tmin(a.start) + a.dur);
    if(d < GAP) return 'зазор ' + d + ' мин';
  });

  check('11. blockedRanges неприкосновенны, слот сдвигается', function(){
    var r = run(mkCtx([D1], [{id: 'b1', title: 'Тяжёлое', est: 60, energy: 'deep'}],
                      {blocked: [[540, 600], [600, 660], [900, 960]]}));
    var p = find(r, 'b1');
    if(!p) return 'не разложена';
    if(p.start !== '11:00') return 'ожидал 11:00 после двух блоков, получил ' + p.start;
  });

  check('12. занятое пиковое окно: тяжёлое не падает в провал', function(){
    var r = run(mkCtx([D1], [{id: 'b1', title: 'Тяжёлое', est: 90, energy: 'deep'}],
                      {blocked: [[540, 780]]}));
    var p = find(r, 'b1');
    if(!p) return 'не разложена';
    var s = tmin(p.start);
    if(s < 900) return 'села в провал 13:00-15:00: ' + p.start;
  });

  check('13. приоритет и срок поднимают задачу в начало очереди', function(){
    var r = run(mkCtx([D1], [
      {id: 'plain', title: 'Без сигнала', est: 60},
      {id: 'p0',    title: 'Приоритет 0', est: 60, priority: 0},
      {id: 'soon',  title: 'Срок завтра', est: 60, priority: 4, due: D2}
    ], {cap: 600}));
    var a = find(r, 'p0'), b = find(r, 'soon'), c = find(r, 'plain');
    if(!a || !b || !c) return 'разложено не всё';
    if(!(tmin(a.start) < tmin(b.start) && tmin(b.start) < tmin(c.start)))
      return 'порядок: p0=' + a.start + ' soon=' + b.start + ' plain=' + c.start;
  });

  check('14. существующие события съедают ёмкость дня', function(){
    var ctx = mkCtx([D1], [{id: 'b1', title: 'Новая', est: 120}], {cap: 180},
                    [{id: 'e1', date: D1, title: 'Созвон', start: '16:00', dur: 120, kind: 'active'}]);
    ctx.zones[D1].blockedRanges = [[960, 1080]];
    var r = run(ctx);
    if(r.placements.length) return 'превысил ёмкость: событие 120 + задача 120 > 180';
    if(String(why(r, 'b1')).indexOf('не влезла') < 0) return 'формулировка: ' + why(r, 'b1');
  });

  check('15. рабочее окно не переполняется: длинная задача честно отсеивается', function(){
    var r = run(mkCtx([D1], [{id: 'b1', title: 'Марафон', est: 600}], {work: [540, 720], peak: [540, 600], dip: null}));
    if(r.placements.length) return 'впихнул 10 часов в трёхчасовое окно';
    if(!why(r, 'b1')) return 'нет причины отказа';
  });

  check('16. детерминизм: два прогона одинакового ctx дают одинаковый ответ', function(){
    var mk = function(){
      return mkCtx([D1, D2], [
        {id: 'a', title: 'A', est: 90, energy: 'deep'},
        {id: 'b', title: 'B', est: 30, energy: 'low'},
        {id: 'c', title: 'C', est: 60, priority: 2, due: D2},
        {id: 'd', title: 'D', est: 45},
        {id: 'e', title: 'E'}
      ], {cap: 300});
    };
    var r1 = JSON.stringify(run(mk())), r2 = JSON.stringify(run(mk()));
    if(r1 !== r2) return 'ответы разошлись';
    if(r1.indexOf('Math.random') >= 0) return 'в ответе мусор';
  });

  check('17. мусор на входе не роняет функцию', function(){
    var r = window.AutoPlan.propose(undefined);
    if(!r || !Array.isArray(r.placements) || !Array.isArray(r.skipped) || !Array.isArray(r.notes)) return 'сломался контракт выхода';
    var r2 = window.AutoPlan.propose({dates: ['кривая'], backlog: [{id: 'b1', est: 'нет'}], zones: null});
    if(r2.placements.length) return 'разложил в никуда';
    var r3 = window.AutoPlan.propose({dates: [D1], zones: {}, backlog: [{id: 'b1', est: 60}]});
    if(r3.placements.length) return 'разложил в день без зоны';
    if(!has(r3.notes, 'Нет дней для раскладки')) return 'нет ноты про отсутствие дней: ' + r3.notes.join(' | ');
  });

  check('18. big3: щель между главными делами дня бережём, если место есть в другом месте', function(){
    var ctx = mkCtx([D1], [{id: 'b1', title: 'Механика', est: 30, energy: 'deep'}], undefined,
                    [{id: 'm1', date: D1, title: 'Съёмка', start: '10:00', dur: 60, kind: 'active'},
                     {id: 'm2', date: D1, title: 'Монтаж', start: '12:00', dur: 60, kind: 'active'}]);
    ctx.big3 = {}; ctx.big3[D1] = ['m1', 'm2'];
    var r = run(ctx);
    var p = find(r, 'b1');
    if(!p) return 'не разложена: ' + why(r, 'b1');
    var s = tmin(p.start);
    if(s >= 660 && s < 720) return 'залез в щель между главными делами, хотя было место в другом месте: ' + p.start;
    if(p.reason.indexOf('между главными делами') >= 0) return 'ушёл в крайний заход без нужды: ' + p.reason;
  });

  check('19. big3: если свободно только между главными делами - ставим туда, а не пропускаем задачу', function(){
    var ctx = mkCtx([D1], [{id: 'b1', title: 'Довесок', est: 30, energy: 'deep'}],
                    {work: [540, 780], peak: [540, 780], dip: null},
                    [{id: 'm1', date: D1, title: 'Съёмка', start: '09:00', dur: 60, kind: 'active'},
                     {id: 'm2', date: D1, title: 'Монтаж', start: '12:00', dur: 60, kind: 'active'}]);
    ctx.big3 = {}; ctx.big3[D1] = ['m1', 'm2'];
    var r = run(ctx);
    var p = find(r, 'b1');
    if(!p) return 'пропустил задачу, хотя щель между главными делами была свободна: ' + why(r, 'b1');
    if(p.start !== '10:00') return 'ожидал 10:00 в щели между главными делами, получил ' + p.start;
    if(p.reason.indexOf('между главными делами') < 0) return 'reason не объясняет крайний случай: ' + p.reason;
  });

  check('20. when: дата за горизонтом ctx.dates (три формата) - откладываем, не трогаем', function(){
    var variants = ['10.09', '~10.09', '10.09.2026'];
    for(var i = 0; i < variants.length; i++){
      var r = run(mkCtx([D1, D2], [{id: 'b1', title: 'Отчёт', est: 60, when: variants[i]}]));
      if(r.placements.length) return 'поставил задачу с пометкой when=' + variants[i];
      if(String(why(r, 'b1')).indexOf('отложено тобой до 10.09') < 0) return 'формулировка при "' + variants[i] + '": ' + why(r, 'b1');
    }
  });

  check('21. when: дата внутри ctx.dates - не трогаем, раскладываем как обычно', function(){
    var r = run(mkCtx([D1, D2, D3], [{id: 'b1', title: 'Скоро', est: 30, when: '29.08'}]));
    var p = find(r, 'b1');
    if(!p) return 'не разложена, хотя пометка внутри горизонта недели: ' + why(r, 'b1');
  });

  check('22. when: «след[ующая] неделя» в любом написании - откладываем без разбора даты', function(){
    var variants = ['след. неделя', 'следующая', 'Следующая неделя'];
    for(var i = 0; i < variants.length; i++){
      var r = run(mkCtx([D1], [{id: 'b1', title: 'Потом', est: 30, when: variants[i]}]));
      if(r.placements.length) return 'поставил задачу с пометкой when="' + variants[i] + '"';
      if(String(why(r, 'b1')).indexOf('следующую неделю') < 0) return 'формулировка при "' + variants[i] + '": ' + why(r, 'b1');
    }
  });

  check('23. переполненный день закрыт целиком, но соседний день продолжает работать', function(){
    var ctx = mkCtx([D1, D2], [{id: 'b1', title: 'Задача', est: 30}], {cap: 200},
                    [{id: 'e1', date: D1, title: 'Забито', start: '09:00', dur: 300, kind: 'active'}]);
    var r = run(ctx);
    var p = find(r, 'b1');
    if(!p) return 'не разложена: ' + why(r, 'b1');
    if(p.date !== D2) return 'попытался влезть в перегруженный день ' + D1 + ': сел на ' + p.date;
    if(!has(r.notes, 'уже перегружен (300 из 200)')) return 'нет честной ноты про перегруз дня: ' + r.notes.join(' | ');
    if(has(r.notes, 'Неделя уже перегружена')) return 'ошибочно объявил перегруженной всю неделю из-за одного дня';
  });

  check('24. вся неделя перегружена - общая честная нота, ни одной задачи никуда не лезем', function(){
    var r = run(mkCtx([D1], [{id: 'b1', title: 'Задача', est: 30}], {cap: 100},
                      [{id: 'e1', date: D1, title: 'Забито', start: '09:00', dur: 200, kind: 'active'}]));
    if(r.placements.length) return 'умудрился поставить задачу в перегруженную неделю';
    if(!has(r.notes, 'Неделя уже перегружена')) return 'нет общей ноты о перегрузе недели: ' + r.notes.join(' | ');
    if(!has(r.notes, 'уже перегружен (200 из 100)')) return 'нет ноты по конкретному дню: ' + r.notes.join(' | ');
  });

  check('25. событие без явного поля kind - всё равно жёсткий блок размещения', function(){
    var ctx = mkCtx([D1], [{id: 'b1', title: 'Новая', est: 60}], {cap: 600},
                    [{id: 'e1', date: D1, title: 'Летучка', start: '13:00', dur: 60}]);   // kind нарочно не задан
    var r = run(ctx);
    var p = find(r, 'b1');
    if(!p) return 'не разложена: ' + why(r, 'b1');
    if(p.start === '13:00') return 'сел ровно на событие без явного kind, будто блока не было';
    if(tmin(p.start) < 840) return 'пересёкся с событием 13:00-14:00 без явного kind: ' + p.start;
  });

  console.log('--- ИТОГО: PASS ' + pass + ', FAIL ' + fail + ' ---');
  return {pass: pass, fail: fail};
}

window.AutoPlan._selfTest = runSelfTests;
if(testsRequested()){
  if(typeof setTimeout === 'function') setTimeout(runSelfTests, 0);
  else runSelfTests();
}

})();

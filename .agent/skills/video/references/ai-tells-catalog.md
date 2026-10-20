# AI tells catalog (RU + EN)

Каталог типовых «AI tells» - конструкций которые выдают что писала не автор. Используется в `workflow/05-review.md` 5.1 (regex matrix).

Дополнение к `_voice-TEMPLATE.md` (26 классов A-Z с full examples). Этот файл - flat list для regex детектора.

## RU lexical tells

| Pattern | Replacement |
|---|---|
| «не просто X, а Y» | «Y. X = его часть» |
| «давайте разберём» | сразу к делу |
| «давайте посмотрим» | сразу к делу |
| «важно понимать» | убрать |
| «стоит отметить» | убрать |
| «стоит обратить внимание» | убрать |
| «не секрет, что» | убрать или личное |
| «эффективный» (no number) | конкретный результат |
| «инновационный» | конкретный механизм |
| «уникальный» | конкретное отличие |
| «полезный» | конкретное benefit |
| «интересный» | конкретный insight |
| «современный» | конкретная характеристика |
| «открывает возможности» | «делает X» |
| «помогает вам» | «с этим ты [действие]» |
| «открывает двери» | конкретика |
| «новый уровень» | конкретный показатель |
| «качественно новый» | конкретно |
| «на сегодняшний день» | убрать |
| «в современном мире» | убрать |
| «в наши дни» | убрать |
| «безусловно» | убрать или «100%» |
| «определённо» | убрать |
| «несомненно» | убрать |

## RU structural tells

| Pattern | Replacement |
|---|---|
| «быстро, легко и эффективно» | одно конкретное |
| «просто, понятно и доступно» | одно конкретное |
| «один из самых X» | «самый X» или конкретика |
| «более того» | «и ещё» |
| «при этом» | «и» |
| «однако» | «но» |
| «таким образом» | убрать |
| «следовательно» | «значит» |
| «вместе с тем» | убрать |
| «помимо этого» | «и» |
| «кроме того» | «и ещё» |
| «также» (начало beat) | конкретный link |
| «стоит / следует / нужно» | imperative directly |
| «по сути» | убрать |
| «на деле» | убрать |
| «по большому счёту» | убрать |
| «в целом» | убрать |
| «в общем» | убрать |

## RU audience tells (автора specific)

| Pattern | Replacement |
|---|---|
| «эксперт» (audience) | «ты», «тех у кого» |
| «эксперты по X» | «один человек который» |
| «специалисты» | «ты», «один человек» |
| «без опыта в коде» | «не маркетолог» |
| «не программист» | «не маркетолог» |
| «программисты делают X» | «маркетологи делают X» |

## RU listing tells (generic AI artifacts)

| Pattern | Replacement |
|---|---|
| «10 советов про X» | конкретная методология |
| «топ 5 ошибок» | personal observation |
| «N способов добиться» | personal mechanism |
| «100 промптов в подарок» | trip wire mechanic |
| «X секретов» | один конкретный |
| «N лайфхаков» | один конкретный workflow |

## EN lexical tells

| Pattern | Replacement |
|---|---|
| «It's important to note that» | drop |
| «It's worth mentioning» | drop |
| «Let's dive into» | drop, go directly |
| «In today's world» | drop |
| «In the modern age» | drop |
| «It's no secret that» | drop or personal |
| «effective» (no number) | concrete result |
| «innovative» | concrete mechanism |
| «unique» | concrete distinction |
| «cutting-edge» | concrete |
| «state-of-the-art» | concrete |
| «game-changing» | concrete impact |
| «revolutionary» | concrete impact |
| «seamless» | concrete process |
| «leverage» | «use» |
| «utilize» | «use» |
| «delve» | «look at» / specific action |
| «moreover» | «and» / drop |
| «furthermore» | drop |
| «in addition» | «and» |
| «consequently» | «so» |
| «therefore» (spoken) | «so» |

## EN structural tells

| Pattern | Replacement |
|---|---|
| «Not only X, but Y» | «Y. X too» |
| «Various factors contribute» | specific factor |
| «A wide range of» | specific count |
| «In light of» | spoken equivalent |
| «With that said» | drop |
| «That being said» | drop |
| «As we can see» | drop |

## EN audience tells

| Pattern | Replacement |
|---|---|
| «experts» (audience) | «you», «folks who» |
| «professionals» | «you» |
| «specialists» | «you» |

## Detection method

В 05-review.md:
1. Scan каждый beat через regex matrix
2. Hit = автоматическая замена если есть mapping, иначе flag
3. Output: list detected + applied replacements

## Maintenance

- Новые AI tells появляются с каждым model upgrade
- Раз в квартал - full sweep на новые patterns
- Каждый новый pattern зафиксировать прецедентом (пропустил skill 1 раз - добавил pattern)
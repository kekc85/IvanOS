# Legal & Licenses cheat sheet

Каждое изображение в output папке обязано иметь явный license tag в README.md. Если неизвестно — `UNKNOWN — verify before use`.

## License types (по убыванию свободы)

### Public Domain (PD)
- Можно всё: commercial use, modification, no attribution required
- Источники: US government works, expired copyright, explicit PD dedication
- На Wikimedia Commons: `{{PD-self}}`, `{{PD-USGov}}`, `{{PD-old-70}}`

### CC0 (Creative Commons Zero)
- Equivalent to PD
- Источники: Unsplash, Pexels, Wikimedia Commons с CC0 tag

### CC-BY (Creative Commons Attribution)
- Commercial + modification OK
- Требует attribution: автор + license + link
- Пример строки в README:
  ```
  Photo by John Doe, CC-BY-4.0
  Source: https://commons.wikimedia.org/wiki/File:Example.jpg
  ```

### CC-BY-SA (Attribution-ShareAlike)
- Commercial + modification OK
- Attribution required
- Derivative works должны быть тоже CC-BY-SA (ShareAlike clause)
- ⚠️ Если используешь в коммерческой публикации — финальный артефакт тоже CC-BY-SA

### CC-BY-NC (NonCommercial)
- ⚠️ Запрещено для коммерческого использования
- Контент автора = коммерческий → CC-BY-NC брать НЕЛЬЗЯ для production
- Только для educational / personal projects

### CC-BY-ND (NoDerivatives)
- Нельзя модифицировать
- Можно использовать as-is с attribution
- Не подходит для crops / overlays / композиций

### "All Rights Reserved" / Copyright
- Default по умолчанию для большинства фото
- Требует explicit permission или fair use claim

## Press kit / Editorial use only

### Company press kits
- Anthropic press kit / OpenAI press / etc
- Usually OK для: news coverage, editorial articles, educational content
- Usually NOT OK для: paid ads, merchandise, endorsements (implies endorsement)
- Read terms: `<company>.com/press/terms` или footer license box

### News editorial photos
- TechCrunch / Verge / Reuters/AP photos
- Editorial use only — нельзя в ads без separate license
- Attribution to photographer + outlet required

## Fair use (US doctrine)

4 factors:
1. Purpose: commercial vs educational (educational favors fair use)
2. Nature: published facts vs creative works
3. Amount: small portion vs whole work
4. Effect on market: doesn't compete with original

Для контент-завода автора:
- ✅ Comment / criticism / parody — likely fair use
- ✅ Educational explainer с context — likely fair use
- ⚠️ Decorative use в monetized post — borderline
- ❌ Direct re-publication без transformation — NOT fair use

⚠️ Fair use ≠ blanket license. Для high-stakes использования (sponsored posts, paid ads) — strict license check.

## По юрисдикциям

### USA (DMCA)
- Fair use doctrine
- Right of publicity (commercial use лица требует release)
- DMCA takedown process если ошибся

### EU (GDPR + copyright directives)
- Стрикчер про personal data (фото = personal data)
- Right to be forgotten
- Журналистский exemption есть, но узкий

### Россия (ГК РФ ч.4)
- Свободное использование для информационных/научных/учебных целей с указанием автора (ст. 1274)
- Изображение гражданина (ст. 152.1 ГК) — для коммерции нужно согласие
- Исключение: использование в государственных/общественных интересах + публичная фигура в публичном месте

## License extraction workflow (Wikimedia)

1. Open file page: `commons.wikimedia.org/wiki/File:<name>`
2. Scroll к "Licensing" section
3. Найти license tag (CC-BY-SA-4.0 / PD-self / etc)
4. Записать author + license + source URL в README.md

## License extraction workflow (press kit)

1. Open press kit landing page
2. Найти "Terms of use" / "License" / "Permitted uses"
3. Цитировать relevant clause в README.md
4. Если нет explicit license → пометить `License: UNKNOWN — verify with company press contact before commercial use`

## README.md license block template

```markdown
## Files

### dario-amodei-hires.jpg
- Source: https://commons.wikimedia.org/wiki/File:Dario_Amodei_at_TechCrunch_Disrupt_2023_01_(cropped).jpg
- Author: TechCrunch (photographer Steve Jennings)
- License: CC-BY-2.0
- Use: ✅ commercial OK with attribution required
- Original URL: https://upload.wikimedia.org/wikipedia/commons/e/e4/Dario_Amodei_at_TechCrunch_Disrupt_2023_01_(cropped).jpg

### anthropic-company-page.png
- Source: https://www.anthropic.com/company
- License: Editorial use only (screenshot of public page)
- Use: ✅ for commentary/educational, ❌ as standalone visual in paid ads

### dario-google-images.png
- Source: Google Images search result screenshot
- License: COMPOSITE — individual photos have separate licenses (do NOT use as final asset)
- Use: ✅ as reference / variety preview only, ❌ for publication
```

## Anti-patterns

- ❌ "Found on Google" ≠ free to use
- ❌ "No copyright notice visible" ≠ public domain
- ❌ Crop-and-publish без attribution даже если CC-BY
- ❌ AI-generated photos выдавать за real (separate from licensing — это honesty issue)
- ❌ Использовать leaked / hacked photos «потому что они есть в интернете»
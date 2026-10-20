# Production handoff map

Детальный mapping Mode + tier → downstream production skill + точный brief format.

Используется в `workflow/06-output.md` для генерации production handoff brief.

## Decision matrix

| Mode | Tier | Intent / signal | Recommended skill | Justification |
|---|---|---|---|---|
| A / B1 / B2 | short-15-30s | demo / build-with-me | screen-record-face-cam | авторская alpha format, authentic |
| A / B1 / B2 | short-30-60s | demo / build-with-me | screen-record-face-cam | most common авторский use |
| A / B1 / B2 | short-30-60s | trend-jack / split | split-screen-trend-jack | trending content capture 24-72h |
| A / B1 / B2 | short-30-60s | daily volume / no recording | ai-avatar-news | HeyGen Avatar V pipeline |
| A / B1 / B2 | short-30-60s | before/after AI rebuild | before-after | highest stop-scroll Нельзяграм |
| A / B1 / B2 | short-60-180s | deep demo + commentary | screen-record-face-cam | room for context |
| C | any short | replication | replicate-reel | Remotion render with spec |
| D | short-30-60s | надиктовка short | screen-record-face-cam OR ai-avatar-news | depends on raw audio quality |
| A / B / C / D | mid-3-10min | YouTube mid-form | (manual production v1.0; future: youtube-mid-form skill) | no automated skill |
| A / B / C / D | long-10-60min | YouTube long-form | (manual production v1.0; future: youtube-long-form skill) | experimental tier |

## Brief format per downstream skill

### screen-record-face-cam

```yaml
script:
  text: "<full script>"
  captions: [<ALL CAPS lines>]
  hook_first_3s: "<text>"

demo_brief:
  tool: "<Claude / Lovable / Bolt / Cursor / etc>"
  steps_to_demonstrate:
    - "<step 1>"
    - "<step 2>"
    - "<step 3 (max 3-5)>"
  expected_result_on_screen: "<specific>"
  estimated_demo_duration_sec: <number>

production_specs:
  aspect: "9:16"
  face_cam_corner: "bottom-right"
  face_cam_size: "20% area"
  caption_style: "Hormozi yellow word-by-word"
  recording_tool: "Tella OR Screen Studio"
  audio: "wireless mic"
```

### split-screen-trend-jack

```yaml
script:
  text: "<bottom-half voice over>"
  captions: [<ALL CAPS lines>]
  hook_first_3s: "<text>"

top_half_brief:
  source_url: "<viral trending content URL>"
  source_published_date: "<YYYY-MM-DD>"
  hours_since_publish: <number>
  target_under_72h: true
  AI_tool_to_generate_top: "<Kling | Higgsfield | Nano Banana | ChatGPT image>"
  top_half_prompt: "<exact AI prompt>"
  top_half_duration_sec: <number>

bottom_half_brief:
  type: "face-cam reaction OR AI demo"
  recording_tool: "<iPhone front cam OR Screen Studio>"
  voice_over_script: "<from script.text>"

production_specs:
  aspect: "9:16 split 50/50"
  hook_caption_overlay_first_1_5s: "<text>"
  sync_moments: ["<moment 1>", "<moment 2>"]
  total_duration_sec: <15-25>
```

### ai-avatar-news

```yaml
script:
  text: "<full script>"
  captions: [<ALL CAPS lines>]
  hook_first_3s: "<text>"

avatar_specs:
  tool: "HeyGen Avatar V"
  voice: "ElevenLabs PVC <Russian | English>"
  face_time_pct: "<30 (uncanny valley prevention)"
  length_sec: <30-90>

b_roll_specs:
  tool: "Kling 3.0"
  shots:
    - duration_sec: 3
      description: "<shot 1 description>"
    - duration_sec: 5
      description: "<shot 2>"
    - duration_sec: 7
      description: "<shot 3>"
  estimated_cost_usd: <number>

assembly_specs:
  tool: "Descript"
  captions: "Hormozi word-by-word"
  aspect: "9:16"
  ai_label: true   # Нельзяграм + TikTok requirement
```

### before-after

```yaml
script:
  text: "<voice over script>"
  captions: [<ALL CAPS lines>]
  hook_first_3s: "<text>"

before_specs:
  source: "<own old | student project | open-source | brand-trending>"
  problem_visible: "<ugly UI | slow | confusing copy>"
  recording_duration_sec: <5-10>
  recording_tool: "Screen Studio OR Tella"

ai_rebuild_specs:
  tool_used: "<Lovable | Bolt | Cursor | Claude Code>"
  estimated_build_time_min: <10-30>
  key_prompts_to_demonstrate:
    - "<prompt 1>"
    - "<prompt 2>"
    - "<prompt 3>"

after_specs:
  recording_duration_sec: <5-10>
  zoom_focus_areas: ["<area 1>", "<area 2>"]

edit_specs:
  transition_type: "<split-screen | wipe>"
  hook_caption_overlay_first_1_5s: "<text>"
  tool_name_displayed: true
  total_duration_sec: <15-25>
  aspect: "9:16"
```

### replicate-reel (Mode C)

```yaml
script:
  captions: [<for spec.captions[] in Remotion>]
  text: "<for voice-generate>"

remotion_spec_hints:
  composition: "<TutorialOfferSplitScreen | VariableComposition>"
  duration_sec: <from card.md>
  speaker_audio_src: null   # use --with-voice flag to fill
  speaker_video_src: null   # use --with-avatar flag to fill
  overlay_timeline_count: <D / 2.5 sec>
  layout_timeline: <if VariableComposition>
  caption_color: "<#FFFFFF (variable) | #FFEB3B (offer)>"

ingest_dir: "<absolute path>"
video_id: "<id>"

invocation_suggestion: "/replicate <ingest_id> --with-voice --with-avatar"
```

### cut-from-long-form (post-publish, mid/long tier)

Этот flow обратный - video skill производит long-form script, после publish → cut-from-long-form извлекает Shorts.

```yaml
long_form_metadata:
  youtube_url: "<after publish>"
  duration_min: <number>
  language: "<ru | en>"
  
cuts_request:
  target_clip_count: 5-7
  target_clip_duration_sec: 30-60
  captions_language: "<auto-detect or explicit>"
  aspect: "9:16"
  auto_dub_target_lang: "<en if source ru, ru if source en>"

production_specs_after_cuts:
  caption_style: "Hormozi word-by-word"
  cross_distribution: ["YouTube Shorts", "Нельзяграм Reels", "TikTok"]
```

## Default fallback (если intent неясен)

- Tier short → ai-avatar-news (автор не должен лично записывать каждое видео)
- Tier mid → manual production brief
- Tier long → manual production brief

## Intent detection signals

Из user input в Mode A/B/D можно extract intent:
- «снять самому» / «face-cam» / «build-with-me» → screen-record-face-cam
- «trend-jack» / «split» / «реакция» → split-screen-trend-jack
- «без записи» / «daily volume» / «avatar» → ai-avatar-news
- «before/after» / «rebuild» / «transformation» → before-after
- Никакого signal → ask user или default

## Override

Пользователь может указать `--handoff <skill>` явно в начальном запросе → router передаёт в `config.flags.override_handoff` → 06-output.md использует override вместо decision matrix.

## Cross-refs

- Sister skills: см. SKILL.md Memory cross-refs
- `feedback_strategy_copy_faster_more_better` - same-format reproduction strategy
- `project_viral_hook_library_2026` - hook patterns по платформам
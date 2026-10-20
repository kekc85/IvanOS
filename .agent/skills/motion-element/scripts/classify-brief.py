#!/usr/bin/env python3
"""classify-brief.py — bag-of-keywords классификатор брифа → template_id.

Грубый детерминированный роутер (без LLM): печатает топ-3 кандидата с весами.
Низкая уверенность (top < 2 или разрыв top1-top2 < 2) → скилл переспрашивает.

Usage: python3 classify-brief.py "сделай тикер MRR с 0 до 9700"
"""
import sys, re, json

# template_id -> keywords (RU+EN), вес 1 за совпадение
KEYWORDS = {
    "comment-pop":       ["коммент", "комменты", "лайк", "реакц", "эмодзи", "social", "comment", "like", "engagement", "всплыва", "pop"],
    "count-up-ticker":   ["счётчик", "счетчик", "count", "тикер", "ticker", "число", "растёт", "роллинг", "подписчик", "counter", "roll", "0 до", "from", "до "],
    "kinetic-caption":   ["кинетик", "kinetic", "подписи", "субтитр", "caption", "слова появля", "под озвучк", "под бит", "караоке", "highlight", "текст по словам"],
    "code-terminal":     ["терминал", "terminal", "код печат", "командн", "консоль", "code typ", "печатает код", "syntax", "промпт в код"],
    "before-after-wipe": ["было стало", "до после", "before", "after", "wipe", "трансформац", "переход было", "сравнение до"],
    "ui-comparison-bar": ["сравнен", "vs", "против", "comparison", "бар", "логотип", "tool a", "инструмент", "winner", "рейтинг бар"],
    "chat-bubbles":      ["переписк", "чат", "chat", "imessage", "сообщени", "пузыр", "bubble", "dm", "диалог", "telegram чат"],
    "scribble-callout":  ["маркер", "кружок", "обведи", "стрелк", "подчеркн", "scribble", "callout", "circle", "arrow", "нарисуй"],
    "screen-zoom-punch": ["зум", "zoom", "приблиз", "punch", "наезд", "highlight кнопк", "screen record", "скринкаст", "фокус на"],
    "price-odometer":    ["цена", "price", "одометр", "odometer", "скидк", "discount", "прайс", "стоимость", "ролл цен"],
}

def classify(brief: str):
    b = brief.lower()
    scores = {}
    for tid, kws in KEYWORDS.items():
        s = sum(1 for kw in kws if kw in b)
        if s:
            scores[tid] = s
    ranked = sorted(scores.items(), key=lambda x: -x[1])
    top = ranked[:3]
    confident = bool(top) and top[0][1] >= 2 and (len(top) < 2 or top[0][1] - top[1][1] >= 2)
    return {"brief": brief, "ranked": top, "confident": confident,
            "ask_user": None if confident else [t for t, _ in top[:2]] or list(KEYWORDS)[:2]}

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: classify-brief.py \"<бриф>\"", file=sys.stderr); sys.exit(2)
    print(json.dumps(classify(" ".join(sys.argv[1:])), ensure_ascii=False, indent=2))
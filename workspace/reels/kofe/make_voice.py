import asyncio
import edge_tts

text = """Если до обеда тебе нужны минимум две чашки кофе, чтобы просто собрать голову в кучу - у меня плохая новость.
Кофе не даёт тебе новую энергию. Он просто выключает в мозге датчик усталости.
Ты берёшь энергию взаймы у своих надпочечников под грабительский процент. Через час - яма, голова гудит, а к вечеру ты выжат в ноль.
Настоящая энергия рождается не от стимуляторов. Она вырабатывается внутри клеток - твоими митохондриями. И когда их мембраны повреждены, клетки буквально задыхаются.
Как запустить естественную выработку энергии без кофеиновых качелей, мы подробно разобрали в бесплатной Школе долголетия.
Напиши слово КОФЕ в комментариях, и я пришлю тебе доступ ко всем урокам."""

async def main():
    communicate = edge_tts.Communicate(text, "ru-RU-DmitryNeural")
    sub_maker = edge_tts.SubMaker()
    with open("workspace/reels/kofe/voice_kofe.mp3", "wb") as f:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] in ("WordBoundary", "SentenceBoundary"):
                sub_maker.feed(chunk)
    
    with open("workspace/reels/kofe/subtitles.srt", "w", encoding="utf-8") as f:
        f.write(sub_maker.get_srt())
    
    print("SRT_AND_AUDIO_OK")

if __name__ == "__main__":
    asyncio.run(main())

import whisper
import json
import os

model = whisper.load_model("large-v2")
audios = sorted(os.listdir("audios"))   

all_chunks = []
all_texts = {}  

for audio in audios:
    number = audio.split("-")[0].strip()
    name_no_ext = os.path.splitext(audio)[0]
    idx = name_no_ext.rfind(']')
    title = name_no_ext[idx+1:].strip() if idx != -1 else name_no_ext

    print("Processing:", number, title)
    result = model.transcribe(audio=f"audios/{audio}",
                              language="hi",
                              task="translate",
                              word_timestamps=False)

    
    for segment in result.get("segments", []):
        all_chunks.append({
            "number": number,
            "title": title,
            "start": segment["start"],
            "end": segment["end"],
            "text": segment["text"]
        })

    
    all_texts[f"{number}_{title}"] = result.get("text", "")


chunks_with_metadata = {
    "chunks": all_chunks,
    "texts_per_file": all_texts
}

with open("jsons.json", "w", encoding="utf-8") as f:
    json.dump(chunks_with_metadata, f, ensure_ascii=False, indent=2)


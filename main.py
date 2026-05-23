import os, requests, json
from datetime import datetime
from pathlib import Path

# ─── YOUR KEYS ──────────────────────────────────────────
GROQ_KEY      = os.environ.get("GROQ_KEY", "")
PEXELS_KEY    = os.environ.get("PEXELS_KEY", "")
ELEVEN_KEY    = os.environ.get("ELEVEN_KEY", "")
VOICE_ID      = os.environ.get("VOICE_ID", "")

CHANNEL      = "KaifiyatTV"
STYLE        = "cinematic, dramatic, Hinglish — mix of Urdu and English like Pakistanis naturally speak"
NICHE        = "space, science, and geopolitics"

# ─── STEP 1: GET TOPIC ──────────────────────────────────
def get_topic():
    headers = {
        "Authorization": f"Bearer {GROQ_KEY}",
        "Content-Type": "application/json"
    }
    prompt = f"""You are the creative director of {CHANNEL}, a Pakistani YouTube channel.
Niche: {NICHE}
Style: {STYLE}

Give me ONE viral YouTube topic for today. Must be:
- Original and not copied from any channel
- Dramatic and curiosity-triggering
- Something a Pakistani 15-30 year old would click immediately

Return ONLY this JSON, nothing else:
{{"title": "...", "hook": "...", "keywords": ["...", "...", "..."]}}"""

    r = requests.post("https://api.groq.com/openai/v1/chat/completions",
        headers=headers,
        json={
            "model": "llama3-70b-8192",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 300,
            "temperature": 0.9
        })
    text = r.json()["choices"][0]["message"]["content"]
    start = text.find("{")
    end   = text.rfind("}") + 1
    return json.loads(text[start:end])

# ─── STEP 2: WRITE SCRIPT ───────────────────────────────
def write_script(topic):
    headers = {
        "Authorization": f"Bearer {GROQ_KEY}",
        "Content-Type": "application/json"
    }
    prompt = f"""Write a full YouTube script for: {topic['title']}

Rules:
- Language: Hinglish (natural mix of Urdu + English, how Pakistanis actually talk)
- Tone: cinematic, dramatic, emotional — like a space documentary
- Length: 8-10 minutes when spoken (1200-1400 words)
- Structure: HOOK (30 sec) → BUILD UP → MAIN STORY → MIND BLOW MOMENT → CONCLUSION
- Start with something that freezes the viewer. Example: "Sochiye... agar aaj raat aasman se koi cheez gir jaye..."
- 100% original perspective, not copied from anywhere
- End with a question that makes them want to subscribe

Write ONLY the script. No labels, no stage directions."""

    r = requests.post("https://api.groq.com/openai/v1/chat/completions",
        headers=headers,
        json={
            "model": "llama3-70b-8192",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 2000,
            "temperature": 0.85
        })
    return r.json()["choices"][0]["message"]["content"]

# ─── STEP 3: WRITE METADATA ─────────────────────────────
def write_metadata(topic):
    headers = {
        "Authorization": f"Bearer {GROQ_KEY}",
        "Content-Type": "application/json"
    }
    prompt = f"""For a YouTube video titled: "{topic['title']}"

Write:
1. A YouTube description (150 words, Hinglish, with emojis, call to action to subscribe)
2. 15 SEO tags

Return ONLY this JSON, nothing else:
{{"description": "...", "tags": ["...", "..."]}}"""

    r = requests.post("https://api.groq.com/openai/v1/chat/completions",
        headers=headers,
        json={
            "model": "llama3-70b-8192",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 600,
            "temperature": 0.7
        })
    text = r.json()["choices"][0]["message"]["content"]
    start = text.find("{")
    end   = text.rfind("}") + 1
    return json.loads(text[start:end])

# ─── STEP 4: GENERATE VOICE ─────────────────────────────
def generate_voice(script, output_path):
    headers = {
        "xi-api-key": ELEVEN_KEY,
        "Content-Type": "application/json"
    }
    data = {
        "text": script[:4500],
        "model_id": "eleven_monolingual_v1",
        "voice_settings": {
            "stability": 0.4,
            "similarity_boost": 0.8,
            "style": 0.6
        }
    }
    r = requests.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}",
        headers=headers,
        json=data
    )
    if r.status_code == 200:
        with open(output_path, "wb") as f:
            f.write(r.content)
        print("Voice generated")
        return True
    else:
        print(f"Voice error: {r.text}")
        return False

# ─── STEP 5: FETCH FOOTAGE ──────────────────────────────
def fetch_footage(keywords, output_dir):
    Path(output_dir).mkdir(exist_ok=True)
    headers = {"Authorization": PEXELS_KEY}
    clips = []
    for kw in keywords[:3]:
        r = requests.get(
            f"https://api.pexels.com/videos/search?query={kw}&per_page=3&size=medium",
            headers=headers
        )
        for v in r.json().get("videos", [])[:2]:
            files = v.get("video_files", [])
            hd = next((f for f in files if f.get("quality") == "hd"), files[0] if files else None)
            if hd:
                path = f"{output_dir}/{v['id']}.mp4"
                with open(path, "wb") as f:
                    f.write(requests.get(hd["link"]).content)
                clips.append(path)
                print(f"Downloaded clip: {path}")
    return clips

# ─── STEP 6: ASSEMBLE VIDEO ─────────────────────────────
def assemble_video(clips, audio_path, output_path, is_short=False):
    try:
        from moviepy.editor import VideoFileClip, AudioFileClip, concatenate_videoclips
        audio    = AudioFileClip(audio_path)
        duration = min(audio.duration, 60 if is_short else audio.duration)
        size     = (1080, 1920) if is_short else (1920, 1080)
        per_clip = duration / max(len(clips), 1)
        processed = []
        for c in clips:
            try:
                vc = VideoFileClip(c).subclip(0, min(per_clip, VideoFileClip(c).duration))
                vc = vc.resize(size)
                processed.append(vc)
            except:
                continue
        if not processed:
            return False
        final = concatenate_videoclips(processed, method="compose")
        final = final.set_audio(audio.subclip(0, duration))
        final.write_videofile(output_path, fps=24, codec="libx264", audio_codec="aac", logger=None)
        print(f"Video ready: {output_path}")
        return True
    except Exception as e:
        print(f"Assembly error: {e}")
        return False

# ─── STEP 7: UPLOAD TO YOUTUBE ──────────────────────────
def upload_to_youtube(video_path, title, description, tags, is_short=False):
    try:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload
        creds   = Credentials.from_authorized_user_file("token.json",
                    ["https://www.googleapis.com/auth/youtube.upload"])
        youtube = build("youtube", "v3", credentials=creds)
        final_title = f"{title} #Shorts" if is_short else title
        body = {
            "snippet": {
                "title":       final_title[:100],
                "description": description,
                "tags":        tags,
                "categoryId":  "28"
            },
            "status": {"privacyStatus": "public"}
        }
        media    = MediaFileUpload(video_path, chunksize=-1, resumable=True)
        request  = youtube.videos().insert(part=",".join(body.keys()), body=body, media_body=media)
        response = request.execute()
        print(f"Uploaded: https://youtube.com/watch?v={response['id']}")
        return response["id"]
    except Exception as e:
        print(f"Upload error: {e}")
        return None

# ─── MAIN ───────────────────────────────────────────────
def run():
    today = datetime.now().strftime("%Y%m%d_%H%M")
    print(f"\n KaifiyatTV Bot starting — {today}\n")

    print("Step 1: Getting topic...")
    topic = get_topic()
    print(f"Topic: {topic['title']}")

    print("Step 2: Writing script...")
    script = write_script(topic)

    print("Step 3: Writing metadata...")
    meta = write_metadata(topic)

    print("Step 4: Generating voice...")
    audio = f"/tmp/voice_{today}.mp3"
    generate_voice(script, audio)

    print("Step 5: Fetching footage...")
    clips = fetch_footage(topic["keywords"], f"/tmp/clips_{today}")

    print("Step 6: Assembling main video...")
    main_video = f"/tmp/main_{today}.mp4"
    assemble_video(clips, audio, main_video, is_short=False)

    print("Step 6b: Assembling Short...")
    short_video = f"/tmp/short_{today}.mp4"
    assemble_video(clips, audio, short_video, is_short=True)

    print("Step 7: Uploading...")
    upload_to_youtube(main_video, topic["title"], meta["description"], meta["tags"], is_short=False)
    upload_to_youtube(short_video, topic["title"], meta["description"], meta["tags"], is_short=True)

    print(f"\nDone! KaifiyatTV video published — {today}\n")

if __name__ == "__main__":
    run()

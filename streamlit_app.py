"""WaqasYtdownloader - Streamlit version. Link paste karo, format chuno, download karo."""
import os
import shutil
import tempfile
from urllib.parse import urlparse

import streamlit as st
import yt_dlp

ALLOWED_HOSTS = {
    "youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be",
    "music.youtube.com",
    "instagram.com", "www.instagram.com",
    "tiktok.com", "www.tiktok.com", "vm.tiktok.com", "vt.tiktok.com",
    "facebook.com", "www.facebook.com", "m.facebook.com", "fb.watch",
    "x.com", "www.x.com", "twitter.com", "www.twitter.com", "mobile.twitter.com",
    "vimeo.com", "www.vimeo.com",
    "dailymotion.com", "www.dailymotion.com",
    "soundcloud.com", "www.soundcloud.com",
}
MAX_DURATION = 60 * 60       # 60 min
MAX_FILE_MB = 250            # Streamlit Cloud has 1 GB RAM


def valid_url(url: str) -> bool:
    try:
        p = urlparse(url.strip())
    except Exception:
        return False
    if p.scheme not in ("http", "https"):
        return False
    return (p.hostname or "").lower() in ALLOWED_HOSTS


def fmt_duration(sec):
    if not sec:
        return ""
    sec = int(sec)
    h, r = divmod(sec, 3600)
    m, s = divmod(r, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def build_options(info):
    opts = [{"label": "Best quality", "spec": "best", "kind": "video"}]
    seen = set()
    for f in sorted(info.get("formats") or [], key=lambda x: (x.get("height") or 0), reverse=True):
        if f.get("vcodec") in (None, "none") or f.get("acodec") in (None, "none"):
            continue
        h = f.get("height")
        if not h or h in seen:
            continue
        seen.add(h)
        opts.append({"label": f"{h}p Video", "spec": f"bestvideo[height<={h}]+bestaudio/best[height<={h}]/best",
                     "kind": "video"})
        if len(opts) >= 6:
            break
    opts.append({"label": "Audio only (MP3)", "spec": "bestaudio/best", "kind": "audio"})
    return opts


st.set_page_config(page_title="WaqasYtdownloader", page_icon="⚡", layout="centered")
st.title("⚡ WaqasYtdownloader")
st.caption("Link paste karo, format chuno, download karo — bilkul free")

url = st.text_input("Video ka link", placeholder="https://youtube.com/watch?v=...")

if st.button("Fetch", type="primary"):
    st.session_state.pop("info", None)
    st.session_state.pop("dl", None)
    if not url or not valid_url(url):
        st.error("Ye link supported nahi hai.")
    else:
        with st.spinner("Link read ho raha hai..."):
            try:
                with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True,
                                       "noplaylist": True, "socket_timeout": 20}) as ydl:
                    info = ydl.extract_info(url.strip(), download=False)
                if (info.get("duration") or 0) > MAX_DURATION:
                    st.error("Video 60 minute se lambi hai, allow nahi.")
                else:
                    st.session_state["info"] = {
                        "title": info.get("title"),
                        "uploader": info.get("uploader"),
                        "thumbnail": info.get("thumbnail"),
                        "duration": fmt_duration(info.get("duration")),
                        "page_url": info.get("webpage_url") or url.strip(),
                        "options": build_options(info),
                    }
            except Exception as e:
                st.error(f"Link read nahi ho saka: {e}")

info = st.session_state.get("info")
if info:
    if info.get("thumbnail"):
        st.image(info["thumbnail"], use_container_width=True)
    st.subheader(info.get("title") or "")
    meta = " • ".join(x for x in [info.get("uploader"), info.get("duration")] if x)
    if meta:
        st.caption(meta)
    labels = [o["label"] for o in info["options"]]
    choice = st.selectbox("Format chuno", labels)
    opt = next(o for o in info["options"] if o["label"] == choice)

    if st.button("⬇ Download tayar karo"):
        st.session_state.pop("dl", None)
        tmpdir = tempfile.mkdtemp(prefix="wqd_")
        progress = st.progress(0, text="Download ho raha hai...")

        def hook(d):
            if d.get("status") == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate")
                done = d.get("downloaded_bytes") or 0
                if total:
                    progress.progress(min(done / total, 1.0), text="Download ho raha hai...")

        ydl_opts = {
            "quiet": True, "no_warnings": True, "noplaylist": True,
            "socket_timeout": 30,
            "outtmpl": os.path.join(tmpdir, "%(title).80s.%(ext)s"),
            "restrictfilenames": True,
            "progress_hooks": [hook],
            "format": opt["spec"],
        }
        if opt["kind"] == "audio":
            ydl_opts["postprocessors"] = [{"key": "FFmpegExtractAudio",
                                           "preferredcodec": "mp3", "preferredquality": "192"}]
        else:
            ydl_opts["merge_output_format"] = "mp4"
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.extract_info(info["page_url"], download=True)
            files = [os.path.join(tmpdir, f) for f in os.listdir(tmpdir)
                     if os.path.isfile(os.path.join(tmpdir, f))]
            if not files:
                st.error("Download fail ho gaya.")
            else:
                fp = files[0]
                size_mb = os.path.getsize(fp) / (1024 * 1024)
                if size_mb > MAX_FILE_MB:
                    st.error(f"File bari hai ({size_mb:.0f} MB), free server pe allow nahi.")
                else:
                    with open(fp, "rb") as fh:
                        st.session_state["dl"] = {"name": os.path.basename(fp), "data": fh.read()}
                    st.success("Tayar hai! Neeche button dabao.")
        except Exception as e:
            st.error(f"Download fail: {e}")
        finally:
            progress.empty()
            shutil.rmtree(tmpdir, ignore_errors=True)

dl = st.session_state.get("dl")
if dl:
    st.download_button("⬇ Download file", data=dl["data"],
                       file_name=dl["name"], mime="application/octet-stream",
                       type="primary")

st.divider()
st.caption("Sirf apne ya copyright-free content ke liye use karein.")

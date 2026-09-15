# api.py
import threading
from flask import Flask, request, jsonify
import yt_dlp
from waitress import serve
import instaloader

app = Flask(__name__)

def _extract_instagram_shortcode(url: str) -> str:
    if '/p/' in url:
        return url.split('/p/')[1].split('/')[0].split('?')[0].split('&')[0]
    elif '/reel/' in url:
        return url.split('/reel/')[1].split('/')[0].split('?')[0].split('&')[0]
    elif '/reels/' in url:
        return url.split('/reels/')[1].split('/')[0].split('?')[0].split('&')[0]
    return None

@app.route('/api/extract', methods=['POST'])
def extract_media():
    """هذا المسار يتصل به تطبيق VidVibe لاستخراج الفيديوهات"""
    try:
        data = request.get_json()
        url = data.get("url")
        
        if not url:
            return jsonify({"status": "error", "text": "URL is required"}), 400

        # ✅ مسار مخصص لإنستجرام لحل مشكلة No video formats found ودعم الكاروسيل
        if 'instagram.com' in url and any(seg in url for seg in ('/p/', '/reel/', '/reels/')):
            shortcode = _extract_instagram_shortcode(url)
            if shortcode:
                try:
                    L = instaloader.Instaloader(quiet=True, max_connection_attempts=1)
                    post = instaloader.Post.from_shortcode(L.context, shortcode)
                    if post.typename == 'GraphSidecar':
                        picker = []
                        for node in post.get_sidecar_nodes():
                            if node.is_video:
                                picker.append({"type": "video", "url": node.video_url, "thumb": node.display_url})
                            else:
                                picker.append({"type": "photo", "url": node.display_url, "thumb": node.display_url})
                        return jsonify({"status": "picker", "picker": picker}), 200
                    else:
                        is_video = post.is_video
                        media_url = post.video_url if is_video else post.url
                        ext = "mp4" if is_video else "jpg"
                        return jsonify({
                            "status": "success",
                            "url": media_url,
                            "filename": f"instagram_media_{shortcode}.{ext}",
                            "text": "تم استخراج الميديا بنجاح"
                        }), 200
                except Exception as e:
                    # ✅ Fallback: Try public Cobalt instances for Instagram to bypass blocks
                    import urllib.request
                    import json
                    instances = ["https://co.wuk.sh/api/json", "https://cobalt.kwiatekm.cc/api/json"]
                    for inst in instances:
                        try:
                            req = urllib.request.Request(inst)
                            req.add_header('Accept', 'application/json')
                            req.add_header('Content-Type', 'application/json')
                            req.add_header('User-Agent', 'Mozilla/5.0')
                            payload = json.dumps({"url": url}).encode('utf-8')
                            resp = urllib.request.urlopen(req, data=payload, timeout=8)
                            cobalt_data = json.loads(resp.read().decode('utf-8'))
                            
                            if cobalt_data.get("status") == "picker":
                                return jsonify({"status": "picker", "picker": cobalt_data.get("picker")}), 200
                            elif cobalt_data.get("status") in ["stream", "redirect"]:
                                return jsonify({
                                    "status": "success",
                                    "url": cobalt_data.get("url"),
                                    "filename": f"instagram_media_{shortcode}.mp4",
                                    "text": "تم استخراج الميديا بنجاح"
                                }), 200
                        except:
                            continue
                    
                    pass # Fallback to yt-dlp if everything else fails

        # إعدادات الاستخراج لتناسب معظم المواقع
        ydl_opts = {
            'format': 'best',
            'quiet': True,
            'no_warnings': True,
            # 'cookiefile': 'cookies.txt', # (اختياري) يمكنك تفعيله إذا أضفت ملف كوكيز لتخطي حماية تيك توك/يوتيوب
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36'
            },
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # استخدام download=False للحصول على المعلومات فقط
            info = ydl.extract_info(url, download=False)
            
            # ترتيب البيانات لتتطابق مع ما يتوقعه تطبيق VidVibe (CobaltResponse)
            direct_url = info.get("url") or (info.get("urls")[0] if info.get("urls") else "")
            
            response_data = {
                "status": "success",
                "url": direct_url,
                "filename": f"{info.get('title', 'video')}.mp4",
                "text": info.get("title", "تم استخراج الفيديو بنجاح")
            }
            return jsonify(response_data), 200

    except Exception as e:
        return jsonify({"status": "error", "text": str(e)}), 500

@app.route('/')
def health_check():
    return jsonify({"status": "Online", "service": "VidVibe Backend + Telegram Bot"})

def run_server():
    # تشغيل السيرفر على البورت 9123 باستخدام Waitress (Production Server)
    serve(app, host="0.0.0.0", port=9123, threads=8)

def start_api_server_background():
    """تشغيل الفلاسك في الخلفية لكي لا يوقف عمل بوت التيليجرام"""
    server_thread = threading.Thread(target=run_server)
    server_thread.daemon = True
    server_thread.start()
    print("[API] 🌐 Flask API server started in background on port 9123")

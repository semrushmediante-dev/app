import os
import json
import uuid
import threading
import traceback
import multiprocessing
from datetime import datetime
from flask import Flask, jsonify, request, send_file
from flask_cors import CORS

# ─── Todo el cache en la carpeta del proyecto ─────────────────────────────────
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_CACHE    = os.path.join(_BASE_DIR, "whisper_cache")
os.makedirs(_CACHE, exist_ok=True)

os.environ["HF_HOME"]                          = _CACHE
os.environ["HF_HUB_CACHE"]                    = _CACHE
os.environ["HUGGINGFACE_HUB_CACHE"]           = _CACHE
os.environ["XDG_CACHE_HOME"]                  = _CACHE
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["HF_HUB_DISABLE_TELEMETRY"]        = "1"
os.environ["HF_HUB_DISABLE_IMPLICIT_TOKEN"]   = "1"
os.environ["HF_HUB_VERBOSITY"]                = "warning"
os.environ["HF_HUB_DISABLE_PROGRESS_BARS"]    = "1"
os.environ["TOKENIZERS_PARALLELISM"]           = "false"
os.environ["TRANSFORMERS_VERBOSITY"]           = "error"

# ─── TOKEN DE HUGGINGFACE (necesario para diarización) ────────────────────────
HF_TOKEN = "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"

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

TRANSCRIPCIONES_FILE = os.path.join(_BASE_DIR, 'transcripciones.json')
UPLOADS_DIR          = os.path.join(_BASE_DIR, 'whisper_uploads')
OUTPUTS_DIR          = os.path.join(_BASE_DIR, 'whisper_outputs')
MODELS_DIR           = os.path.join(_BASE_DIR, 'whisper_models')

for d in (UPLOADS_DIR, OUTPUTS_DIR, MODELS_DIR):
    os.makedirs(d, exist_ok=True)

jobs = {}

# ─── Persistencia ─────────────────────────────────────────────────────────────

def load_transcripciones():
    try:
        if os.path.exists(TRANSCRIPCIONES_FILE):
            with open(TRANSCRIPCIONES_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception:
        pass
    return []

def save_transcripciones(data):
    with open(TRANSCRIPCIONES_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ─── Conversión de audio ──────────────────────────────────────────────────────

def convert_to_wav(src, dst):
    import shutil
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        try:
            import imageio_ffmpeg
            ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        except Exception:
            pass
    if not ffmpeg:
        return False
    try:
        import subprocess
        cmd = [ffmpeg, "-y", "-i", src, "-ar", "16000", "-ac", "1", "-sample_fmt", "s16", dst]
        result = subprocess.run(cmd, capture_output=True)
        return result.returncode == 0 and os.path.exists(dst)
    except Exception as e:
        print(f"[whisper] conversión falló ({e}), usando archivo original")
        return False

# ─── Formatear resultado con hablantes ────────────────────────────────────────

def format_with_speakers(segments):
    """Convierte segmentos con hablantes en texto formateado."""
    lines = []
    current_speaker = None
    current_text = []

    for seg in segments:
        speaker = seg.get('speaker', 'HABLANTE')
        text    = seg.get('text', '').strip()
        if not text:
            continue
        if speaker != current_speaker:
            if current_text:
                lines.append(f"[{current_speaker}]: {' '.join(current_text)}")
            current_speaker = speaker
            current_text = [text]
        else:
            current_text.append(text)

    if current_text:
        lines.append(f"[{current_speaker}]: {' '.join(current_text)}")

    return "\n\n".join(lines)

# ─── Worker ───────────────────────────────────────────────────────────────────

def run_transcription(job_id, filepath, language, model_name):
    try:
        jobs[job_id]['status']   = 'converting'
        jobs[job_id]['progress'] = 10

        wav_path    = os.path.join(UPLOADS_DIR, f"{job_id}.wav")
        converted   = convert_to_wav(filepath, wav_path)
        audio_input = wav_path if converted else filepath

        jobs[job_id]['status']   = 'transcribing'
        jobs[job_id]['progress'] = 20

        import whisperx
        import torch

        cpu_cores = multiprocessing.cpu_count()
        device    = "cpu"
        print(f"[whisper] CPU cores: {cpu_cores} | modelo: {model_name} | WhisperX")

        # 1. Transcribir
        jobs[job_id]['progress'] = 25
        print("[whisper] Cargando modelo de transcripción...")
        model = whisperx.load_model(
            model_name,
            device,
            compute_type="int8",
            language=None if language == 'auto' else language,
            download_root=MODELS_DIR,
        )

        # WhisperX llama a "ffmpeg" hardcodeado — parcheamos su módulo
        # para que use la ruta completa del ffmpeg de imageio_ffmpeg
        import shutil
        import whisperx.audio as _waudio

        ffmpeg_exe = shutil.which("ffmpeg")
        if not ffmpeg_exe:
            try:
                import imageio_ffmpeg
                ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
            except Exception:
                ffmpeg_exe = None

        if ffmpeg_exe:
            # Parchear la constante FFMPEG_PATH en el módulo de whisperx
            _waudio.FFMPEG = ffmpeg_exe
            # También parchear directamente la función load_audio
            _orig_load = _waudio.load_audio
            def _patched_load(file, sr=16000):
                import numpy as np
                import subprocess
                cmd = [ffmpeg_exe, "-nostdin", "-threads", "0", "-i", file,
                       "-f", "s16le", "-ac", "1", "-acodec", "pcm_s16le",
                       "-ar", str(sr), "-"]
                out = subprocess.run(cmd, capture_output=True, check=True).stdout
                return np.frombuffer(out, np.int16).flatten().astype(np.float32) / 32768.0
            _waudio.load_audio = _patched_load
            whisperx.load_audio = _patched_load

        audio = whisperx.load_audio(audio_input)
        jobs[job_id]['progress'] = 35
        print("[whisper] Transcribiendo...")

        result = model.transcribe(
            audio,
            batch_size=8,
            language=None if language == 'auto' else language,
        )
        detected_language = result.get("language", language)
        print(f"[whisper] Idioma detectado: {detected_language}")

        # Liberar memoria
        import gc
        del model
        gc.collect()

        # 2. Alinear
        jobs[job_id]['progress'] = 55
        print("[whisper] Alineando palabras...")
        try:
            model_a, metadata = whisperx.load_align_model(
                language_code=detected_language,
                device=device,
                model_dir=MODELS_DIR,
            )
            result = whisperx.align(
                result["segments"], model_a, metadata, audio, device,
                return_char_alignments=False,
            )
            del model_a
            gc.collect()
        except Exception as e:
            print(f"[whisper] Alineación falló ({e}), continuando sin alineación")

        # 3. Diarización (detección de hablantes)
        jobs[job_id]['progress'] = 70
        print("[whisper] Detectando hablantes...")
        try:
            diarize_model = whisperx.DiarizationPipeline(
                use_auth_token=HF_TOKEN,
                device=device,
            )
            diarize_segments = diarize_model(audio)
            result = whisperx.assign_word_speakers(diarize_segments, result)
            del diarize_model
            gc.collect()
            has_speakers = True
        except Exception as e:
            print(f"[whisper] Diarización falló ({e}), sin etiquetas de hablante")
            has_speakers = False

        jobs[job_id]['progress'] = 90

        # 4. Formatear texto
        if has_speakers:
            text = format_with_speakers(result["segments"])
        else:
            text = "\n".join(
                seg.get('text', '').strip()
                for seg in result["segments"]
                if seg.get('text', '').strip()
            )

        if not text:
            raise Exception('No se obtuvo texto. Comprueba que el audio tenga voz audible.')

        # 5. Guardar
        txt_path = os.path.join(OUTPUTS_DIR, f"{job_id}.txt")
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(text)

        historial = load_transcripciones()
        entry = {
            'id':           job_id,
            'filename':     jobs[job_id]['filename'],
            'language':     detected_language,
            'model':        model_name,
            'text':         text,
            'chars':        len(text),
            'words':        len(text.split()),
            'has_speakers': has_speakers,
            'fecha':        datetime.now().strftime('%Y-%m-%d %H:%M'),
            'txt_path':     txt_path,
        }
        historial.insert(0, entry)
        save_transcripciones(historial[:50])

        jobs[job_id].update({
            'status':       'done',
            'progress':     100,
            'text':         text,
            'words':        entry['words'],
            'chars':        entry['chars'],
            'has_speakers': has_speakers,
            'txt_path':     txt_path,
            'model':        model_name,
            'language':     detected_language,
        })

        for p in [filepath, wav_path]:
            try:
                if os.path.exists(p):
                    os.remove(p)
            except Exception:
                pass

        print(f"[whisper] ✅ Completado — {entry['words']} palabras | hablantes: {has_speakers}")

    except Exception as e:
        jobs[job_id]['status'] = 'error'
        jobs[job_id]['error']  = str(e)
        print(f"[whisper] ERROR job {job_id}:\n{traceback.format_exc()}")
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
        except Exception:
            pass

# ─── Rutas ────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return app.send_static_file('indexWhisper.html')

@app.route('/api/transcribe', methods=['POST'])
def transcribe():
    try:
        if 'audio' not in request.files:
            return jsonify({'success': False, 'error': 'No se recibió archivo'}), 400

        file       = request.files['audio']
        language   = request.form.get('language', 'auto')
        model_name = request.form.get('model', 'small')

        if not file.filename:
            return jsonify({'success': False, 'error': 'Nombre de archivo vacío'}), 400

        job_id    = str(uuid.uuid4())[:8]
        ext       = os.path.splitext(file.filename)[1].lower()
        save_path = os.path.join(UPLOADS_DIR, f"{job_id}{ext}")
        file.save(save_path)

        jobs[job_id] = {
            'status':   'queued',
            'progress': 0,
            'filename': file.filename,
            'language': language,
            'model':    model_name,
            'text':     None,
            'error':    None,
        }

        threading.Thread(
            target=run_transcription,
            args=(job_id, save_path, language, model_name),
            daemon=True,
        ).start()

        return jsonify({'success': True, 'job_id': job_id})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/status/<job_id>', methods=['GET'])
def status(job_id):
    job = jobs.get(job_id)
    if not job:
        return jsonify({'success': False, 'error': 'Job no encontrado'}), 404
    return jsonify({'success': True, **job})

@app.route('/api/download/<job_id>', methods=['GET'])
def download(job_id):
    job      = jobs.get(job_id)
    txt_path = job.get('txt_path') if job else None

    if not txt_path:
        entry = next((h for h in load_transcripciones() if h['id'] == job_id), None)
        if not entry:
            return jsonify({'success': False, 'error': 'Archivo no encontrado'}), 404
        txt_path = entry['txt_path']

    if not os.path.exists(txt_path):
        return jsonify({'success': False, 'error': 'Archivo no encontrado en disco'}), 404

    return send_file(txt_path, as_attachment=True, mimetype='text/plain',
                     download_name=f"transcripcion_{job_id}.txt")

@app.route('/api/history', methods=['GET'])
def history():
    return jsonify({'success': True, 'history': load_transcripciones()})

@app.route('/api/history/<job_id>', methods=['DELETE'])
def delete_history(job_id):
    historial = [h for h in load_transcripciones() if h['id'] != job_id]
    save_transcripciones(historial)
    return jsonify({'success': True})

@app.route('/api/clear-history', methods=['DELETE'])
def clear_history():
    save_transcripciones([])
    return jsonify({'success': True})

if __name__ == '__main__':
    print("\n🎙️  Servidor WhisperX con detección de hablantes")
    print(f"💻  CPU cores: {multiprocessing.cpu_count()}")
    print(f"📁  Modelos en: {MODELS_DIR}")
    print(f"🔑  HF Token: {'configurado' if HF_TOKEN != 'REEMPLAZA_CON_TU_TOKEN' else '⚠️ NO CONFIGURADO'}")
    print("📝  Abre http://localhost:7861 en tu navegador\n")
    app.run(debug=False, host='0.0.0.0', port=7861)
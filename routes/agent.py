from flask import Blueprint, jsonify, render_template, request, session

bp = Blueprint('agent', __name__)


@bp.route('/')
def index():
    return render_template('agent/index.html')


@bp.route('/agent/historia')
def history():
    from models.agent_task import ENTITY_TYPE_LABELS, INTENT_LABELS, get_tasks
    return render_template('agent/history.html', tasks=get_tasks(),
                           entity_type_labels=ENTITY_TYPE_LABELS, intent_labels=INTENT_LABELS)


@bp.route('/api/agent/transcribe', methods=['POST'])
def api_agent_transcribe():
    from models.settings import get_setting
    from services.gemini_ocr import transcribe_audio

    audio_file = request.files.get('audio')
    if not audio_file or not audio_file.filename:
        return jsonify({'status': 'error', 'message': 'Brak nagrania.'})
    audio_bytes = audio_file.read()
    if not audio_bytes:
        return jsonify({'status': 'error', 'message': 'Puste nagranie.'})

    api_key = get_setting('gemini_api_key', '')
    model = get_setting('gemini_model', 'gemini-2.5-flash')
    if not api_key:
        return jsonify({'status': 'error', 'message': 'Brak klucza API Gemini (Ustawienia → Integracje).'})

    result = transcribe_audio(audio_bytes, audio_file.mimetype or 'audio/webm', api_key, model=model)
    if 'error' in result:
        return jsonify({'status': 'error', 'message': result['error']})
    return jsonify({'status': 'ok', 'text': result['text']})


@bp.route('/api/agent/parse', methods=['POST'])
def api_agent_parse():
    from models.settings import get_setting
    from services.agent_resolver import resolve_intent
    from services.gemini_agent import parse_command

    data = request.get_json(silent=True) or {}
    text = (data.get('text') or '').strip()
    if not text:
        return jsonify({'status': 'error', 'message': 'Brak treści polecenia.'})

    api_key = get_setting('gemini_api_key', '')
    model = get_setting('gemini_model', 'gemini-2.5-flash')
    if not api_key:
        return jsonify({'status': 'error', 'message': 'Brak klucza API Gemini (Ustawienia → Integracje).'})

    parsed = parse_command(text, api_key, model=model)
    if 'error' in parsed:
        return jsonify({'status': 'error', 'message': parsed['error']})

    resolved = resolve_intent(parsed)
    resolved['input_text'] = text
    return jsonify({'status': 'ok', 'result': resolved})


@bp.route('/api/agent/execute', methods=['POST'])
def api_agent_execute():
    from services.agent_resolver import execute_action

    payload = request.get_json(silent=True) or {}
    try:
        result = execute_action(payload, session.get('user_id'))
    except ValueError as e:
        return jsonify({'status': 'error', 'message': str(e)})
    return jsonify({'status': 'ok', **result})

// AI-18: offline voice for any page. Whisper hears and Piper speaks on this PC; the audio is never stored or sent anywhere.
// The microphone is on only while listening, which ends by itself after a short pause, on stop(), or after 30 seconds.
window.AlfredVoice = (() => {
    // Browser noise suppression leaves a room near 0.005 RMS; quiet speech is above 0.015.
    const SPEECH_RMS = 0.015, CHUNK = 4096, PAUSE_CHUNKS = 5, NOTHING_HEARD_MS = 8000, MAX_MS = 30000, PIECE = 580;  // 5 chunks ≈ 1.3 s at 16 kHz
    let state = null, player = null, recording = null;

    function status() {
        state = state || Alfred.fetchJSON("/api/ai/speech/status/").catch(() => ({listen: false, speak: false}));
        return state;
    }

    // The offline voice reads up to 600 characters at a time; split at sentence ends so each piece sounds whole.
    function pieces(text) {
        const out = [];
        let current = "";
        for (const sentence of String(text || "").replace(/\s+/g, " ").match(/[^.!?]+[.!?]*\s*/g) || []) {
            if (current && (current + sentence).length > PIECE) { out.push(current.trim()); current = ""; }
            current += sentence.slice(0, PIECE);
        }
        if (current.trim()) out.push(current.trim());
        return out;
    }

    async function audio(text) {
        const response = await fetch("/api/ai/speech/speak/", {method: "POST", credentials: "same-origin",
            headers: {"Content-Type": "application/json", "X-CSRFToken": getCookie("csrftoken")}, body: JSON.stringify({text})});
        if (!response.ok) throw new Error((await response.json().catch(() => ({}))).detail || "The offline voice could not read this.");
        return response.arrayBuffer();
    }

    function stopSpeaking() {
        if (player) { player.close().catch(() => {}); player = null; }
    }

    // Resolves when everything was read, or early when stopped. The next piece is made while the current one plays.
    async function speak(text) {
        stopSpeaking();
        const parts = pieces(text);
        if (!parts.length) return;
        // Web Audio plays the WAV without a blob: URL, which the page's Content Security Policy blocks.
        const context = player = new AudioContext();
        let next = audio(parts[0]);
        for (let index = 0; index < parts.length; index++) {
            const data = await next;
            if (index + 1 < parts.length) next = audio(parts[index + 1]);
            if (player !== context) return;
            const sound = context.createBufferSource();
            sound.buffer = await context.decodeAudioData(data);
            sound.connect(context.destination);
            await new Promise(resolve => { sound.onended = resolve; sound.start(); });
            if (player !== context) return;
        }
        stopSpeaking();
    }

    function wav16k(chunks, rate) {
        const total = chunks.reduce((sum, chunk) => sum + chunk.length, 0), input = new Float32Array(total);
        let at = 0; chunks.forEach(chunk => { input.set(chunk, at); at += chunk.length; });
        const length = Math.floor(total * 16000 / rate), view = new DataView(new ArrayBuffer(44 + length * 2));
        const tag = (offset, value) => [...value].forEach((char, index) => view.setUint8(offset + index, char.charCodeAt(0)));
        tag(0, "RIFF"); view.setUint32(4, 36 + length * 2, true); tag(8, "WAVE"); tag(12, "fmt "); view.setUint32(16, 16, true);
        view.setUint16(20, 1, true); view.setUint16(22, 1, true); view.setUint32(24, 16000, true); view.setUint32(28, 32000, true);
        view.setUint16(32, 2, true); view.setUint16(34, 16, true); tag(36, "data"); view.setUint32(40, length * 2, true);
        // Fallback only when the browser refuses a 16 kHz context: nearest-sample downsampling.
        for (let i = 0; i < length; i++) view.setInt16(44 + i * 2, Math.max(-1, Math.min(1, input[Math.floor(i * rate / 16000)] || 0)) * 0x7fff, true);
        return new Blob([view], {type: "audio/wav"});
    }

    // Records until a pause after speech, stop(), or the time limit, then returns the words ("" when nothing was said).
    // onStage("listening" | "transcribing") lets the page show what is happening.
    async function listen(onStage = () => {}) {
        stopSpeaking();
        // The browser's own free noise suppression and echo cancellation clean the voice before Whisper hears it.
        const stream = await navigator.mediaDevices.getUserMedia({audio: {channelCount: 1, noiseSuppression: true, echoCancellation: true, autoGainControl: true}});
        // A 16 kHz context lets the browser resample with filtering; naive downsampling garbled words.
        let context; try { context = new AudioContext({sampleRate: 16000}); } catch { context = new AudioContext(); }
        const source = context.createMediaStreamSource(stream), processor = context.createScriptProcessor(CHUNK, 1, 1), chunks = [];
        let heard = false, quiet = 0, finish;
        const done = new Promise(resolve => { finish = resolve; });
        processor.onaudioprocess = event => {
            const samples = new Float32Array(event.inputBuffer.getChannelData(0));
            chunks.push(samples);
            const level = Math.sqrt(samples.reduce((sum, value) => sum + value * value, 0) / samples.length);
            if (level > SPEECH_RMS) { heard = true; quiet = 0; } else if (heard && ++quiet >= PAUSE_CHUNKS) finish("pause");
        };
        source.connect(processor); processor.connect(context.destination); await context.resume();
        const current = recording = {finish};
        const limits = [setTimeout(() => finish("limit"), MAX_MS), setTimeout(() => { if (!heard) finish("silence"); }, NOTHING_HEARD_MS)];
        onStage("listening");
        const reason = await done;
        limits.forEach(clearTimeout);
        if (recording === current) recording = null;
        stream.getTracks().forEach(track => track.stop());
        const rate = context.sampleRate; await context.close();
        if (reason === "silence") return "";
        onStage("transcribing");
        const result = await Alfred.fetchJSON("/api/ai/speech/transcribe/", {method: "POST", headers: {"Content-Type": "audio/wav"}, body: wav16k(chunks, rate)});
        return (result.text || "").trim();
    }

    return {
        status, speak, stopSpeaking, listen,
        get listening() { return Boolean(recording); },
        stop() { if (recording) recording.finish("stopped"); },
    };
})();

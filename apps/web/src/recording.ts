export type Recording = { finish: () => Promise<string>; cancel: () => Promise<void> };

export async function startRecording(onLimit: () => void): Promise<Recording> {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: { channelCount: 1 } });
  let context: AudioContext;
  try { context = new AudioContext({ sampleRate: 24000 }); }
  catch (error) { stream.getTracks().forEach(track => track.stop()); throw error; }
  const chunks: Float32Array[] = [];
  let count = 0;
  let closed = false;
  try {
    if (context.sampleRate !== 24000) throw new Error('Use text on this browser.');
    await context.audioWorklet.addModule(new URL('./recorder.worklet.js', import.meta.url));
    const source = context.createMediaStreamSource(stream);
    const node = new AudioWorkletNode(context, 'telecom-recorder');
    const silent = context.createGain(); silent.gain.value = 0;
    source.connect(node); node.connect(silent); silent.connect(context.destination);
    node.port.onmessage = (event: MessageEvent<Float32Array>) => {
      if (closed) return;
      const remaining = 24000 * 15 - count;
      if (remaining > 0) {
        const chunk = event.data.slice(0, remaining);
        chunks.push(chunk); count += chunk.length;
      }
    };
    const timer = setTimeout(onLimit, 15_000);
    async function close() {
      if (closed) return;
      closed = true; clearTimeout(timer); node.port.onmessage = null;
      source.disconnect(); node.disconnect(); silent.disconnect();
      stream.getTracks().forEach(track => track.stop());
      await context.close();
    }
    return {
      cancel: async () => { await close(); chunks.length = 0; },
      finish: async () => {
        await close();
        const bytes = new Uint8Array(count * 2); const view = new DataView(bytes.buffer);
        let position = 0;
        for (const chunk of chunks) for (const sample of chunk) {
          view.setInt16(position * 2, Math.round(Math.max(-1, Math.min(1, sample)) * 32767), true);
          position++;
        }
        chunks.length = 0;
        let binary = '';
        for (let index = 0; index < bytes.length; index += 8192) {
          binary += String.fromCharCode(...bytes.subarray(index, index + 8192));
        }
        return btoa(binary);
      },
    };
  } catch (error) {
    stream.getTracks().forEach(track => track.stop()); await context.close(); throw error;
  }
}

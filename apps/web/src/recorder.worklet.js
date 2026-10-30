/* global AudioWorkletProcessor, registerProcessor */
class Recorder extends AudioWorkletProcessor {
  process(inputs) {
    const samples = inputs[0]?.[0];
    if (samples) this.port.postMessage(samples.slice());
    return true;
  }
}
registerProcessor('telecom-recorder', Recorder);

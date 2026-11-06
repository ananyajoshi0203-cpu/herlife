/**
 * On-device speech seam for the Log screen. The web app sends audio nowhere and asks her
 * to type; on iPhone, Apple's recognizer can transcribe on the device, so a voice note
 * never leaves the phone as audio. Only the transcript goes to `POST /logs/voice`.
 */

export interface Dictation {
  isAvailable(): Promise<boolean>;
  /** Streams partial transcripts to `onText` until `stop` is called. */
  start(onText: (transcript: string) => void): Promise<void>;
  stop(): Promise<void>;
}

/**
 * TODO(speech): implement with expo-speech-recognition in a development build.
 * `npx expo install expo-speech-recognition`, add its config plugin with
 * NSSpeechRecognitionUsageDescription and NSMicrophoneUsageDescription copy, then start
 * with `requiresOnDeviceRecognition: true` and `interimResults: true`, forwarding each
 * "result" event's transcript to `onText`.
 */
export const dictation: Dictation = {
  isAvailable: async () => false,
  start: async () => {},
  stop: async () => {},
};

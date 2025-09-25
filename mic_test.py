import sounddevice as sd
from scipy.io.wavfile import write

# Aufnahme-Einstellungen
samplerate = 16000  # 16 kHz
seconds = 5  # 5 Sekunden aufnehmen
filename = "mic_test.wav"

print("Recording... 🎤")
recording = sd.rec(
    int(seconds * samplerate), samplerate=samplerate, channels=1, dtype="int16"
)
sd.wait()  # Aufnahme beenden
print("Recording finished, saved to", filename)

# Speichern als WAV
write(filename, samplerate, recording)

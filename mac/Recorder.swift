// Grava o áudio do sistema e o microfone em duas trilhas separadas (.m4a)
// usando ScreenCaptureKit. Nenhum bot entra na reunião: o áudio é capturado localmente.
//
// Uso: mac-recorder <pasta-de-saida>
// Para parar: Ctrl+C (SIGINT). Gera <pasta>/sistema.m4a e <pasta>/mic.m4a.

import AVFoundation
import CoreMedia
import Foundation
import ScreenCaptureKit

/// Escreve buffers de áudio num .m4a, preenchendo com silêncio os intervalos
/// em que nenhum buffer chegou, para manter as duas trilhas alinhadas no tempo.
final class TrackWriter {
    private let url: URL
    private let startTime: CMTime
    private var file: AVAudioFile?
    private var framesWritten: AVAudioFramePosition = 0
    /// Volume (RMS) do último buffer, para o medidor da interface.
    var level: Float = 0

    init(url: URL, startTime: CMTime) {
        self.url = url
        self.startTime = startTime
    }

    func append(_ sampleBuffer: CMSampleBuffer) {
        guard sampleBuffer.isValid, sampleBuffer.numSamples > 0,
              let desc = sampleBuffer.formatDescription else { return }
        let format = AVAudioFormat(cmAudioFormatDescription: desc)

        do {
            if file == nil {
                let settings: [String: Any] = [
                    AVFormatIDKey: kAudioFormatMPEG4AAC,
                    AVSampleRateKey: format.sampleRate,
                    AVNumberOfChannelsKey: format.channelCount,
                    AVEncoderBitRateKey: 64_000,
                ]
                file = try AVAudioFile(forWriting: url, settings: settings,
                                       commonFormat: format.commonFormat,
                                       interleaved: format.isInterleaved)
            }
            guard let file else { return }

            // Preenche com silêncio o tempo entre o início da gravação (ou o último buffer) e este buffer.
            let pts = sampleBuffer.presentationTimeStamp
            let expected = AVAudioFramePosition(CMTimeGetSeconds(CMTimeSubtract(pts, startTime)) * format.sampleRate)
            let gap = expected - framesWritten
            if gap > AVAudioFramePosition(format.sampleRate * 0.05) {
                try writeSilence(frames: gap, format: format, to: file)
            }

            try sampleBuffer.withAudioBufferList { abl, _ in
                guard let pcm = AVAudioPCMBuffer(pcmFormat: format, bufferListNoCopy: abl.unsafePointer) else { return }
                level = Self.rms(pcm)
                try file.write(from: pcm)
                framesWritten += AVAudioFramePosition(pcm.frameLength)
            }
        } catch {
            fputs("Error writing \(url.lastPathComponent): \(error)\n", stderr)
        }
    }

    private static func rms(_ pcm: AVAudioPCMBuffer) -> Float {
        guard let data = pcm.floatChannelData, pcm.frameLength > 0 else { return 0 }
        let n = Int(pcm.frameLength) * (pcm.format.isInterleaved ? Int(pcm.format.channelCount) : 1)
        var sum: Float = 0
        for i in 0..<n { sum += data[0][i] * data[0][i] }
        return (sum / Float(n)).squareRoot()
    }

    private func writeSilence(frames: AVAudioFramePosition, format: AVAudioFormat, to file: AVAudioFile) throws {
        var remaining = frames
        let chunk: AVAudioFrameCount = 16_384
        guard let silence = AVAudioPCMBuffer(pcmFormat: format, frameCapacity: chunk) else { return }
        // Buffers novos já vêm zerados.
        while remaining > 0 {
            let n = AVAudioFrameCount(min(AVAudioFramePosition(chunk), remaining))
            silence.frameLength = n
            try file.write(from: silence)
            remaining -= AVAudioFramePosition(n)
            framesWritten += AVAudioFramePosition(n)
        }
    }

    func close() {
        file = nil  // AVAudioFile finaliza o arquivo ao ser desalocado
    }
}

final class Recorder: NSObject, SCStreamOutput, SCStreamDelegate {
    private var stream: SCStream?
    private var system: TrackWriter!
    private var mic: TrackWriter!
    private let queue = DispatchQueue(label: "audio")

    func start(outputDir: URL) async throws {
        let content = try await SCShareableContent.excludingDesktopWindows(false, onScreenWindowsOnly: true)
        guard let display = content.displays.first else {
            throw NSError(domain: "Recorder", code: 1, userInfo: [NSLocalizedDescriptionKey: "No display found"])
        }
        let filter = SCContentFilter(display: display, excludingApplications: [], exceptingWindows: [])

        let config = SCStreamConfiguration()
        config.capturesAudio = true
        config.captureMicrophone = true
        config.excludesCurrentProcessAudio = true
        config.sampleRate = 48_000
        config.channelCount = 1
        // Só queremos áudio: vídeo mínimo e raro.
        config.width = 2
        config.height = 2
        config.minimumFrameInterval = CMTime(value: 1, timescale: 1)

        let startTime = CMClockGetTime(CMClockGetHostTimeClock())
        system = TrackWriter(url: outputDir.appendingPathComponent("sistema.m4a"), startTime: startTime)
        mic = TrackWriter(url: outputDir.appendingPathComponent("mic.m4a"), startTime: startTime)

        let stream = SCStream(filter: filter, configuration: config, delegate: self)
        try stream.addStreamOutput(self, type: .screen, sampleHandlerQueue: queue)
        try stream.addStreamOutput(self, type: .audio, sampleHandlerQueue: queue)
        try stream.addStreamOutput(self, type: .microphone, sampleHandlerQueue: queue)
        try await stream.startCapture()
        self.stream = stream
    }

    var levels: (system: Float, mic: Float) {
        // Zera após ler: se nenhum buffer chegar até a próxima leitura, o medidor cai para zero.
        queue.sync {
            defer { system.level = 0; mic.level = 0 }
            return (system.level, mic.level)
        }
    }

    func stop() async {
        try? await stream?.stopCapture()
        queue.sync {
            system.close()
            mic.close()
        }
    }

    func stream(_ stream: SCStream, didOutputSampleBuffer sampleBuffer: CMSampleBuffer, of type: SCStreamOutputType) {
        switch type {
        case .audio: system.append(sampleBuffer)
        case .microphone: mic.append(sampleBuffer)
        default: break
        }
    }

    func stream(_ stream: SCStream, didStopWithError error: Error) {
        fputs("Capture stopped: \(error.localizedDescription)\n", stderr)
        exit(1)
    }
}

@main
struct Main {
    static func main() async {
        guard CommandLine.arguments.count == 2 else {
            fputs("Usage: mac-recorder <output-folder>\n", stderr)
            exit(2)
        }
        let outputDir = URL(fileURLWithPath: CommandLine.arguments[1])
        try? FileManager.default.createDirectory(at: outputDir, withIntermediateDirectories: true)

        let recorder = Recorder()
        do {
            try await recorder.start(outputDir: outputDir)
        } catch {
            // A primeira linha é mostrada na interface (traduzida pelo Python); a segunda ajuda no terminal.
            fputs("\(error.localizedDescription)\n", stderr)
            fputs("Allow Psiu (or your terminal) in System Settings > Privacy & Security > Screen & System Audio Recording and Microphone, then reopen it.\n", stderr)
            exit(1)
        }
        print("GRAVANDO", terminator: "\n")
        fflush(stdout)

        // Informa o volume de cada trilha várias vezes por segundo: "NIVEL <sistema> <mic>".
        let meter = DispatchSource.makeTimerSource(queue: .main)
        meter.schedule(deadline: .now(), repeating: .milliseconds(150))
        meter.setEventHandler {
            let (system, mic) = recorder.levels
            print("NIVEL \(system) \(mic)")
            fflush(stdout)
        }
        meter.resume()

        // Espera SIGINT (Ctrl+C ou enviado pelo script Python) para finalizar os arquivos corretamente.
        signal(SIGINT, SIG_IGN)
        await withCheckedContinuation { (cont: CheckedContinuation<Void, Never>) in
            let source = DispatchSource.makeSignalSource(signal: SIGINT, queue: .main)
            source.setEventHandler {
                source.cancel()
                cont.resume()
            }
            source.resume()
            sigintSource = source
        }
        meter.cancel()
        await recorder.stop()
        print("PARADO")
    }
}

nonisolated(unsafe) var sigintSource: DispatchSourceSignal?

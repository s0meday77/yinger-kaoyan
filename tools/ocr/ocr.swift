import Foundation
import Vision
import AppKit

// 用 macOS Vision 引擎识别印刷体英文单词，输出带坐标的 JSON
func ocr(_ path: String) -> [[String: Any]] {
    guard let img = NSImage(contentsOfFile: path),
          let cg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) else {
        return []
    }
    let req = VNRecognizeTextRequest()
    req.recognitionLevel = .accurate
    req.recognitionLanguages = ["en-US"]
    req.usesLanguageCorrection = false   // 词表不要被"自动纠正"成常用词
    let handler = VNImageRequestHandler(cgImage: cg, options: [:])
    do { try handler.perform([req]) } catch { return [] }
    var out: [[String: Any]] = []
    for obs in (req.results ?? []) {
        guard let top = obs.topCandidates(1).first else { continue }
        let b = obs.boundingBox
        out.append([
            "text": top.string,
            "conf": Double(top.confidence),
            "x": Double(b.minX), "y": Double(b.minY),
            "w": Double(b.width), "h": Double(b.height)
        ])
    }
    return out
}

let args = Array(CommandLine.arguments.dropFirst())
var result: [String: Any] = [:]
for p in args {
    result[p] = ocr(p)
}
if let data = try? JSONSerialization.data(withJSONObject: result, options: []),
   let s = String(data: data, encoding: .utf8) {
    print(s)
}

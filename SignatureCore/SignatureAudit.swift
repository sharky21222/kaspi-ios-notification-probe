import Foundation

enum SignatureAudit {
    enum AuditError: Error { case malformed, unsigned, unsupported }

    static func entitlements(in data: Data) throws -> [String: Any] {
        func number(_ offset: Int, bigEndian: Bool = false) throws -> Int {
            guard offset >= 0, offset <= data.count - 4 else { throw AuditError.malformed }
            let bytes = Array(data[offset..<(offset + 4)])
            let ordered = bigEndian ? bytes : Array(bytes.reversed())
            return ordered.reduce(0) { ($0 << 8) | Int($1) }
        }
        guard try number(0) == 0xfeedfacf else { throw AuditError.unsupported }
        let commands = try number(16)
        guard commands <= 4096 else { throw AuditError.malformed }
        var offset = 32
        for _ in 0..<commands {
            let command = try number(offset)
            let length = try number(offset + 4)
            guard length >= 8, offset <= data.count - length else { throw AuditError.malformed }
            if command == 0x1d {
                guard length >= 16 else { throw AuditError.malformed }
                let start = try number(offset + 8)
                let size = try number(offset + 12)
                guard size >= 12, start <= data.count - size,
                      try number(start, bigEndian: true) == 0xfade0cc0 else { throw AuditError.malformed }
                let count = try number(start + 8, bigEndian: true)
                guard count <= (size - 12) / 8 else { throw AuditError.malformed }
                for index in 0..<count {
                    let entry = start + 12 + index * 8
                    if try number(entry, bigEndian: true) != 5 { continue }
                    let relative = try number(entry + 4, bigEndian: true)
                    guard relative >= 12, relative <= size - 8 else { throw AuditError.malformed }
                    let blob = start + relative
                    let blobSize = try number(blob + 4, bigEndian: true)
                    guard try number(blob, bigEndian: true) == 0xfade7171,
                          blobSize >= 8, blobSize <= size - relative else { throw AuditError.malformed }
                    let xml = data.subdata(in: (blob + 8)..<(blob + blobSize))
                    guard let values = try PropertyListSerialization.propertyList(from: xml, format: nil) as? [String: Any] else {
                        throw AuditError.malformed
                    }
                    return values
                }
                throw AuditError.unsupported
            }
            offset += length
        }
        throw AuditError.unsigned
    }
}

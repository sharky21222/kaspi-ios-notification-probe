import Foundation

func word(_ value: UInt32, bigEndian: Bool = false) -> Data {
    var raw = bigEndian ? value.bigEndian : value.littleEndian
    return withUnsafeBytes(of: &raw) { Data($0) }
}

let key = "com.apple.developer.accessory-data-provider"
let xml = try PropertyListSerialization.data(fromPropertyList: [key: true], format: .xml, options: 0)
let entitlement = word(0xfade7171, bigEndian: true) + word(UInt32(xml.count + 8), bigEndian: true) + xml
let superblob = word(0xfade0cc0, bigEndian: true) + word(UInt32(entitlement.count + 20), bigEndian: true)
    + word(1, bigEndian: true) + word(5, bigEndian: true) + word(20, bigEndian: true) + entitlement
var header = Data(repeating: 0, count: 32)
header.replaceSubrange(0..<4, with: word(0xfeedfacf))
header.replaceSubrange(16..<20, with: word(1))
let binary = header + word(0x1d) + word(16) + word(48) + word(UInt32(superblob.count)) + superblob
let values = try SignatureAudit.entitlements(in: binary)
precondition(values[key] as? Bool == true)
for prefix in [0, 1, 4, 16, 31, 40, 47, binary.count - 1] {
    do {
        _ = try SignatureAudit.entitlements(in: binary.prefix(prefix))
        fatalError("Truncated signature accepted")
    } catch {}
}
var huge = binary
huge.replaceSubrange(56..<60, with: word(UInt32.max, bigEndian: true))
do {
    _ = try SignatureAudit.entitlements(in: huge)
    fatalError("Unbounded entry count accepted")
} catch {}
print("PASS signature extraction, malformed inputs, and count bounds")

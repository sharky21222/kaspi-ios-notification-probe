#!/bin/bash
set -euo pipefail
command -v xcodegen >/dev/null || HOMEBREW_NO_AUTO_UPDATE=1 HOMEBREW_NO_INSTALL_CLEANUP=1 brew install xcodegen
xcodegen generate
swiftc SignatureCore/SignatureAudit.swift Tests/main.swift -o /tmp/probe-signature-tests
/tmp/probe-signature-tests
python3 -m unittest discover -s Tests -p 'test_*.py' -v
for scheme in InstallProbe AccessProbe; do
  xcodebuild -project KaspiProbe.xcodeproj -scheme "$scheme" -configuration Release \
    -sdk iphoneos -destination 'generic/platform=iOS' -derivedDataPath build/device \
    CODE_SIGNING_ALLOWED=NO CODE_SIGNING_REQUIRED=NO ARCHS=arm64 build > "build-${scheme}.log" 2>&1 || {
      tail -n 140 "build-${scheme}.log"; exit 1;
    }
  tail -n 3 "build-${scheme}.log"
done
python3 scripts/package_ipa.py
xcodebuild -project KaspiProbe.xcodeproj -scheme InstallProbe -configuration Debug \
  -sdk iphonesimulator -destination 'generic/platform=iOS Simulator' -derivedDataPath build/simulator \
  CODE_SIGNING_ALLOWED=NO build > build-simulator.log 2>&1 || {
    tail -n 100 build-simulator.log; exit 1;
  }
python3 scripts/simulator_capture.py

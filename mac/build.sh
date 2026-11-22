#!/bin/sh
# Compila o gravador nativo do macOS (requer Xcode Command Line Tools).
set -e
cd "$(dirname "$0")"
swiftc -O -parse-as-library -swift-version 5 Recorder.swift -o mac-recorder
echo "OK: $(pwd)/mac-recorder"

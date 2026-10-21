#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export CI=true
export RUSTUP_TOOLCHAIN=1.99.1
export PATH="$HOME/.cargo/bin:$PATH"
mkdir -p build output

case "${1:-}" in
  test)
    if ! command -v rustup >/dev/null; then
      url="https://static.rust-lang.org/rustup/dist/aarch64-apple-darwin/rustup-init"
      curl --fail --location --retry 2 "$url" -o build/rustup-init
      expected="$(curl --fail --location "$url.sha256" | awk '{print $1}')"
      actual="$(shasum -a 256 build/rustup-init | awk '{print $1}')"
      test "$expected" = "$actual"
      chmod +x build/rustup-init
      build/rustup-init -y --no-modify-path --default-toolchain none
    fi
    rustup toolchain install 1.99.1 --profile minimal --component rustfmt
    cargo test --manifest-path signer/Cargo.toml --locked -p kaspi-probe-signer 2>&1 | tee build-signer-tests.log
    cargo test --manifest-path signer/Cargo.toml --locked -p apple-codesign-quick --lib 2>&1 | tee -a build-signer-tests.log
    # These must fail before prompting or contacting Apple, even with a TTY.
    if cargo run --manifest-path signer/Cargo.toml --locked -- check-account; then
      echo 'ERROR: CI account guard failed' >&2
      exit 1
    fi
    ;;
  windows)
    export HOMEBREW_NO_AUTO_UPDATE=1
    if ! brew list llvm >/dev/null 2>&1; then brew install llvm; fi
    export PATH="$(brew --prefix llvm)/bin:$PATH"
    python3 -m venv build/signer-tools
    build/signer-tools/bin/python -m pip install --disable-pip-version-check 'cargo-xwin==0.23.1'
    export PATH="$PWD/build/signer-tools/bin:$PATH"
    rustup target add x86_64-pc-windows-msvc
    export XWIN_ARCH=x86_64
    export XWIN_CACHE_DIR="$HOME/.cache/kaspi-xwin"
    export CARGO_TARGET_X86_64_PC_WINDOWS_MSVC_RUSTFLAGS='-C target-feature=+crt-static'
    cargo xwin build --manifest-path signer/Cargo.toml --locked --release --bin kaspi-probe-signer --target x86_64-pc-windows-msvc 2>&1 | tee build-signer-windows.log
    git archive --format=zip -o build/signer-source.zip HEAD signer scripts/build_signer.sh scripts/package_signer.py codemagic.yaml
    python3 scripts/package_signer.py
    ;;
  *) echo 'Usage: build_signer.sh test|windows' >&2; exit 2 ;;
esac

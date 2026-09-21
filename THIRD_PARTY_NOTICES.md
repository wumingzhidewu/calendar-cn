# Third-party components

## Notification Center Styler

Author: m417z (Michael Maltsev), with upstream contributors.

Source: https://github.com/ramensoftware/windhawk-mods/blob/main/mods/windows-11-notification-center-styler.wh.cpp

License: GNU General Public License version 3, as declared in the source header.
The complete unmodified fetched file is retained in `vendor/`; its SHA-256 is
recorded in `project.json`. Generated modifications are made by `manage.py` and
the native holiday implementation is retained under `src/`. If distributing the
compiled DLL, distribute its corresponding source and this license material.

## Windhawk

Author: Ramen Software / Michael Maltsev.

Source and releases: https://github.com/ramensoftware/windhawk

Pinned build/runtime version: 1.7.3. The framework, compiler, runtime libraries,
and installer are acquired from the official release. The 0.3.0 desktop installer bundles only the required runtime subset and includes the corresponding Windhawk source archive under Source/. The compiler and editor are not bundled. Their upstream licenses remain applicable.
The build uses Windhawk's supplied compiler and import library.

## holiday-cn

Copyright (c) 2019 NateScarlet.

Source: https://github.com/NateScarlet/holiday-cn

Snapshot: 18c8f140cd8574faf72c8bb5cd0a9bdf9d1c1b6c.

License: MIT; full notice in `data/LICENSE`. Annual JSON files and the derived
TSV are included. Each JSON retains the government's source notice URLs.
Online updates may advance individual years beyond the initial snapshot; the
data manifest records the exact cached file hashes.

## Standalone updater runtime (0.2.0)

The frozen updater includes CPython 3.12.14 and standard-library components.
The Python Software Foundation license and incorporated notices are retained in
`licenses/Python-LICENSE.txt`. TLS support includes OpenSSL under the license
retained in `licenses/OpenSSL-LICENSE.txt`.

The executable uses the PyInstaller 6.22.3 bootloader under its GPL exception
for generated applications. The complete upstream license and exception are
in `licenses/PyInstaller-COPYING.txt`. PyInstaller is a build dependency, not
an end-user installation requirement. Sources:

- https://github.com/python/cpython
- https://github.com/openssl/openssl
- https://github.com/pyinstaller/pyinstaller


## Desktop installer (0.3.0)

Built using NSIS 3.12 (zlib/libpng license; upstream at https://nsis.sourceforge.io/). The installed LLVM libc++/libunwind runtime license is retained in licenses/LLVM-LICENSE.txt. The minimal Windhawk binaries are unmodified official 1.7.3 files; corresponding upstream source is bundled as Source/windhawk-1.7.3-source.zip. Project source, including the installer and manager, is bundled as Source/native-calendar-holidays-source.zip.

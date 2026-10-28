"""Install verified Debian Qt dev packages into /workspace without root privileges."""
from pathlib import Path
import os
import subprocess
import sys

BASE = Path('/workspace/toolchains')
APT = BASE / 'apt'
QT = BASE / 'qt'
PACKAGES = [
    'qt6-base-dev', 'qt6-declarative-dev', 'qt6-svg-dev', 'qt6-svg-plugins',
    'qt6-tools-dev', 'qt6-l10n-tools', 'qt6-serialport-dev', 'qt6-httpserver-dev',
    'qt6-websockets-dev', 'qml6-module-qtquick', 'qml6-module-qtquick-controls',
    'qml6-module-qtquick-layouts', 'qml6-module-qtquick-window',
    'qml6-module-qtquick-templates', 'qml6-module-qtqml-workerscript',
    'libssl-dev', 'ninja-build', 'clang-format-19',
]


def main():
    release = Path('/etc/os-release').read_text()
    if 'ID=debian' not in release or 'VERSION_ID="13"' not in release:
        raise RuntimeError('This helper targets Debian 13 only; use your native Qt SDK elsewhere')
    for p in ['lists/partial', 'archives/partial', 'empty']:
        (APT / p).mkdir(parents=True, exist_ok=True)
    (APT / 'sources.list').write_text('deb [signed-by=/usr/share/keyrings/debian-archive-keyring.gpg] https://deb.debian.org/debian trixie main\n')
    (APT / 'apt.conf').write_text(f'''Dir::Etc::parts "{APT}/empty";
Dir::Etc::main "-";
Dir::Etc::sourcelist "{APT}/sources.list";
Dir::Etc::sourceparts "{APT}/empty";
Dir::State::lists "{APT}/lists";
Dir::Cache::archives "{APT}/archives";
Debug::NoLocking "true";
APT::Sandbox::User "agent";
''')
    env = dict(os.environ, APT_CONFIG=str(APT / 'apt.conf'))
    subprocess.run(['apt-get', 'update'], env=env, check=True)
    subprocess.run(['apt-get', '--download-only', '-y', '--no-install-recommends', 'install', *PACKAGES], env=env, check=True)
    QT.mkdir(exist_ok=True)
    for deb in sorted((APT / 'archives').glob('*.deb')):
        subprocess.run(['dpkg-deb', '-x', str(deb), str(QT)], check=True)
    # Merge only missing installed runtime files. Do not overwrite extracted signed packages.
    for rel in ['usr/lib/x86_64-linux-gnu/qt6/qml', 'usr/lib/x86_64-linux-gnu/qt6/plugins']:
        source = Path('/') / rel
        for parent, directories, files in os.walk(source):
            for name in directories + files:
                original = Path(parent) / name
                target = QT / rel / original.relative_to(source)
                if not os.path.lexists(target):
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.symlink_to(original, target_is_directory=original.is_dir())
    source = Path('/usr/lib/x86_64-linux-gnu')
    target_dir = QT / 'usr/lib/x86_64-linux-gnu'
    target_dir.mkdir(parents=True, exist_ok=True)
    for original in source.iterdir():
        if original.name.startswith(('libQt6', 'libGL', 'libOpenGL', 'libEGL', 'libvulkan')):
            target = target_dir / original.name
            if not os.path.lexists(target):
                target.symlink_to(original, target_is_directory=original.is_dir())
    tools = BASE / 'python'
    if not (tools / 'bin/python').exists():
        subprocess.run([sys.executable, '-m', 'venv', str(tools)], check=True)
    subprocess.run([str(tools / 'bin/python'), '-m', 'pip', 'install', 'cmake==4.4.4', '-r', str(Path(__file__).resolve().parents[1] / 'test/requirements.txt')], check=True)
    cmake_bin = next((tools / 'lib').glob('python*/site-packages/cmake/data/bin'))
    (BASE / 'env.sh').write_text(f'''export PATH={cmake_bin}:{QT}/usr/bin:{QT}/usr/lib/qt6/bin:$PATH
export CMAKE_PREFIX_PATH={QT}/usr
export LD_LIBRARY_PATH={QT}/usr/lib/x86_64-linux-gnu${{LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}}
export QT_PLUGIN_PATH={QT}/usr/lib/x86_64-linux-gnu/qt6/plugins
export QML_IMPORT_PATH={QT}/usr/lib/x86_64-linux-gnu/qt6/qml
export XDG_CACHE_HOME=/workspace/.cache
''')
    print('Toolchain ready. Run: source /workspace/toolchains/env.sh')


if __name__ == '__main__':
    main()

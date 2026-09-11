# Copyright 2017 Virgil Dupras
#
# This software is licensed under the "GPLv3" License as described in the "LICENSE" file,
# which should be included with this package. The terms are also available at
# http://www.gnu.org/licenses/gpl-3.0.html

import sys
import os
import os.path as op
import compileall
import shutil
import json
from argparse import ArgumentParser
import subprocess
from pathlib import Path
import platform
import distro

from hscommon.build import (
    print_and_do,
    copy_packages,
    build_debian_changelog,
    get_module_version,
    filereplace,
    copy,
    setup_package_argparser,
    copy_all,
)

ENTRY_SCRIPT = "run.py"
LOCALE_DIR = "build/locale"
HELP_DIR = "build/help"


def parse_args():
    parser = ArgumentParser()
    setup_package_argparser(parser)
    parser.add_argument("--skip-nsis", action="store_true", help="Stage the PyInstaller directory only")
    parser.add_argument("--nsis-path", default=os.environ.get("TWINQUAY_NSIS", "makensis"))
    return parser.parse_args()


def check_loc_doc():
    if not op.exists(LOCALE_DIR):
        print('Locale files are missing. Have you run "build.py --loc"?')
    # include help files if they are built otherwise exit as they should be included?
    if not op.exists(HELP_DIR):
        print('Help files are missing. Have you run "build.py --doc"?')
    return op.exists(LOCALE_DIR) and op.exists(HELP_DIR)


def copy_files_to_package(destpath, packages, with_so):
    # when with_so is true, we keep .so files in the package, and otherwise, we don't. We need this
    # flag because when building debian src pkg, we *don't* want .so files (they're compiled later)
    # and when we're packaging under Arch, we're packaging a binary package, so we want them.
    if op.exists(destpath):
        shutil.rmtree(destpath)
    os.makedirs(destpath)
    shutil.copy(ENTRY_SCRIPT, op.join(destpath, ENTRY_SCRIPT))
    extra_ignores = ["*.so"] if not with_so else None
    copy_packages(packages, destpath, extra_ignores=extra_ignores)
    # include locale files if they are built otherwise exit as it will break
    # the localization
    if not check_loc_doc():
        print("Exiting...")
        return
    shutil.copytree(op.join("build", "help"), op.join(destpath, "help"))
    shutil.copytree(op.join("build", "locale"), op.join(destpath, "locale"))
    compileall.compile_dir(destpath)


def package_debian_distribution(distribution):
    app_version = get_module_version("core")
    version = "{}~{}".format(app_version, distribution)
    destpath = op.join("build", "dupeguru-{}".format(version))
    srcpath = op.join(destpath, "src")
    packages = ["hscommon", "core", "qt", "send2trash"]
    copy_files_to_package(srcpath, packages, with_so=False)
    os.mkdir(op.join(destpath, "modules"))
    copy_all(op.join("core", "pe", "modules", "*.*"), op.join(destpath, "modules"))
    copy(
        op.join("qt", "pe", "modules", "block.c"),
        op.join(destpath, "modules", "block_qt.c"),
    )
    copy(
        op.join("pkg", "debian", "build_pe_modules.py"),
        op.join(destpath, "build_pe_modules.py"),
    )
    debdest = op.join(destpath, "debian")
    debskel = op.join("pkg", "debian")
    os.makedirs(debdest)
    debopts = json.load(open(op.join(debskel, "dupeguru.json")))
    for fn in ["compat", "copyright", "dirs", "rules", "source"]:
        copy(op.join(debskel, fn), op.join(debdest, fn))
    filereplace(op.join(debskel, "control"), op.join(debdest, "control"), **debopts)
    filereplace(op.join(debskel, "Makefile"), op.join(destpath, "Makefile"), **debopts)
    filereplace(op.join(debskel, "dupeguru.desktop"), op.join(debdest, "dupeguru.desktop"), **debopts)
    changelogpath = op.join("help", "changelog")
    changelog_dest = op.join(debdest, "changelog")
    project_name = debopts["pkgname"]
    from_version = "2.9.2"
    build_debian_changelog(
        changelogpath,
        changelog_dest,
        project_name,
        from_version=from_version,
        distribution=distribution,
    )
    shutil.copy(op.join("images", "dgse_logo_128.png"), srcpath)
    os.chdir(destpath)
    cmd = "dpkg-buildpackage -F -us -uc"
    os.system(cmd)
    os.chdir("../..")


def package_debian():
    print("Packaging for Debian/Ubuntu")
    for distribution in ["unstable"]:
        package_debian_distribution(distribution)


def package_arch():
    # For now, package_arch() will only copy the source files into build/. It copies less packages
    # than package_debian because there are more python packages available in Arch (so we don't
    # need to include them).
    print("Packaging for Arch")
    srcpath = op.join("build", "dupeguru-arch")
    packages = ["hscommon", "core", "qt", "send2trash"]
    copy_files_to_package(srcpath, packages, with_so=True)
    shutil.copy(op.join("images", "dgse_logo_128.png"), srcpath)
    debopts = json.load(open(op.join("pkg", "arch", "dupeguru.json")))
    filereplace(op.join("pkg", "arch", "dupeguru.desktop"), op.join(srcpath, "dupeguru.desktop"), **debopts)


def package_source_txz():
    print("Creating git archive")
    app_version = get_module_version("core")
    name = "twinquay-src-{}.tar".format(app_version)
    base_path = os.getcwd()
    build_path = op.join(base_path, "build")
    dest = op.join(build_path, name)
    print_and_do("git archive -o {} HEAD".format(dest))
    print_and_do("xz {}".format(dest))


def package_windows(skip_nsis=False, nsis_path="makensis"):
    if sys.platform != "win32":
        raise RuntimeError("Windows packages must be built on Windows")
    if platform.architecture()[0] != "64bit":
        raise RuntimeError("TwinQuay requires a 64-bit Python interpreter")
    if not check_loc_doc():
        raise RuntimeError("Run build.py --clean before packaging")
    version = get_module_version("core").split(".")
    info_path = Path("win_version_info.txt")
    info_path.write_text(
        Path("win_version_info.temp").read_text(encoding="utf-8").format(*version, "64"), encoding="utf-8"
    )
    subprocess.run([sys.executable, "tools/collect_notices.py"], check=True)
    import PyInstaller.__main__

    try:
        PyInstaller.__main__.run(
            [
                "--name=TwinQuay",
                "--windowed",
                "--onedir",
                "--clean",
                "--noconfirm",
                "--icon=images/twinquay/logo.ico",
                "--add-data=build/locale;locale",
                "--add-data=build/help;help",
                "--add-data=LICENSE;.",
                "--add-data=THIRD-PARTY-NOTICES.txt;.",
                "--add-data=build/notices;notices",
                "--version-file=win_version_info.txt",
                ENTRY_SCRIPT,
            ]
        )
    finally:
        info_path.unlink(missing_ok=True)
    subprocess.run([sys.executable, "tools/package_inventory.py", "dist/TwinQuay"], check=True)
    if not skip_nsis:
        compiler = shutil.which(nsis_path)
        if compiler is None:
            raise RuntimeError("NSIS missing: provide --nsis-path or TWINQUAY_NSIS; use --skip-nsis for MSIX staging")
        subprocess.run(
            [
                compiler,
                f"/DVERSIONMAJOR={version[0]}",
                f"/DVERSIONMINOR={version[1]}",
                f"/DVERSIONPATCH={version[2]}",
                "/DBITS=64",
                "/DAPPNAME=TwinQuay",
                "setup.nsi",
            ],
            check=True,
        )


def package_macos():
    # include locale files if they are built otherwise exit as it will break
    # the localization
    if not check_loc_doc():
        print("Exiting")
        return
    # run pyinstaller from here:
    import PyInstaller.__main__

    PyInstaller.__main__.run(
        [
            "--name=dupeguru",
            "--windowed",
            "--noconfirm",
            "--icon=images/dupeguru.icns",
            "--osx-bundle-identifier=com.hardcoded-software.dupeguru",
            "--add-data={0}:locale".format(LOCALE_DIR),
            "--add-data={0}:help".format(HELP_DIR),
            "{0}".format(ENTRY_SCRIPT),
        ]
    )


def main():
    args = parse_args()
    if args.src_pkg:
        print("Creating source package for TwinQuay")
        package_source_txz()
        return
    if sys.platform != "win32":
        raise SystemExit("TwinQuay packages must be built on Windows; this host supports source and local tests.")
    print("Packaging TwinQuay with UI qt")
    if sys.platform == "win32":
        package_windows(args.skip_nsis, args.nsis_path)
    elif sys.platform == "darwin":
        package_macos()
    else:
        if not args.arch_pkg:
            distname = distro.id()
        else:
            distname = "arch"
        if distname == "arch":
            package_arch()
        else:
            package_debian()


if __name__ == "__main__":
    main()

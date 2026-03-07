 Grabbing pre-built releases is the right call. Here's why:

  Pre-built releases (recommended):
  - sqldef already publishes binaries for all the platforms you care about (linux/mac/win × amd64/arm64)
  - No Go toolchain needed in your CI
  - You're not maintaining a fork — you just pin to a known-good version
  - This is the established pattern for Python packages vendoring non-Python binaries (ruff, shfmt-py, etc.)

  Building from source would make sense if you needed to patch sqldef or link it as a library, but you're just shelling out to
  it, so there's no reason to take on that complexity.

  How it works in practice:

  You'd publish platform-specific wheels — one per OS/arch combo. Each wheel contains only the single psqldef (or mysqldef)
  binary for that platform. The structure looks like:

  embar-0.1.0-py3-none-manylinux_2_17_x86_64.whl
  embar-0.1.0-py3-none-manylinux_2_17_aarch64.whl
  embar-0.1.0-py3-none-macosx_11_0_arm64.whl
  embar-0.1.0-py3-none-macosx_10_9_x86_64.whl
  embar-0.1.0-py3-none-win_amd64.whl

  Your CI/release script would:
  1. Download the sqldef release tarball for each platform
  2. Place the binary into src/embar/_vendor/ (or similar)
  3. Build a wheel with the correct platform tag
  4. Upload all wheels to PyPI

  pip install embar then automatically picks the right wheel for the user's platform.

  Want me to look at your current project structure and sketch out the implementation?

# devenv.sh — single source of truth for sunset's toolchain (tambor/DDL-irv
# fleet pattern). The Python layer is pinned by uv.lock + .python-version;
# this module supplies the interpreter and uv binary via Nix.
# Verify (pending nix install on this machine): devenv shell -- just spec-check
{ pkgs, ... }: {
  packages = with pkgs; [
    git
  ];

  languages.python = {
    enable = true;
    # Keep in lockstep with .python-version; note nixpkgs-rolling may lag —
    # if unavailable, drop to the newest supported minor and re-pin uv.lock.
    version = "3.15";
    uv.enable = true;
  };

  enterShell = ''
    if [ ! -d .venv ]; then
      echo "devenv: .venv missing — run 'uv sync'"
    fi
  '';
}

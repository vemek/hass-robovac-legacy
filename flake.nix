{
  description = "Home Assistant RoboVac 11c integration (legacy) — dev shell";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs =
    { self, nixpkgs }:
    let
      inherit (nixpkgs) lib;
      forAllSystems = lib.genAttrs lib.systems.flakeExposed;
    in
    {
      devShells = forAllSystems (
        system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
        in
        {
          default = pkgs.mkShell {
            packages = [ pkgs.python3 ];
            shellHook = ''
              echo 'LAN control is vendored under custom_components/robovac_legacy/lan (+ Home Assistant protobuf).'
              echo 'Python: use direnv (layout python3 in .envrc). pip exists only in .direnv/python-*; run: pip install -r requirements-dev.txt'
              echo 'LAN debug script: PYTHONPATH="$(pwd)" python scripts/dump_robovac_lan.py'
              echo 'Smoke tests (stdlib, no HA): PYTHONPATH="$(pwd)" python -m unittest discover -s tests -p "test_eufynet.py" -v'
              echo 'Full suite (separate venv): python3 -m venv .qa && .qa/bin/pip install --ignore-installed idna requests==2.32.4 pycares==4.11.0 protobuf==6.32.0 pycryptodome -r requirements-test.txt six && env -u PYTHONPATH ".qa/bin/pytest" tests -v'
            '';
          };
        }
      );
    };
}

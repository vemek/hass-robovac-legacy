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
          py = pkgs.python3.withPackages (ps: [ ps.requests ]);
        in
        {
          default = pkgs.mkShell {
            packages = [ py ];
            shellHook = ''
              echo 'Legacy integration uses PyRobovac via HA manifest dependency `robovac==0.0.9`.'
              echo 'Smoke tests (stdlib, no HA): PYTHONPATH="$(pwd)" python -m unittest discover -s tests -p "test_eufynet.py" -v'
              echo 'Full suite (venv recommended): python3 -m venv .qa && .qa/bin/pip install --ignore-installed idna requests==2.32.4 pycares==4.11.0 -r requirements-test.txt six && env -u PYTHONPATH ".qa/bin/pytest" tests -v'
            '';
          };
        }
      );
    };
}

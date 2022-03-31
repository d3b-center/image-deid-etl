{
  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixpkgs-unstable";

    # Pinned to @rbreslow's PR that adds support for JPEG 2000.
    # https://github.com/NixOS/nixpkgs/pull/165477
    nixpkgs-dcm2niix.url = "github:nixos/nixpkgs/38eccfa38687aee87f1690991e9924a555e5ef86";

    # Pinned to @rbreslow's PR that adds the Flywheel CLI to Nixpkgs.
    # https://github.com/NixOS/nixpkgs/pull/165458
    nixpkgs-flywheel-cli.url = "github:nixos/nixpkgs/826d00cd02e6cd58d56c77784bcddcf496e7c330";

    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, nixpkgs-dcm2niix, nixpkgs-flywheel-cli, flake-utils, ... }:
    flake-utils.lib.eachSystem [ "x86_64-darwin" "x86_64-linux" ] (system:
      let
        lib = nixpkgs.lib;
        pkgs = import nixpkgs { inherit system; };

        # We need to build our own version of dcm2niix because there hasn't
        # been a release since @neurolabusc fixed
        # https://github.com/rordenlab/dcm2niix/issues/566.
        dcm2niixSnapshot = with (import nixpkgs-dcm2niix { inherit system; });
          (dcm2niix.overrideAttrs (oldAttrs: rec {
            # Development snapshot from February 22, 2022.
            version = "002ebcdb9b2a87de7b883e9ddada3963a1cc2327";

            src = fetchFromGitHub {
              owner = "rordenlab";
              repo = "dcm2niix";
              rev = "${version}";
              sha256 = "sha256-OdLHXcYPJROdjLR7RvBvKVQwLdVIKcVwfuH4Zkm7Bb0=";
            };
          }));

        # Temporary, until @rbreslow's PR is merged into Nixpkgs.
        flywheel-cli = (import nixpkgs-flywheel-cli { inherit system; })
          .flywheel-cli;
      in
      {
        devShell = pkgs.mkShell {
          # The directory to create the Python virtual environment in.
          venvDir = "./.venv";

          buildInputs = with pkgs; [
            awscli2
            dcm2niixSnapshot
            flywheel-cli
            python3
            # Executes some shell code to initialize a venv in $venvDir before
            # dropping into the shell.
            python3Packages.venvShellHook
          ];

          postShellHook = ''
            # Enable support for the deprecated `fw import` command while we
            # migrate to `fw ingest`.
            # https://docs.flywheel.io/hc/en-us/articles/4416119193491-Deprecation-of-CLI-fw-import-Command
            export FLYWHEEL_CLI_LEGACY=true

            # Read and export our dotenv file to the environment.
            set -o allexport
            source .env
            set +o allexport
          '';
        };
      }
    );
}

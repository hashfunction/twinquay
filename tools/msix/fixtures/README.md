# Store export receipt replay

`store-export-success.json` comes from the successful Windows run 34680779425 (public source 7a88fceeec60a70e34e324a90deafe2101ed641e), both disposable and assigned Store identities. It retains actual installation, file-oracle, surface geometry and loaded-module facts. Large UI control lists and non-native payload entries are omitted because the export replay does not consume them.

The tests add current run fields, bind source helper hashes, and substitute clearly synthetic screenshot bytes in exclusive local temporary files. The complete export tests additionally create a real ZIP/Git tree with synthetic native bytes. These are regression fixtures for validation and refusal; they do not represent another Windows run or qualify a distributable. The real Windows workflow must pass every original installed gate again before exporting.

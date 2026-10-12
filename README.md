# Doonesbury archive reader

A dependency-free static website for browsing the daily and Sunday strip archive in one chronological sequence.

## Build the catalog

The browser cannot list local directories, so generate `data/catalog.json` after adding, removing, or renaming archive files:

```sh
python3 scripts/build_catalog.py
```

Verify that the committed catalog is current without changing it:

```sh
python3 scripts/build_catalog.py --check
```

The image files are the source of truth for navigation. The yearly JSON files supply optional storyline descriptions. Existing date collisions and weekday anomalies are preserved and reported by the generator.

## Serve locally

From the repository root, run:

```sh
python3 -m http.server 8000
```

Then open [http://localhost:8000/](http://localhost:8000/) in a browser. The reader stores the last successfully displayed strip in a one-year browser cookie so the index can offer a resume link.

## Test

```sh
python3 -m unittest discover -s tests
```

# Astroverse crawler

This project crawls novels from truyenfull-like sites and saves each novel to `data/<novel-slug>/`.

Quick start

1. Create virtualenv and install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r crawling/requirements.txt
```

2. Run crawler with resume support:

```bash
python3 crawling/main.py --debug
# or force a fresh run (delete or ignore previous state):
python3 crawling/main.py --no-resume
```

Data layout

- data/
  - state.json          # crawler resume state
  - genres.json         # collected genres
  - <novel-slug>/
    - metadata.json
    - 001 - CHAPTER-ID - title.txt
    - 002 - ...

To force a clean run delete `data/` directory.

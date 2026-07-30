# Publishing the benchmark data on Zenodo

Goal: deposit the benchmark **data** (CC-BY-4.0), get a citable DOI, put that DOI
into `./doc/logistic_benchmark_lncs.pdf` before submitting to the conference.

Scope chosen: **data only** (manual web upload).

---

## 0. What to upload

Upload these from the repo root:

| File | What it is |
|------|------------|
| `Generated_Data.zip` (1.8 MB) | The benchmark instances (35 synthetic + 15 real-geometry) |
| `Results.zip` (1.1 MB) | Computational results |
| `LICENSE-DATA.txt` | CC-BY-4.0 data license + attribution text |
| `CITATION.cff` | Machine-readable citation metadata |
| `Generator.py` (+ `Solver.py`, `VNS.py`, etc.) | *Optional*, generator code as context |

Before uploading, sanity-check the archives still match the directories:

```bash
cd /Users/aponom/research/Optimal-Logistic-Net
unzip -l Generated_Data.zip | tail -3
unzip -l Results.zip | tail -3
```

If they're stale, regenerate:

```bash
zip -r Generated_Data.zip Generated_Data
zip -r Results.zip Results
```

---

## 1. Create the account

1. Go to <https://zenodo.org> and **Sign up** (you can log in with GitHub or ORCID).
2. If you have an **ORCID iD**, link it now — it auto-fills your author record and
   makes the dataset discoverable under your profile.

---

## 2. Start a new upload and RESERVE the DOI first

This is the important ordering step.

1. Top-right **New upload** (or <https://zenodo.org/uploads/new>).
2. Under **Digital Object Identifier**, choose **"No"** to "Do you already have a DOI?"
   then click **Reserve DOI**.
3. Zenodo shows a reserved DOI like `10.5281/zenodo.XXXXXXX`. **Copy it.**
   This DOI is valid even though the record isn't published yet.

> Zenodo gives you two DOIs: a **concept DOI** (always points to the latest
> version — cite this one in the paper for longevity) and a **version DOI**
> (this exact upload). For the paper, prefer the **concept DOI** shown as
> "Cite all versions".

---

## 3. Fill in the metadata

| Field | Value |
|-------|-------|
| **Resource type** | *Dataset* |
| **Title** | A Benchmark Generator of Realistic Logistic Transport Networks with Nonlinear Edge Costs and Transshipment Capacities |
| **Authors** | Kovaleva, Varvara; Ponomarenko, Alexander — affiliation: HSE University, Laboratory of Algorithms and Technologies for Network Analysis, Nizhny Novgorod, Russia (add ORCIDs if available) |
| **Description** | Paste the `abstract` from `CITATION.cff` |
| **License** | Creative Commons Attribution 4.0 International (CC-BY-4.0) |
| **Keywords** | benchmark generation, synthetic data, spatial networks, multi-commodity flow, gravity model, Zipf's law, logistics |
| **Version** | 1.0.0 |
| **Language** | English |

Under **Related works / identifiers**, add a link to the paper once it has a
DOI/arXiv id (relation: *"is supplement to"*). You can also add the GitHub repo
URL here (relation: *"is supplemented by"*).

---

## 4. Put the DOI into the paper, then rebuild

1. Edit `./doc/logistic_benchmark_lncs.tex` — add the dataset citation /
   data-availability statement, e.g.:

   > *Data availability.* The benchmark corpus is openly available on Zenodo at
   > `https://doi.org/10.5281/zenodo.XXXXXXX` (CC-BY-4.0).

2. Update `CITATION.cff` — uncomment and fill the DOI line:

   ```yaml
   doi: 10.5281/zenodo.XXXXXXX
   ```

3. Rebuild the PDF:

   ```bash
   cd /Users/aponom/research/Optimal-Logistic-Net/doc
   latexmk -pdf logistic_benchmark_lncs.tex
   ```

---

## 5. Publish

1. Back on the Zenodo upload page, click **Publish**.
2. The reserved DOI is now live and resolvable at
   `https://doi.org/10.5281/zenodo.XXXXXXX`.

> **Note:** Files cannot be changed after publishing — only a *new version*
> (with a new version DOI but the same concept DOI) can be created. Double-check
> the zips before clicking Publish.

---

## 6. After submission

- Once the paper is accepted and has its own DOI, edit the Zenodo record's
  **Related identifiers** to link it (relation: *"is supplement to"*).
- If you later regenerate data, use **New version** on the Zenodo record so the
  concept DOI in the paper keeps resolving to the newest data.

---

### Quick checklist

- [ ] Archives verified / regenerated
- [ ] Zenodo account + ORCID linked
- [ ] DOI reserved and copied
- [ ] Metadata filled (Dataset, CC-BY-4.0, authors, abstract)
- [ ] DOI added to `logistic_benchmark_lncs.tex` and `CITATION.cff`
- [ ] Paper PDF rebuilt
- [ ] Zenodo record published
- [ ] Paper submitted to conference

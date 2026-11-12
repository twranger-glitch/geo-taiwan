# data/gnss

`gnss.json` is derived from **Tung, H. et al. (2026), "A 2010–2024 continuous GNSS dataset for Taiwan", Scientific Data**,
doi:10.1038/s41597-026-07876-y; data: https://doi.org/10.5281/zenodo.23551543 (CC BY 4.0, Institute of Earth Sciences, Academia Sinica).

Derived here (not part of the original dataset):
- `st`: station velocity (mm/yr) relative to Penghu S01R, fitted as linear + annual + semi-annual on the offset-corrected daily series (weekly medians).
- `ser`: monthly displacement since 2010.0 (mm, E/N/U) relative to S01R, with coseismic offsets kept and instrument offsets removed.
- `eq`: coseismic offsets (mm), estimated as the step in (raw − offset-corrected) around each listed earthquake date.
- `land`, `border`, `labels`, `hs`: basemap shared with the power map (MOI boundaries via taiwan-atlas; Terrain Tiles hillshade).

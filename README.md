# Understanding mobility-aware social segregation in Sweden through big mobile phone application

This pilot study is to conduct a mini version of its [parent project](https://github.com/MobiSegInsights), 
relying the state-of-the-art methods and practices in quantifying experienced social segregation, 
transport accessibility, mobility patterns, and how they are associated with each other. 
The pilot study will be used to reveal the data limitations, the idea of cross-regional comparison, 
and the baseline for further innovative method development.

## Data
Big geolocation data from various sources offer an opportunity to better understand human mobility and built environment. 
Mobile Application Data (MAD) is a cost-effective source of anonymised population mobility data. 
The geolocations (GPS coordinates) and times are recorded when phone users use applications that enable location tracking.
MAD is harvested by Internet companies, e.g., Pickwell (http://www.pickwell.co/), 
and has high spatiotemporal resolution and extensive population coverage without personal information.  

An existing dataset of anonymised MAD for Sweden is available, covering six months in 2019. 
For Sweden, the current data cover around 10% of the Swedish population, with about 25 million daily records. 
The raw data are not available due to privacy concern. However, the aggregated results of social segregation measures,
together with the metrics on transport accessibility, residential segregation etc will be made publicly available with
high spatial and temporal resolution.

## Scripts
The repo contains the scripts (`src/`), libraries (`lib/`) for conducting the data processing, analysis, and visualisation.
The original input data are stored under `dbs/` locally and intermediate results are stored in a local database.
Only results directly used for visualisation and upcoming article writing are stored under `results/`.
The produced figures are stored under `figures/`.
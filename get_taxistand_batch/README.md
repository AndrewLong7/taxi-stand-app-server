# Taxi Stands Finder

This project is a taxi stand recommendation system that computes distances between a user's location and taxi stands using Google Maps API, H3 grids, or OSMnx road networks. It also ranks the top 5 taxi stands based on distance and order volume using a scoring algorithm.

## Features
- Compute distances using:
  - Google Maps Distance Matrix API
  - H3 hexagonal grids
  - OSMnx road networks
- Rank taxi stands by f_score (based on distance and order volume)
- Interactive CLI for user input

---

## Setup Instructions
### 1. Set Up Python Environment
Ensure you have `conda` installed. Create and activate the `conda` environment:
```bash
conda env create -f environment.yml
conda activate taxist_lab
```

### 2. Add Google Maps API Key
Replace the placeholder `API_KEY` in the code with your actual Google Maps API key:
```python
API_KEY = "YOUR_GOOGLE_MAPS_API_KEY"
```

### 3. Install OSMnx Dependencies
If not installed already:
```bash
conda install -c conda-forge osmnx
```

---

## How to Use

1. Run the program:
   ```bash
   python get_nearby_taxi_batch.py
   ```

2. Follow the prompts:
   - Enter your **latitude**, **longitude**, and **hour of the day**.
   - Select the type of taxi stand (`Urban`, `Cross Harbour`, etc.).
   - Choose the distance calculation method:
     - OSMnx road network
     - H3 grid system
     - Google Maps API

3. View the top 5 recommended taxi stands.(change)


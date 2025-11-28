# Autonomous Vehicle Simulation: Micro-Grid & Macro-City Navigation

![Python](https://img.shields.io/badge/Python-3.9%2B-blue)
![Pygame](https://img.shields.io/badge/Library-Pygame-green)
![OSMnx](https://img.shields.io/badge/Geospatial-OSMnx-orange)
![NetworkX](https://img.shields.io/badge/Graph-NetworkX-red)

## 🚗 Project Overview

This project is a dual-layer autonomous vehicle (AV) simulation engine that bridges the gap between local safety and global navigation. Unlike standard simulations that focus on only one aspect, this system integrates two distinct planners:

1.  **Global Planner (Macro-Scope):** Navigates real-world city networks (e.g., Jaipur, London) using OpenStreetMap data and a Modified Dijkstra Algorithm that accounts for real-time traffic density.
2.  **Local Planner (Micro-Scope):** Handles immediate physical safety on an $8 \times 30$ grid, utilizing predictive collision detection to avoid dynamic obstacle vehicles and static potholes.

The simulation features a robust GUI with dual-view dashboards, real-time telemetry, occupancy matrices, and schematic overviews to visualize the AV's decision-making logic.

## ✨ Key Features

### 🌍 Module 1: Global Path Planning (Macro)
* **Real-World Maps:** Uses `OSMnx` to fetch and render actual street networks from cities like **Jaipur, London, and New York**.
* **Traffic-Aware Routing:** Implements a **Modified Dijkstra Algorithm** that calculates costs based on travel time and traffic density rather than just physical distance.
    * *Formula:* $Cost = Length \times (1 + TrafficDensity^2 \times 0.1)$
* **Dynamic Re-routing:** The AV automatically recalculates the optimal path if a user manually blocks a road or traffic congestion spikes.
* **Abstract Graph Generation:** Converts complex geospatial data into simplified "Abstract Nodes" for easier waypoint selection.

### ⚠️ Module 2: Local Collision Avoidance (Micro)
* **Predictive Safety:** Uses a `will_be_free()` function to check future grid states before moving.
* **Dynamic Obstacles:** AI-driven obstacle vehicles move laterally, reverse at boundaries, and interact with the environment.
* **Static Hazards:** Randomly generated potholes that require immediate avoidance maneuvering.
* **Occupancy Matrix:** A real-time binary visualization of the grid ($8 \times 30$) used for debugging collision logic.

### 📊 Visualization & Telemetry
* **Schematic Overview:** Top-down logic view of the grid.
* **Path Planning Panel:** Visualizes the A* or local search logic.
* **Data Dashboard:** Plots success rates, collision counts, and completion times using `Matplotlib`.

## 🛠️ Tech Stack

* **Language:** Python 3.x
* **Rendering Engine:** Pygame (60 FPS simulation loop)
* **Geospatial Data:** OSMnx (OpenStreetMap API)
* **Graph Algorithms:** NetworkX
* **UI/UX:** Pygame-Menu
* **Data Analysis:** Matplotlib, Pandas

## ⚙️ Algorithms Explained

### 1. Modified Dijkstra (Global)
Standard GPS navigation often fails to account for dynamic traffic flow. Our implementation weights the edges of the city graph dynamically. "Traffic Bots" move randomly through the city; their density on a specific road segment exponentially increases the "cost" of that edge, forcing the AV to find alternative, less congested routes.

### 2. Predictive Collision Detection (Local)
The local planner does not just check if a cell is empty *now*; it checks if it will be empty *in the next frame*.
* **Pre-Move Check:** Validates if the target cell is within bounds and free of potholes.
* **Dynamic Prediction:** specific logic ensures the AV does not move into a cell that an obstacle vehicle is about to enter.
* **Terminal Check:** A final safety validation post-movement to trigger "Crash" states if physical overlap occurs.

## 🚀 Installation & Usage

### Prerequisites
Ensure you have Python 3.9+ installed.

### Installation
1.  Clone the repository:
    ```bash
    git clone [https://github.com/yourusername/av-simulation-project.git](https://github.com/yourusername/av-simulation-project.git)
    cd av-simulation-project
    ```

2.  Install dependencies:
    ```bash
    pip install pygame pygame-menu osmnx networkx matplotlib requests
    ```
    *(Note: Windows users may need to install binary wheels for `GDAL` or `Rtree` if OSMnx installation fails directly.)*

### Running the Simulation
Execute the main engine:
```bash
python main.py

👥 Authors
Tirumala Sumith (2021BTECH114)

Asit Kumar Giri (2021BTECH028) 

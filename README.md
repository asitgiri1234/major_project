Autonomous Vehicle Obstacle Avoidance Simulation

A Python-based visual simulation that demonstrates how an Autonomous Vehicle (AV) detects obstacles, avoids collisions, and navigates through a road environment using a simple decision-making algorithm. The project visualizes the AV’s real-time environment, occupancy matrix, and path planning logic through multiple graphical panels.

 Overview

This simulation represents the functioning of an autonomous vehicle navigating on a grid-based road with multiple obstacles and potholes. The AV makes intelligent decisions at each time step to move safely while avoiding dynamic and static hazards.

The interface contains:

Main Road View: Displays the AV, other moving vehicles, and potholes on a scrolling road.

Schematic Overview: Simplified top-down grid showing all object positions.

Occupancy Matrix: Binary matrix showing which grid cells are occupied.

Path Planning Panel: Highlights how the AV plans its next move.

Log Panel: Displays simulation events and debug information.

 Features

 Real-time vehicle motion and obstacle movement
 Random obstacle and pothole generation each run
 AV path planning with collision avoidance
 Multi-panel visualization (Schematic, Matrix, Planning View)
 Smooth animation using easing functions
 Dynamic environment with parallax road background
 Logging of simulation events for debugging

 Algorithm and Logic

The Autonomous Vehicle (AV) follows a simple but effective path-planning logic:

Obstacle Mapping:
The AV reads the grid (occupancy matrix) to detect vehicles and potholes nearby.

Movement Decision:

Move forward if the next cell is free.

If blocked, check left/right lanes for a safe move.

If both sides are blocked, try diagonal escape.

If all directions are unsafe, stay put.

Obstacle Dynamics:
Each obstacle vehicle moves horizontally (left/right). If it reaches the edge or another vehicle, it reverses direction.

Collision Avoidance:
The AV ensures that no planned move results in occupying a cell with an obstacle or pothole.

Animation Smoothing:
The transition between cells uses an ease-in-out function for realistic motion.

 Real-World Inspiration

This simulation mimics real-world AV systems such as those used by:

Tesla Autopilot

Waymo

Cruise by GM

Baidu Apollo

These vehicles use real-time perception, obstacle detection, and motion planning algorithms to navigate safely — the core principles of which are represented here in a simplified grid format.

 Tech Stack
Component	Technology
Language	Python 3.x
Graphics Engine	Pygame
Data Structures	Dictionaries, Sets, Tuples
Animation Logic	Frame-based easing interpolation
UI Elements	Multi-panel rendering and logging

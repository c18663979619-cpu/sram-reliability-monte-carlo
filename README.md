# SRAM Reliability Monte Carlo Project

## Project question

How does random transistor threshold-voltage variation affect the read stability of a conventional 6-transistor (6T) SRAM cell?

## First model

- Reliability metric: read noise margin (RNM).
- Random input: threshold-voltage variation for the six transistors.
- Failure rule: RNM <= 0, which represents a read-stability failure in the referenced model.
- Main outputs: the RNM distribution and estimated failure probability as variation changes.
- Tools: Python, NumPy and Matplotlib.

## Scope and limitations

This project will implement and explain a source-based statistical sensitivity model. It is not a transistor-level SPICE simulation and does not claim to predict a particular commercial chip. Parameter values, units and assumptions will be documented before results are interpreted.

## Learning plan

1. Learn the SRAM cell and read-stability concepts.
2. Understand the published model parameters and assumptions.
3. Implement one Monte Carlo run in Python.
4. Sweep variation levels and estimate failure probability.
5. Plot, interpret and document the results.

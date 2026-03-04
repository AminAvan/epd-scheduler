# Earliest Possible Deadline (EPD) Scheduler

> **Based on the paper:** *"A Robust Scheduling Algorithm for Overload-Tolerant Real-Time Systems (IEEE ISORC 2023)"*

## Overview
In soft real-time systems, overload conditions can occur and represent a critical point of failure. When a system becomes overloaded, classic scheduling algorithms like Rate Monotonic (RM), Earliest Deadline First (EDF), and Least Laxity First (LLF) suffer from severe performance degradation due to the **domino effect** and excessive **context switching**.

This repository contains the implementation of the **Earliest Possible Deadline (EPD)** algorithm. EPD is a novel robust task-scheduling algorithm designed for both uniprocessor and partitioned multiprocessor systems. It maintains optimal performance under normal conditions while gracefully handling overload situations without sacrificing system efficiency.

## Key Features & Contributions
* **Dual-Mode Efficiency:** Operates similarly to EDF under normal conditions (guaranteeing optimality for non-overloaded systems) but dynamically adapts during overloads.
* **Domino Effect Elimination:** Prevents the cascading failure of task deadlines that plagues traditional algorithms during CPU saturation.
* **Zero/Minimal Context Switching Overhead:** Drastically reduces the burden on the system by making smarter execution decisions, achieving the lowest miss-rate without unnecessary context-switching.
* **High Processor Utilization:** Maximizes scheduling efficiency and throughput compared to RM, EDF, and LLF.
* **Versatile Architecture:** Designed to operate seamlessly on uniprocessor and partitioned multiprocessor environments.

---

## How EPD Works
Instead of blindly attempting to execute tasks as they approach their deadlines, EPD introduces a crucial feasibility check. 

The algorithm allocates processor time based on the *actual possibility* of task completion. Specifically, **EPD executes the task with the earliest absolute deadline ONLY IF that task can be completed within the remaining time prior to its absolute deadline.** If a task cannot mathematically finish in time, EPD avoids wasting processor cycles on it, thereby saving resources for tasks that can actually be saved.

## Performance vs. Classic Algorithms
Experimental results demonstrate that EPD consistently outperforms classic scheduling algorithms in overloaded states:

| Feature/Metric | RM / EDF / LLF | EPD (Our Approach) |
| :--- | :--- | :--- |
| **Non-Overload Performance** | Optimal | **Optimal** (Mirrors EDF) |
| **Overload Handling** | Deficient | **Robust** |
| **Domino Effect** | Susceptible | **Eliminated** |
| **Context Switching** | High Overhead | **Zero/Minimal Overhead** |
| **Miss Rate** | High | **Lowest** |
| **Throughput & Efficiency**| Limited | **Highest** |


## Workload

This workload dataset currently consists of one-hundred overloaded workloads with different tasks.

Contact: Amin Avan (amin.avan@ontariotechu.net)

### Description
Each workload has parameters including:

* `NumberOfTask`: shows How many tasks are in the workload. 
* `WorkloadUtilization`: shows how much is the utilization of the workload.
* `Execution Time`: shows the execution time of each task.
* `Deadline`: shows the deadline of each task.
* `Time Period`: shows the period of each task.

We assume that the "period" equals the "deadline".

### Format of dataset (example)
```
[10,1.25]
4,20,20
4,40,40
6,60,60
8,80,80
10,100,100
30,200,200
50,400,400
70,600,600
90,800,800
150,1000,1000
```
According to the example,
* There are ten tasks in the workload.
* The workload utilization is 1.25, which demonstrates that the workload is in an overloading situation.
* The first task has the following characteristics:
	* Execution time: 4
	* Deadline: 20
	* Period: 20

## Citation
If you use this dataset for your research, please cite our paper [A Robust Scheduling Algorithm for Overload-Tolerant Real-Time Systems](https://ieeexplore.ieee.org/document/10197026)
```
@inproceedings{avan2023robust,
  title={A Robust Scheduling Algorithm for Overload-Tolerant Real-Time Systems},
  author={Avan, Amin and Azim, Akramul and Mahmoud, Qusay H},
  booktitle={2023 IEEE 26th International Symposium on Real-Time Distributed Computing (ISORC)},
  pages={1--10},
  year={2023},
  organization={IEEE}
}
```
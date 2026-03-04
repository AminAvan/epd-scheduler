"""
================================================================================
Least Laxity First (LLF) Scheduling Algorithm - Overload Edition
================================================================================
Author      : Amin Avan
--------------------------------------------------------------------------------
DESCRIPTION:
    This program implements the Least Laxity First (LLF) algorithm, adapted for
    overloaded workloads where total CPU utilization exceeds 1 (i.e., > 100%).

    LLF assigns the highest priority at each time tick to the task with the
    smallest laxity value, where laxity is defined as:

        laxity = deadline - current_time - remaining_execution

    A laxity of '0' means the task must run continuously from now to meet its
    deadline with no slack remaining. A negative laxity means the task can
    no longer meet its deadline regardless of scheduling; it is immediately
    dropped and logged as missed.

--------------------------------------------------------------------------------
ALGORITHM OVERVIEW:
    1.  Load tasks from input_workload1.csv (columns: execution, deadline,
        period). Task numbers are assigned from the CSV enumerate index
        starting at 1, not from the CSV data itself.
    2.  Compute utilization = sum(execution / period) for all tasks.
    3.  Collect task periods and compute LCM (hyperperiod). If LCM equals
        the maximum value found across all fields of all workload tuples
        (not just deadlines), triple the LCM to avoid edge-case gaps.
    4.  Expand each task into individual job instances across the hyperperiod.
        For iteration > 1, each job's absolute deadline is adjusted as:
            deadline = base_deadline + (iteration - 1) * period
    5.  Populate ThrDExe[task][job][slot] with job instances (jp starts at 1,
        correctly matching actual task numbers). Remove placeholder '#'
        entries from the end of each task's job list.
    6.  Simulate tick by tick from 0 to lcm-1:
        a. For each j in range(jj) — note jj uses the previous tick's task
           count, not the current one:
             - If j < len(ThrDExe): compute
               lax = deadline - (current_tick + remaining_execution).
             - If j >= len(ThrDExe): lax is NOT recomputed; it retains its
               stale value from the previous loop step. This stale lax may
               then pass the lax >= 0 check and be incorrectly appended to
               the laxity candidate list.
             - If lax < 0 AND j < len(ThrDExe): task has missed its deadline.
               Log it in misdTsksdtl and misdTsks, then execute
               del ThrDExe[j] — this deletes the ENTIRE task row (all
               remaining job instances), not just the current job instance.
               All subsequent ThrDExe indices shift down after this deletion,
               meaning remaining j values in the same loop pass now reference
               different tasks than intended.
             - If lax >= 0: append lax to laxity list and update index_min
               to the position of the current minimum in laxity.
        b. After the inner loop, if laxity was never populated (all tasks
           dropped), index_min is undefined and line 197 raises a NameError.
           There is no empty-laxity guard.
        c. Decrement ThrDExe[index_min][0][1].execution by 1.
        d. Count a context switch if TimLin[-1] (previous task number) differs
           from the current task's number AND current remaining execution > 0.
        e. Append current task number to TimLin.
        f. If execution reaches '0' AND deadline <= current_tick:
           append task to misdTsks as a second missed-deadline check.
           NOTE: deadline <= i when execution just hit 0 means a task
           completing exactly at its deadline tick (deadline == i) is also
           flagged as missed; a likely off-by-one error.
        g. If execution reaches 0: remove current job instance
           (del ThrDExe[index_min][0]). The next job instance becomes active.
        h. Update jj = len(ThrDExe) for the next tick's loop range.
    8.  Write results to LLF_output.txt.

--------------------------------------------------------------------------------
INPUT (input_workload1.csv):
    Header row followed by task rows:
        execution_time, deadline, period
    Task numbers are assigned from the CSV enumerate index (starting at 1).

OUTPUT (LLF_output.txt):
    - Task count and workload summary
    - CPU utilization
    - Task periods list
    - Hyperperiod (LCM)
    - Per-miss log: "Task X ignored as its laxity is negative at tick Y"
    - Total number of context switches
    - LCM value (printed a second time at end of output)
    - List of all missed task numbers
    NOTE: The per-tick timeline (TimLin) is collected during simulation but
    its output lines are commented out — it does not appear in the output file.

--------------------------------------------------------------------------------
KEY DATA STRUCTURES:
    - tasks[]        : Task objects loaded from CSV.
    - execution[]    : Flat list of all job instances with adjusted deadlines.
    - ThrDExe[][][]  : 3D live scheduling queue: ThrDExe[task][job][slot],
                       where slot 0 = task number, slot 1 = Task object.
    - laxity[]       : Per-tick list of laxity values for candidate tasks.
    - index_min      : Index of minimum laxity in the laxity list, which is
                       also used directly as an index into ThrDExe. These
                       two meanings are only equivalent when no mid-loop
                       deletions have shifted ThrDExe indices.
    - TimLin[]       : Timeline log of task numbers executed per tick
                       (file output is commented out).
    - misdTsks[]     : Task numbers that missed deadlines. May contain
                       duplicates: once from negative laxity, and again
                       if execution reaches 0 with deadline <= current tick.
    - misdTsksdtl[]  : (task_number, time_tick) tuples for laxity-based
                       miss events only.

--------------------------------------------------------------------------------
DEPENDENCIES:
    - numpy   : LCM computation via np.lcm.reduce()
    - copy    : Shallow copying Task objects to prevent shared state mutation
                across job instances
    - csv     : Parsing the input workload CSV file
    - math, sys, operator, pprint : Imported but never used in this file
================================================================================
"""

import numpy as np
import copy
import operator
import sys
import csv
import math
import pprint



# Defining class


def ThreeD(a, b, c):
    lst = [[ ['#' for col in range(a)] for col in range(b)] for row in range(c)]
    return lst

class Task:
    def __init__(self, number, execution, deadline, period, window=0, currentTime=0, passmiss='not determined'):
        super().__init__()
        self.number = number
        self.execution = execution
        self.deadline = deadline
        self.period = period
        self.window = window
        self.passmiss = passmiss
        self.currentTime = currentTime

    def __str__(self):
        return "[%s, %s, %s, %s, %s, %s]" % (self.number, self.execution, self.deadline, self.period, self.currentTime, self.passmiss)

    def __repr__(self):
        return "[%s, %s, %s, %s, %s, %s]" % (self.number, self.execution, self.deadline, self.period, self.currentTime, self.passmiss)

    def test(self):
        print("Task number: {}".format(self.number))
        print("Execution/processing time: {}".format(self.execution))
        print("Deadline: {}".format(self.deadline))
        print("Period: {}".format(self.period))
        print("Execution window: {}".format(self.window))


# Variables
tasks_count = 0
tasks = []
workload = []
tasks_periods = []
utilization = 0
current_time = 0
schedulable = 'pass'
maxPeriod = 0
missedTasks = []

# Creating output
output = open('LLF_output.txt', 'w')

# Loading csv file
file = open('input_workload1.csv', 'rt')
reader = csv.reader(file)

for index, row in enumerate(reader):
    # Skipping CSV header row
    if index > 0:

        # Setting number of tasks
        tasks_count += 1

        # Creating task and appending to array
        task = Task(int(index), int(row[0]), int(row[1]), int(row[2]))
        tasks.append(task)

        #Creating workload for printing in output file
        workload_task = int(index), int(row[0]), int(row[1]), int(row[2])
        workload.append(workload_task)

file.close()

print("Tasks count:", tasks_count, file=output)
print("Workload:", workload, file=output)

# Checking utilization and schedulability
# if feasible, calculate execution
for i in range(tasks_count):
    utilization += float(tasks[i].execution / tasks[i].period)

print("Utilization:", utilization, file=output)

if utilization > 1:
    #print("Schedulable: NO", file=output)
    # Getting tasks periods
    for i in range(tasks_count):
        tasks_periods.append(tasks[i].period)
    print("Periods: {}".format(tasks_periods), file=output)
    print("Periods: {}".format(tasks_periods))

    # Finding the "Least Common Multiple" between the deadlines of tasks in the workload
    lcm = np.lcm.reduce(tasks_periods)
    mxddl = -1
    for i in range(len(workload)):
        if (mxddl < max(workload[i])):
            mxddl = max(workload[i])
    # print("mxddl",mxddl)
    if lcm == mxddl:
        lcm = (3 * lcm)
    print("Common time between tasks in the workload for scheduling the workload: {}".format(lcm), file=output)
    print("======================================================", file=output)

    # Creating execution list by task period
    execution = []

    for i in range(tasks_count):
        iteration = 1
        while True:
            if iteration * tasks[i].period <= lcm:
                execution_window = iteration * tasks[i].period

                # using copy to break inheritance
                tasks[i].window = execution_window
                execution.append(copy.copy(tasks[i]))

                if iteration > 1:
                    # -1 gets the last element of the array
                    item = execution[-1]
                    item.deadline = item.deadline + (iteration - 1) * (item.period)

                iteration += 1
            else:
                break

    max_itr = 0
    itr_1 = 0

    for j in range(tasks_count):
        itr_1 = 0
        for i in range(len(execution)):
            if (execution[i].number == j):
                itr_1 = itr_1 + 1
        if (max_itr < itr_1):
            max_itr = itr_1

    col1 = 2
    col2 = max_itr
    row = len(workload)
    ThrDExe = ThreeD(col1, col2, row)

    jp = 1
    jpp = 0
    for j in range(tasks_count):
        jpp = 0
        for i in range(len(execution)):
            if (execution[i].number == jp):
                ThrDExe[j][jpp][0] = execution[i].number
                ThrDExe[j][jpp][1] = execution[i]
                jpp = jpp + 1
        jp = jp + 1

    # for kk in range(len(ThrDExe)):
    #     print(ThrDExe[kk])
    #print("\/\/\/\/\/\/\/\/")

    TimLin = [] # timeline of the scheduling algorithm
    CxSw = 0 # context switching
    misdTsks = []
    misdTsksdtl = []
    jj = tasks_count

    delItmji = []
    for j in range(len(ThrDExe)):   #eliminating all ['#','#'] from ThrDExe
        delIt = -1
        for i in range(max_itr):
            if ((ThrDExe[j][i][0] == "#") and (delIt == -1)):
                delIt = 1
                delItmji.append([j,i])
    for i in range(len(delItmji)):
        del ThrDExe[delItmji[i][0]][delItmji[i][1]:]

    #for i in range(lcm):
    for i in range(lcm):
        laxity = []
        # print("available tasks:",jj)
        # print("current time:",i)
        if (len(ThrDExe) > 0):
            for j in range(jj):
                if (j < len(ThrDExe)):
                    lax = ThrDExe[j][0][1].deadline - (i + ThrDExe[j][0][1].execution)
                # print("Task:",ThrDExe[j][0][1].number, ", Laxity:", lax)
                if (lax < 0) and (j < len(ThrDExe)):
                    misdTsksdtl.append((ThrDExe[j][0][1].number,i))
                    misdTsks.append(ThrDExe[j][0][1].number)
                    del ThrDExe[j]
                    if ([] in ThrDExe):
                        ThrDExe.remove([])
                if (lax >= 0):
                    laxity.append(lax)
                if (len(laxity) > 0):
                    index_min = min(range(len(laxity)), key=laxity.__getitem__)
            ThrDExe[index_min][0][1].execution = ThrDExe[index_min][0][1].execution - 1
            if (len(TimLin) > 0):
                if ((TimLin[-1] != ThrDExe[index_min][0][1].number) and (ThrDExe[index_min][0][1].execution > 0)):
                    CxSw = CxSw + 1
            TimLin.append(ThrDExe[index_min][0][1].number)
            if (ThrDExe[index_min][0][1].execution == 0):
                if (ThrDExe[index_min][0][1].deadline <= i):
                    misdTsks.append(ThrDExe[index_min][0][1].number)
            if (ThrDExe[index_min][0][1].execution == 0):
                del ThrDExe[index_min][0]
            if ([] in ThrDExe):
                ThrDExe.remove([])
            jj = len(ThrDExe)

            # for kk in range(len(ThrDExe)):
            #     print(ThrDExe[kk])
            # print(TimLin)
            # print(CxSw)
            #print("=====================================================================================")

    # print(TimLin)
    # for i in range(len(TimLin)):
    #     print("Task",TimLin[i],"execute at",i, file=output)
    # print("======================================================", file=output)
    for i in range(len(misdTsksdtl)):
        print("Task", misdTsksdtl[i][0], "ignored as its laxity is negative at", misdTsksdtl[i][1], file=output)
    print("======================================================", file=output)
    print("Number of context switching:",CxSw, file=output)
    print("Common time (Least Common Multiple (LCM)) between tasks in the workload for scheduling the workload: {}".format(lcm), file=output)
    print("missed tasks:", misdTsks, file=output)


    #print("\nTimeline: ", file=output)
    # print("\n========================================================================", file=output)
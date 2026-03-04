"""
================================================================================
Earliest Possible Deadline (EPD) Scheduling Algorithm - Overload Edition
================================================================================
Author      : Amin Avan
--------------------------------------------------------------------------------
DESCRIPTION:
    This program implements Earliest Possible Deadline (EPD), a novel real-time
    scheduling algorithm. It is specifically designed to manage overloaded workload
    (where total utilization exceeds 100%) while maintaining effective scheduling under
    normal load conditions.

    At each time tick, EPD evaluates every active task's feasibility by
    computing a "possibility" value:

        possibility = remaining_execution / remaining_time_to_deadline (rtd)

    - If possibility > 1  : the task cannot finish before its deadline →
                            it is immediately dropped and logged as missed.
    - If 0 < possibility ≤ 1 : the task is still feasible. Among all feasible
                            tasks, the one with the *earliest deadline* is
                            selected for execution at that tick.

--------------------------------------------------------------------------------
IMPORTANT - OVERLOAD CONDITION (utilization > 1 gate):
    ALL scheduling logic runs only if utilization < 1. If utilization >= 1,
    the program prints utilization to the output file and stops. EPD is designed
    to function effectively under both normal and overloaded workloads.

--------------------------------------------------------------------------------
ALGORITHM OVERVIEW:
    1.  Load tasks from input_workload1.csv (columns: execution, deadline,
        period). Task numbers are assigned from the CSV enumerate index
        starting at 1, not from the CSV data itself.
    2.  Collect task periods and compute LCM (hyperperiod). If LCM equals
        the maximum value found across all fields of all workload tuples,
        triple the LCM to avoid edge-case scheduling gaps.
    3.  Expand each task into individual job instances across the hyperperiod.
        For iteration > 1, each job's absolute deadline is adjusted as:
            deadline = base_deadline + (iteration - 1) * period
    4.  Organize all job instances into a 3D list ThrDExe[task][job][slot],
        where slot 0 = task number, slot 1 = Task object. Remove placeholder
        '#' entries that were pre-filled during initialization.
    5.  Simulate tick by tick from 0 to lcm-1:
        a. For each active task, compute rtd = task.deadline - current_tick:
             - rtd < 0  : deadline passed → mark missed, drop from ThrDExe.
             - rtd == 0 : task is added to possibility list but psb value used
                          is stale (leftover from previous computation) because
                          the rtd > 0 branch (which updates psb) is skipped.
                          The inner check "deadline < i" is always False when
                          rtd == 0, so no task is dropped here.
             - rtd > 0  : compute psb = execution / rtd (4 decimal places),
                          add [task_number, deadline, psb] to possibility list.
        b. Remove any empty entries from ThrDExe and possibility.
        c. Sort possibility by deadline (earliest first).
        d. Scan possibility: any task with psb > 1 is marked missed and
           dropped. Its entry in possibility is replaced with [-1,-1,-1]
           then removed.
        e. From the remaining possibility list, check possibility[0]:
           if 0 < psb ≤ 1, select that task (earliest deadline among
           feasible tasks) and decrement its execution by 1.
           Note: if possibility is empty at this point, an IndexError
           will occur — there is no empty-list guard.
        f. Count a context switch if the running task differs from the
           previous tick and the previous task had remaining execution > 0.
        g. Append [task_number, remaining_execution] to TimLin.
        h. If selected task's execution reaches 0, remove its current job
           instance. The next job instance for that task becomes active.
        i. Update jj = len(ThrDExe) for the next tick's loop range.
    7.  Write results to EPD_output_1.txt.

--------------------------------------------------------------------------------
INPUT (input_workload1.csv):
    Header row followed by task rows:
        execution_time, deadline, period

OUTPUT (EPD_output_1.txt):
    - Task count and workload summary
    - CPU utilization
    - Hyperperiod (LCM)
    - A heading line "Task [Task i, Remaining execution...] execute at Time"
      (NOTE: the actual per-tick data rows under this heading are commented
      out in the code, so this heading appears with no data beneath it)
    - Per-miss log: task number and the tick it was dropped
    - Total context switches
    - List of all missed task numbers

--------------------------------------------------------------------------------
KEY DATA STRUCTURES:
    - tasks[]        : Task objects loaded from CSV.
    - execution[]    : Flat list of all job instances with adjusted deadlines.
    - ThrDExe[][][]  : 3D live scheduling queue: ThrDExe[task][job][slot].
    - possibility[]  : Per-tick candidate list [task_number, deadline, psb].
    - TimLin[]       : Timeline log [task_number, remaining_execution] per tick.
    - misdTsks[]     : Task numbers that missed their deadline (duplicates
                       are NOT filtered; a task can appear multiple times).
    - misdTsksdtl[]  : (task_number, time_tick) tuples for each miss event.

--------------------------------------------------------------------------------
DEPDNDENCIES:
    - numpy   : LCM via np.lcm.reduce()
    - copy    : Shallow copying Task objects to prevent shared state mutation
    - csv     : Parsing input CSV
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
LowestDeadline = 0

# Creating output
output = open('EPD_output_1.txt', 'w')

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
print("Utilization:", utilization)

if utilization > 1:
    # Getting tasks periods
    for i in range(tasks_count):
        tasks_periods.append(tasks[i].period)
    print("Periods: {}".format(tasks_periods), file=output)

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
            if (execution[i].number == (j+1)):
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

    # print(ThrDExe[0])
    # print(ThrDExe[0][0])
    # print(ThrDExe[0][0][1].deadline)
    # print(ThrDExe[0])
    # print(ThrDExe[1])
    # print(ThrDExe[2])
    # print("\/\/\/\/\/\/\/\/")

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

    # for kk in range(len(ThrDExe)):
    #     print(ThrDExe[kk])
    # print("\/\/\/\/\/\/\/\/")
    psb = 0
    for i in range(lcm):
        possibility = []
        # print("available tasks:",jj)
        # print("current time:",i)
        if (len(ThrDExe) > 0):
            for j in range(jj):
                rtd = (ThrDExe[j][0][1].deadline - i)
                if (rtd == 0):
                    if (ThrDExe[j][0][1].deadline < i):
                        misdTsksdtl.append((ThrDExe[j][0][1].number, i))
                        misdTsks.append(ThrDExe[j][0][1].number)
                        # print("(rtd < 0)misdTsks")
                        ThrDExe[j] = []
                elif (rtd > 0):
                    psb = ThrDExe[j][0][1].execution / (rtd)
                    psb = float("{0:.4f}".format(psb))
                elif (rtd < 0):
                    misdTsksdtl.append((ThrDExe[j][0][1].number, i))
                    misdTsks.append(ThrDExe[j][0][1].number)
                    # print("(rtd < 0)misdTsks")
                    ThrDExe[j] = []
                if (rtd >= 0):
                    possibility.append([ThrDExe[j][0][1].number,ThrDExe[j][0][1].deadline,psb])

            jj = len(ThrDExe)
            while ([] in ThrDExe): # new
                ThrDExe.remove([]) # new
            while ([] in possibility): # new
                possibility.remove([]) # new
            #print("un-sorted possibility:",possibility)
            possibility.sort(key=lambda x: x[1])
            # print("sorted possibility:", possibility)
            for iii in range(len(possibility)):
                if (possibility[iii][2] > 1):
                    for mk in range(len(ThrDExe)):
                        if (ThrDExe[mk][0][0] == possibility[iii][0]):
                            iiidel = mk
                            # print("iiidel",iiidel)
                            # print("possibility[0]",possibility[0])
                    misdTsksdtl.append((ThrDExe[iiidel][0][1].number, i))
                    misdTsks.append(ThrDExe[iiidel][0][1].number)
                    ThrDExe[iiidel] = []
                    while ([] in ThrDExe):  # new
                        ThrDExe.remove([])  # new
                    #print("possibility[iii]",possibility[iii])
                    #print("208-possibility",possibility, "and iii",iii)
                    possibility[iii] = [-1, -1, -1]
                    #print("208-possibility", possibility)
            for iii in range(len(possibility)):
                if (possibility[iii] == [-1,-1,-1]):
                    possibility[iii] = []
            while ([] in possibility):
                possibility.remove([])
            while ([] in possibility):
                possibility.remove([])

            if (0 < (possibility[0][2]) <= 1):
                # print("1st-possibility:", possibility)
                #print("Time: ", i)
                #for m in range(len(ThrDExe)):
                #    print("m: ",m)
                #    print("possibility[0][0]",possibility[0][0])
                #    print("ThrDExe[m][0][1]: ",ThrDExe[m][0][1])
                #    for pos in range(len(possibility)):
                #        print("possibility", possibility[pos])
                #print("=====================================================================================")
                for m in range(len(ThrDExe)):
                    if (ThrDExe[m][0][0] == possibility[0][0]):
                        slcIndx = m
                        ThrDExe[slcIndx][0][1].execution = ThrDExe[slcIndx][0][1].execution - 1
                        # print("selected task",slcIndx)



            if (len(TimLin) > 0):
                # print("possibility:",possibility)
                # print("236-slcIndx:",slcIndx)
                # print("======================")
                if ((TimLin[-1][0] != ThrDExe[slcIndx][0][1].number) and (TimLin[-1][1] > 0)):
                    CxSw = CxSw + 1

            TimLin.append([ThrDExe[slcIndx][0][1].number,ThrDExe[slcIndx][0][1].execution])

            # if (ThrDExe[index_min][0][1].execution == 0):
            #     if (ThrDExe[index_min][0][1].deadline <= i):
            #         misdTsks.append(ThrDExe[index_min][0][1].number)
            if (ThrDExe[slcIndx][0][1].execution == 0):
                del ThrDExe[slcIndx][0]
            if ([] in ThrDExe):
                ThrDExe.remove([])
            jj = len(ThrDExe)
            #print("missed tasks:", misdTsks)
            # for kk in range(len(ThrDExe)):
            #     print(ThrDExe[kk][0])
            # #print("TimLin",TimLin)
            # print("CxSw:",CxSw)
            # print("=====================================================================================")

    #print(TimLin, file=output)
    print("Task [Task i, Remaining execution of Task i] execute at Time", file=output)
    # for i in range(len(TimLin)):
    #     print("Task",TimLin[i],"execute at",i, file=output)
    # print("======================================================", file=output)
    for i in range(len(misdTsksdtl)):
        print("Task", misdTsksdtl[i][0], "ignored as it cannot execute regarding Remaining Time to its Deadline & its needed Execution Time at", misdTsksdtl[i][1], file=output)
    print("======================================================", file=output)
    print("Common time between tasks in the workload for scheduling the workload: {}".format(lcm), file=output)
    print("Number of context switching:",CxSw, file=output)
    print("missed tasks:", misdTsks, file=output)
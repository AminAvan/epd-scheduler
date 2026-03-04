"""
================================================================================
Rate Monotonic (RM) Scheduling Algorithm - Overload Edition
================================================================================
Author      : Amin Avan
--------------------------------------------------------------------------------
DESCRIPTION:
    This program implements the Rate Monotonic (RM) real-time scheduling
    algorithm, a fixed-priority preemptive scheduling policy where tasks with
    shorter periods are assigned higher priorities. 
    The "Overload Edition" extends the base RM algorithm by detecting and
    reporting deadline misses when the total CPU utilization exceeds the
    Liu & Layland schedulability bound.

--------------------------------------------------------------------------------
ALGORITHM OVERVIEW:
    1. Load task workload from a CSV input file (input_workload1.csv).
    2. Compute total CPU utilization and compare against the Liu & Layland
       bound: U ≤ n * (2^(1/n) - 1), where 'n' is the number of tasks.
    3. Compute the Least Common Multiple (LCM) of all task periods to define
       the scheduling hyperperiod window.
    4. Expand each task into its individual job instances across the hyperperiod,
       adjusting each job's deadline relative to its release iteration.
    5. Organize all job instances into a 3D structure (ThrDExe), grouped by
       task, and trim placeholder entries.
    6. Build a priority array sorted by each task's first-job deadline
       (assumes implicit deadlines, i.e. deadline == period).
    7. Simulate scheduling tick-by-tick across the hyperperiod:
         - At each tick, select the highest-priority task with remaining execution.
         - Decrement its remaining execution time.
         - Record a deadline miss if the current time exceeds the job's deadline.
         - Count context switches when the running task changes.
         - Remove completed jobs when execution reaches 0 at their deadline.
    8. Write results to RM_output.txt.

--------------------------------------------------------------------------------
INPUT (input_workload1.csv):
    A CSV file with a header row followed by task rows in the format:
        execution_time, deadline, period
    Example:
        execution,deadline,period
        1,4,4
        2,6,6

OUTPUT (RM_output.txt):
    - Task count and workload summary
    - CPU utilization value
    - List of missed task numbers
    - Total context switch count

--------------------------------------------------------------------------------
DEPENDENCIES:
    - numpy   : LCM computation via np.lcm.reduce()
    - copy    : Shallow copying task objects per job instance to avoid
                shared state across iterations
    - csv     : Parsing the input workload CSV file
    - math, sys, operator, pprint : Imported but not actively used

--------------------------------------------------------------------------------
KNOWN LIMITATIONS / NOTES:
    - Priority is ordered by the first job instance's deadline, which aligns
      with RM only when deadline == period (implicit deadline task model).
    - The LCM is tripled if it equals the maximum value found across all
      task parameters (not just deadlines), to avoid edge-case scheduling gaps.
    - Only the first deadline miss per task number is recorded in misdTsksdtl.
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
output = open('RM_output.txt', 'w')

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
print("Tasks count:", tasks_count)
print("Workload:", workload,'\n')

# Checking utilization and schedulability
# if feasible, calculate execution
for i in range(tasks_count):
    utilization += float(tasks[i].execution / tasks[i].period)

print("Utilization:", utilization, file=output)
print("Utilization:", utilization)
liuLayland = (tasks_count)*(2**(1/tasks_count)-1)
print("Liu & Layland schedulability analysis:",liuLayland)
if (utilization <=liuLayland):
    print("Workload is schedulable with RM as {utilization:",utilization,"} <= {L&L:",liuLayland,"}",'\n')
elif (utilization > liuLayland):
    print("Workload might or might not be schedulable with RM as {utilization:", utilization, "} > {L&L:", liuLayland, "}",'\n')


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
#print("mxddl",mxddl)
if lcm == mxddl:
    lcm = (3 * lcm)

print("lcm:",lcm)
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


TimLin = [] # timeline of the scheduling algorithm
CxSw = 0 # context switching
misdTsks = []
misdTsksdtl = []
slcTsk = 0
arrPriority = []

for i in range(len(ThrDExe)):
    arrPriority.append([ThrDExe[i][0][1].number, ThrDExe[i][0][1].deadline])
arrPriority.sort(key=lambda x: x[1])


for i in range(lcm):
    # print("current time: ",i)
    # print("Priority", arrPriority)
    blslc = True
    # for kk in range(len(ThrDExe)):
    #     print(ThrDExe[kk])

    for m in range(len(arrPriority)):
        for j in range(len(ThrDExe)):
            if (arrPriority[m][0] == ThrDExe[j][0][1].number) and (ThrDExe[j][0][1].execution > 0) and (blslc == True):
                minTsk = ThrDExe[j][0][1].deadline
                slcTsk = j
                blslc = False
    # print("selected task",slcTsk)

    if(len(ThrDExe)>0):
        ThrDExe[slcTsk][0][1].execution = ThrDExe[slcTsk][0][1].execution - 1
    if ((len(TimLin) > 0) and (len(ThrDExe)>0)):
        if ((TimLin[-1][0] != ThrDExe[slcTsk][0][1].number) and (TimLin[-1][1] > 0)):
            CxSw = CxSw + 1
    if (len(ThrDExe) > 0):
        # print("ThrDExe[slcTsk][0][1].deadline",ThrDExe[slcTsk][0][1].deadline)
        if (ThrDExe[slcTsk][0][1].deadline >= i):
            TimLin.append([ThrDExe[slcTsk][0][1].number, ThrDExe[slcTsk][0][1].execution,"",i])
        else:
            TimLin.append([ThrDExe[slcTsk][0][1].number, (ThrDExe[slcTsk][0][1].execution + 1), "Miss",i])
            if ((ThrDExe[slcTsk][0][1].number not in misdTsks) == True):
                misdTsks.append(ThrDExe[slcTsk][0][1].number)
                misdTsksdtl.append([ThrDExe[slcTsk][0][1].number,"missed at",i])

    if (len(ThrDExe)>0):
        for x in range(len(ThrDExe)):
            if ((ThrDExe[x][0][1].execution == 0) and (ThrDExe[x][0][1].deadline == (i+1))):
                del ThrDExe[x][0]
    if ([] in ThrDExe):
        ThrDExe.remove([])
    # print("TimLin", TimLin)
    # print("CxSw", CxSw)
    # for kk in range(len(ThrDExe)):
    #     print(ThrDExe[kk])
    # print("=============================================================")

#print("TimLin",TimLin)
print("Missed Tasks",misdTsks)
print("Missed Tasks",misdTsks,file=output)
#print("Missed Tasks detail:",misdTsksdtl)
print("Common time between tasks in the workload for scheduling the workload: {}".format(lcm))
print("CxSw",CxSw)
print("CxSw",CxSw,file=output)
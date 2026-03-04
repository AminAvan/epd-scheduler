"""
================================================================================
Earliest Deadline First (EDF) Scheduling Algorithm - Overload Edition
================================================================================
DESCRIPTION:
    This program implements the Earliest Deadline First (EDF) algorithm for
    overloaded workloads (utilization > 1).

    All job instances across the hyperperiod are sorted into EDF order, and
    each job's start time is computed as the cumulative sum of all preceding
    jobs' execution times. Each job is then checked once; if its computed
    start time exceeds its deadline, it is marked as a miss. This assumes
    a non-preemptive processor that never idles between jobs.

--------------------------------------------------------------------------------
ALGORITHM OVERVIEW:
    1.  Load tasks from input_workload1.csv (columns: execution, deadline,
        period). Task numbers are assigned from the CSV enumerate index
        starting at 1, not read from the CSV data itself.
    2.  Compute utilization = sum(execution / period) for all tasks.
    3.  Collect task periods and compute LCM (hyperperiod). If LCM equals
        the maximum value found across all fields of all workload tuples,
        triple the LCM to avoid edge-case gaps.
    4.  Expand each task into individual job instances across the hyperperiod.
        For iteration > 1, each job's absolute deadline is adjusted as:
            deadline = base_deadline + (iteration - 1) * period
    5.  Sort all job instances in two passes (Python sort is stable):
        - First pass : sort by period descending.
        - Second pass: sort by deadline ascending.
        Effective final order: deadline ascending (primary),
        period descending (tiebreaker for equal deadlines).
    6.  Traverse the sorted list to assign start times and check deadlines:
        - Job at position 0: currentTime stays 0 (the if i >= 1 block
          is skipped), so it always passes (deadline is always > 0).
        - Job at position i >= 1: current_time accumulates all preceding
          jobs' execution times. This represents the wall-clock start time
          of job i assuming no processor idle time between jobs.
        - If currentTime <= deadline: mark "Pass".
        - If currentTime > deadline:  mark "Miss", set schedulable = 'miss'.
        - currentTime == deadline is treated as a Pass (uses <= not <).
    7.  Collect unique missed task numbers into missedTasks. Each task number
        appears at most once (deduplication check on line 148).
    8.  Write results to EDF_output.txt.

--------------------------------------------------------------------------------
INPUT (input_workload1.csv):
    Header row followed by task rows:
        execution_time, deadline, period

OUTPUT (EDF_output.txt) — all output goes to file only, none to console:
    Always written (regardless of utilization):
    - Task count and workload
    - CPU utilization
    Written only if utilization > 1:
    - Task periods list
    - Hyperperiod (LCM)
    - "Timeline:" section header
    - Separator line
    - "Results:" section header with field-name label
      (per-task detail rows are commented out — line 144)
    - List of missed task numbers
    - Overall verdict: "All the tasks in the workload pass/miss their deadlines"
    Written only if utilization <= 1:
    - "Schedulable: YES"

--------------------------------------------------------------------------------
DEPENDENCIES:
    - numpy    : LCM computation via np.lcm.reduce()
    - copy     : Shallow copying Task objects per job instance to prevent
                 shared state mutation across iterations
    - operator : attrgetter() used for sorting by period and deadline
    - csv      : Parsing the input workload CSV file
    - sys      : Imported but never used
================================================================================
"""



import numpy as np
import copy
import operator
import sys
import csv


# Defining class
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
output = open('EDF_output.txt', 'w')

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

    # Converting python array to numpy array
    # execution = np.array(execution)

    # Sorting by execution period (inverse) and by deadline and updating the current time
    execution = sorted(execution, key=operator.attrgetter('period'), reverse=True)
    execution = sorted(execution, key=operator.attrgetter('deadline'))

    for i in range(len(execution)):
        if i >= 1:
            current_time += execution[i-1].execution
            execution[i].currentTime = current_time

        if execution[i].currentTime <= execution[i].deadline:
            execution[i].passmiss = "Pass"
        else:
            execution[i].passmiss = "Miss"
            schedulable = 'miss'

    # Result
    print("\nTimeline: ", file=output)
    print("\n===========================================================================================", file=output)
    print("\nResults: ", file=output)
    print("[task's order in workload, execution time, deadline, period, current time, task Pass or Miss the deadline?]"
          , file=output)
    #print(*execution, sep="\n", file=output) #print timeline detail

    for i in range(len(execution)):
        if (execution[i].passmiss == "Miss"):
            if (((execution[i].number) in missedTasks) == False):
                missedTasks.append(execution[i].number)
    print(missedTasks, "miss their deadlines", file=output)

    print("\nAll the tasks in the workload", schedulable, "their deadlines.", file=output)

else:
    print("Schedulable: YES", file=output)
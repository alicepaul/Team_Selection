import numpy as np
import pandas as pd
import picos as pic
from optimizeIP_repeat import optimize_repeat
import time
import string

"""
Optimization using integer programming formulation with PICOS
does not have active comparison with process3.py

Author: Daniel Suh, Summer 2018
"""

####################### Project and Student Global Variables ###########################

# Files to read in
SURVEY_FILE = 'Data/survey_anon17.csv'
STUDENT_FILE = 'Data/students_anon17.csv'

# Project names
PROJECT_NAMES = ['project [1]', 'project [2]', 'project [3]', 'project [4]', 'project [5]', 'project [6]',
                 'project [7]', 'project [8]', 'project [9]', 'project [10]', 'project [11]', 'project [12]',
                 'project [13]', 'project [14]']
num_projects = len(PROJECT_NAMES)
# Create index dictionary for IP indexing
project_index = dict()
for i in range(num_projects):
    project_index[PROJECT_NAMES[i]] = i

# Minimum and maximum number of students per project
MINSTAFF = 5
MAXSTAFF = 6

# Projects allowed to go below the minimum
MINSTAFF_EXCEPTIONS = {
    # unknown for other years!
}
# Create dictionary for min_staff according to exceptions
minstaff_projects = {}
for name in PROJECT_NAMES:
    if name not in MINSTAFF_EXCEPTIONS.keys():
        minstaff_projects[name] = MINSTAFF
    else:
        minstaff_projects[name] = MINSTAFF_EXCEPTIONS[name]

# Projects allowed to go above the maximum
MAXSTAFF_EXCEPTIONS = {
    # unknown for other years!
}
# Create dictionary for MAXSTAFF_PROJECTS according to exceptions
maxstaff_projects = {}
for name in PROJECT_NAMES:
    if name not in MAXSTAFF_EXCEPTIONS.keys():
        maxstaff_projects[name] = MAXSTAFF
    else:
        maxstaff_projects[name] = MAXSTAFF_EXCEPTIONS[name]

# Students locked onto a project 
LOCKED_STUDENTS = []
#   '(locked student token)', 'project [#]'), # reason: mentor really wants him/her


# Students barred from a project 
BARRED_STUDENTS = []
#    ('(barred student token)', 'project [#]'), # reason: non-US citizenship / visa expiry / other

# Citizenship/visa-affected projects
# US citizens only projects, by name
CITIZEN_REQ = []
# US citizens or visa holders only projects
VISA_REQ = []

# Cost constants
# note: pref costs in string form due to working with dictionary below
PREF_COST_5 = '0'
PREF_COST_4 = '1'
PREF_COST_3 = '5'
PREF_COST_2 = '1000'
PREF_COST_1 = '10000'

# Low GPA bar
MIN_GPA = 3.0 # we can change this later to 10th percentile, this is a default

# Maximum number of solutions to extract from the integer program
# this will ask gurobi to find the top # best solutions
SOLUTION_LIMIT = 100

# Maximum number of solutions to take that are pairwise most diverse
DIVERSE_LIMIT = 10

####################### Reading and Processing the Data ###########################

# Extract data from survey_anon.csv, token used as index column
df_survey = pd.read_csv(SURVEY_FILE, index_col='Token')

# Extract data from students_anon.csv, ID Number (same as token) used as index column
df_student = pd.read_csv(STUDENT_FILE, index_col='ID Number')

# Create list of student tokens and an index array for IP (use row index for consistency)
num_students = df_survey.shape[0]
tokens = []
token_index = dict()
i = 0
for index, _ in df_survey.iterrows():
    tokens.append(index)
    token_index[index] = i
    i += 1

# Create dictionary for penalties
# TODO: revise dictionaries to reflect penalties above for sensitivity analysis if not already done so
penalty_dict = {1: PREF_COST_1, 2: PREF_COST_2, 3: PREF_COST_3, 4: PREF_COST_4, 5: PREF_COST_5}

# Manipulation of preferences to map to penalties and store in a numpy array
df_penalty = df_survey[PROJECT_NAMES].copy()
for name in PROJECT_NAMES:
    df_penalty[name].replace(penalty_dict,inplace=True)   
df_penalty_np = df_penalty.values
penalties = df_penalty_np.astype(np.int)

# Create dictionary of antiprefs:
# Index of token (student shooting bullet) to index of token (student receiving bullet)
antiprefs_dict_1 = {}
antiprefs_dict_2 = {}

for token in tokens:
    token_row = token_index[token]
    # obtain antipref tokens
    a1 = df_survey.at[token, 'bullets [1]']
    a2 = df_survey.at[token, 'bullets [2]']
    # find the index at which the antiprefs reside
    # revise antiprefs accordingly
    if pd.notnull(a1):
        antiprefs_dict_1[token_row] = token_index[a1]
    if pd.notnull(a2):
        antiprefs_dict_2[token_row] = token_index[a2]

# Get student GPAs and mark if below MIN_GPA
stu_gpas_np = df_student['Cumulative GPA'].values
# Optionally alter MIN_GPA to 10th percentile of GPAs
#MIN_GPA = np.percentile(stu_gpas_np, 10)
stu_gpa_indic = [1 if indiv_gpa <= MIN_GPA else 0 for indiv_gpa in stu_gpas_np]

# Add non-citizens or visa holder banned assignments
citizen_bans = []
for token in tokens:
    # Obtain citizenship and visa status
    ctzn_status = df_student.at[token, 'Citizenship Description']
    visa_status = df_student.at[token, 'Visa Description']
    # If not a citizen then ban from citizenship required projects
    if ctzn_status != 'Yes':
        for project in CITIZEN_REQ:
            citizen_bans.append((token,project))
    if (ctzn_status != 'Yes') and (visa_status != 'Yes'):
        for project in VISA_REQ:
            citizen_bans.append((token,project))

######################### Find Top Assignments using the IP ###########################
            
# utilize while loop to find solutions without duplicates
# counter initialized to 0, the actual optimization done in optimizeIP_repeat.py
count_solutions = 0
past_solns = []
scores = []
prob, stu_to_proj = optimize_repeat(project_index, token_index, penalties, minstaff_projects, maxstaff_projects,
                                antiprefs_dict_1, antiprefs_dict_2, stu_gpa_indic, LOCKED_STUDENTS,
                                BARRED_STUDENTS,citizen_bans)
while count_solutions != SOLUTION_LIMIT:
    prob.solve(solver='gurobi', verbose=False)
    
    # optimal value of objective function
    obj_val = int(prob.obj_value())
    scores.append(obj_val)

    # create a new solution file txt
    f = open('Results/soln_no_{number}_{score}_{date}.txt'.format(number=count_solutions+1,
                                                          score=obj_val, date=time.strftime("%m%d%Y")),'w+')

    f.write('soln_no_{number}_{score}_{date}.txt'.format(number=count_solutions+1,score=obj_val, date=time.strftime("%m%d%Y")))
    f.write('\n')

    # list of strings containing warnings about skill coverage on project
    skill_warnings = []

    # list of role coverage per project, values range 1-4
    role_coverage = []

    # create assignment vector
    soln_assignment = [1 for _ in range(num_students)] 

    # loop to write data in tabular format
    for j in range(num_projects):
        f.write('\n' + '>> ' + PROJECT_NAMES[j] + ' ({index})'.format(index=j+1) + '\n')

        # booleans to check whether at least one student with that skill exists on project team
        check_MS = 0
        check_MD = 0
        check_P = 0
        check_ECE = 0
        check_MM = 0
        check_UOD = 0
        # booleans to check if a role is satisfied on project team
        check_CREAT = 0
        check_PUSH = 0
        check_DOER = 0
        check_PLAN = 0

        # write student info on the project and checks skills/roles
        for i in range(num_students):
            if stu_to_proj[i, j].value[0] == 1:
                soln_assignment[i] = j
                curr_token = tokens[i]
                antipref_str = '\u005B'
                if i in antiprefs_dict_1:
                    antipref_str += tokens[antiprefs_dict_1[i]]
                    if i in antiprefs_dict_2:
                        antipref_str += ','+tokens[antiprefs_dict_2[i]]
                antipref_str += '\u005D'
                f.write(str(df_survey.at[curr_token,PROJECT_NAMES[j]]) + ' ' # preference code
                        + df_student.at[curr_token,'First Name'] + ' ' # first name
                        + df_student.at[curr_token,'Last Name'] + ' ' # last name
                        + ' '*(24-len(df_student.at[curr_token,'First Name'])-
                               len(df_student.at[curr_token,'Last Name'])) + '\t' # spacing
                        + df_survey.at[curr_token,'major'] +'\t' # major
                        + df_survey.at[curr_token,'role [1]'] + '\t' # primary role
                        #+ df_roles.at[curr_token,'role [2]'] + '\t' # secondary role, suppressed for now
                        + "%.5f" % float(df_student.at[curr_token,'Cumulative GPA']) + '\t' # GPA, rounded to 5 decimals
                        + antipref_str+'\t'
                        #+ '\u005B' + '\u005D' + '\t' # dummy code for violated antipreferences (NOT FUNCTIONAL)
                        )

                if df_survey.at[curr_token,'skills [MS]'] == 'Y':
                    f.write('MS' + ' ')
                    check_MS = 1
                if df_survey.at[curr_token,'skills [MD]'] == 'Y':
                    f.write('MD' + ' ')
                    check_MD = 1
                if df_survey.at[curr_token,'skills [P]'] == 'Y':
                    f.write('P' + ' ')
                    check_P = 1
                if df_survey.at[curr_token,'skills [ECE]'] == 'Y':
                    f.write('ECE' + ' ')
                    check_ECE = 1
                if df_survey.at[curr_token,'skills [MM]'] == 'Y':
                    f.write('MM' + ' ')
                    check_MM = 1
                if df_survey.at[curr_token,'skills [UOD]'] == 'Y':
                    f.write('UOD' + ' ')
                    check_UOD = 1
                if df_survey.at[curr_token,'role [1]'] == 'CREAT':
                    check_CREAT = 1
                if df_survey.at[curr_token,'role [1]'] == 'PUSH':
                    check_PUSH = 1
                if df_survey.at[curr_token,'role [1]'] == 'DOER':
                    check_DOER = 1
                if df_survey.at[curr_token,'role [1]'] == 'PLAN':
                    check_PLAN = 1
                f.write('\n')
        if check_MS + check_MD + check_P + check_ECE + check_MM + check_UOD != 6:
            warning = PROJECT_NAMES[j] + ' is missing specialist(s) in:'
            if check_MS == 0:
                warning += ' MS'
            if check_MD == 0:
                warning += ' MD'
            if check_P == 0:
                warning += ' P'
            if check_ECE == 0:
                warning += ' ECE'
            if check_MM == 0:
                warning += ' MM'
            if check_UOD == 0:
                warning += ' UOD'
            warning += '.'
            skill_warnings.append(warning)
        role_coverage.append(check_PLAN+check_CREAT+check_DOER+check_PUSH)

    # loop to calculate role diversity of a team
    # we give 1 point for all 4 roles covered, 4 points for 3/4 roles, 8 for 2/4 roles, 16 for 1/4 roles
    # rationale is that 5 person team has 1/14 probability of hitting all 4/4 roles, 2/7 of hitting 3/4 roles,
    # 4/7 of hitting 2/4 roles, and 1/14 of hitting 1/4 roles. 4 person case is similar (1/35, 4/35, 26/35, 4/35).
    role_diversity = 0
    for count in role_coverage:
        if count == 4:
            role_diversity += 1
        if count == 3:
            role_diversity += 4
        if count == 2:
            role_diversity += 8
        if count == 1:
            role_diversity += 16
    f.write('\n' + 'Overall role diversity score for this allocation is ' + str(role_diversity) + '.' + '\n')

    # loop to warn faculty of skill imbalance on a team
    if len(skill_warnings) != 0:
        f.write('\n')
        f.write('Below are warnings regarding skill imbalance on a project team.' + '\n'
                + 'If a project requires at least one member to have a particular skill,'
                + ' reconsideration/swap may be necessary.' + '\n')
    for warn in skill_warnings:
        f.write(warn+'\n')

    # close instance of file
    print()
    print('Solution saved as file ' +
          'Results/soln_no_{number}_{score}_{date}.txt'.format(number=count_solutions+1,
                                                       score=obj_val, date=time.strftime("%m%d%Y")))
    f.close()

    past_solns.append(soln_assignment)
    prob.add_constraint(sum([stu_to_proj[i,soln_assignment[i]] for i in range(num_students)]) <= num_students-1)
    count_solutions += 1

# initialize a pairwise distance matrix after solutions are collected
dist_mtrx = np.zeros((SOLUTION_LIMIT,SOLUTION_LIMIT),dtype=int)
# use past solutions to create a distance matrix between allocation solutions
for r in range(SOLUTION_LIMIT):
    for c in range(r+1,SOLUTION_LIMIT):
        # find pairwise differences using the x matrices for each allocation
        differences = 0
        for i in range(num_students):
            if past_solns[r][i] != past_solns[c][i]:
                differences += 1
        dist_mtrx[r][c] = differences
        dist_mtrx[c][r] = differences # upper triangular matrix mirrored to make symmetric matrix
#print(dist_mtrx)

# find the most diverse solutions based on the distance matrix
# methodology is to pick solution with largest pairwise distances to those
# solutions already chosen
count_div_soln = 0
div_soln_indices = []
while count_div_soln < DIVERSE_LIMIT:

    # if we are to choose our first solution
    if count_div_soln == 1:
        # sums over rows
        sums = np.sum(dist_mtrx, axis = 0).tolist()
        # max sum over this new array
        first_soln = sums.index(max(sums))
        obj_val = scores[first_soln]
        div_soln_indices.append(first_soln)
        # start copying
        g = open('Results/soln_no_{number}_{score}_{date}.txt'.format(number=first_soln+1,
                                                              score=obj_val,
                                                              date=time.strftime("%m%d%Y")),'r')

        f = open('div_soln_no_{number}_{score}_{date}.txt'.format(number=count_div_soln+1,score=obj_val,
                                                              date=time.strftime("%m%d%Y")),'w+')
        for line in g:
            f.write(line)
        g.close()
        print('Diverse solution saved as file ' +
              'div_soln_no_{number}_{score}_{date}.txt'.format(number=count_div_soln+1,
                                                               score=obj_val,
                                                               date=time.strftime("%m%d%Y")))
        f.close()
        
    # all other solutions rely on counting max sum of diff from previous chosen solutions
    else:
        check_sum = []
        actual_sum = []
        for soln_check in range(SOLUTION_LIMIT):
            each_sum = 0
            for soln in div_soln_indices:
                each_sum += dist_mtrx[soln,soln_check]
            actual_sum.append(each_sum)
            if soln_check not in div_soln_indices:
                check_sum.append(each_sum)
        new_div_soln_index = actual_sum.index(max(check_sum))
        obj_val = scores[new_div_soln_index]
        div_soln_indices.append(new_div_soln_index)
        g = open('Results/soln_no_{number}_{score}_{date}.txt'.format(number=new_div_soln_index+1,
                                                            score=obj_val, date=time.strftime("%m%d%Y")),'r')

        f = open('div_soln_no_{number}_{score}_{date}.txt'.format(number=new_div_soln_index+1,score=obj_val,
                                                              date=time.strftime("%m%d%Y")),'w+')
        for line in g:
            f.write(line)
        g.close()
        print('Diverse solution saved as file ' +
              'div_soln_no_{number}_{score}_{date}.txt'.format(number=new_div_soln_index+ 1,
                                                               score=obj_val,
                                                               date=time.strftime("%m%d%Y")))
        f.close()
    count_div_soln += 1


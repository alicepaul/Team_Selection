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

# Project names
# TODO: change if project data also changes
project_names = ['project [1]', 'project [2]', 'project [3]', 'project [4]', 'project [5]', 'project [6]',
                 'project [7]', 'project [8]', 'project [9]', 'project [10]', 'project [11]', 'project [12]',
                 'project [13]', 'project [14]']
project_index = dict()
for i in range(len(project_names)):
    project_index[project_names[i]] = i

# Relevant constants
# TODO: change if project data also changes
num_projects = len(project_names)
num_students = 72

# Minimum and maximum number of students per project
# TODO: change if project data also changes
MINSTAFF = 5
MAXSTAFF = 6
# projects allowed to go below the minimum
# TODO: change if project data also changes
MINSTAFF_EXCEPTIONS = {
    # unknown for other years!
}
# create dictionary for MINSTAFF_PROJECTS according to exceptions
MINSTAFF_PROJECTS = {}
for name in project_names:
    if name not in MINSTAFF_EXCEPTIONS.keys():
        MINSTAFF_PROJECTS[name] = MINSTAFF
    else:
        MINSTAFF_PROJECTS[name] = MINSTAFF_EXCEPTIONS[name]

# projects allowed to go above the maximum
# TODO: change if project data also changes
MAXSTAFF_EXCEPTIONS = {
    # unknown for other years!
}
# create dictionary for MAXSTAFF_PROJECTS according to exceptions
MAXSTAFF_PROJECTS = {}
for name in project_names:
    if name not in MAXSTAFF_EXCEPTIONS.keys():
        MAXSTAFF_PROJECTS[name] = MAXSTAFF
    else:
        MAXSTAFF_PROJECTS[name] = MAXSTAFF_EXCEPTIONS[name]

# students locked onto a project 
LOCKED_STUDENTS = []
#   '(locked student token)', 'project [#]'), # reason: mentor really wants him/her


# students barred from a project 
BARRED_STUDENTS = []
#    ('(barred student token)', 'project [#]'), # reason: non-US citizenship / visa expiry / other

# Citizenship/visa-affected projects, list by name
# US citizens only projects, by name
CITIZEN_REQ = []
# US citizens or visa holders only projects
VISA_REQ = []

# Cost constants
# note: pref costs in string form due to working with dictionary below
# caution: must make sure RHS values do not overlap with preference values (hence 1.0 instead of 1)
PREF_COST_5 = '0'
PREF_COST_4 = '1.0'
PREF_COST_3 = '5.0'
PREF_COST_2 = '1000'
PREF_COST_1 = '10000'
ANTIPREF_COST = 100
NONCITIZEN_COST = 1000
MIN_GPA = 3.0 # we can change this later to 10th percentile, this is a default
GPA_COST = 100

# Maximum number of solutions to extract from the integer program
# this will ask gurobi to find the top # best solutions
# TODO: revise as desired
SOLUTION_LIMIT = 100

# Maximum number of solutions to take that are pairwise most diverse
DIVERSE_LIMIT = 10

# extract data from survey_anon.csv, token used as index column
# TODO: change csv file AND names
df = pd.read_csv('Data/survey_anon17.csv', index_col='Token',
                 names=['id', 'project [1]', 'project [2]', 'project [3]', 'project [4]', 'project [5]', 'project [6]',
                        'project [7]', 'project [8]', 'project [9]', 'project [10]', 'project [11]', 'project [12]',
                        'project [13]', 'project [14]', 'bullets [1]', 'bullets [2]',
                        'role [1]', 'role [2]', 'role [3]', 'role [4]',
                        'skills [MS]', 'skills [MD]', 'skills [P]', 'skills [ECE]', 'skills [MM]', 'skills [UOD]',
                        'major', 'major [comment]', 'comments', 'Email address', 'Token'])

# extract data from students_anon.csv, ID Number (same as token) used as index column
# TODO: change csv file
df2 = pd.read_csv('Data/students_anon17.csv', index_col='ID Number',
                  names=['Full Name (Last, First)', 'Section Course Number', 'Section Number', 'Section Session Code',
                         'Section Year', 'ID Number', 'First Name', 'Last Name', 'Gender Code', 'Cumulative GPA',
                         'Major 1 Code', 'Concentration 1 Code', 'Citizenship Description', 'Visa Description', 'EML1'])

# original of first dataframe
df_original = df.copy()

# drop unnecessary columns for first dataframe
df.drop('id',axis=1,inplace=True)
df.drop('major',axis=1,inplace=True)
df.drop('major [comment]',axis=1,inplace=True)
df.drop('comments',axis=1,inplace=True)
df.drop('Email address',axis=1,inplace=True)

# salvage name portion of dataframe for presentation
df_names = df2.iloc[:,[5,6]].copy()
# print(df_names)

#drop unnecessary columns for second dataframe
df2.drop('Full Name (Last, First)',axis=1,inplace=True)
df2.drop('Section Course Number',axis=1,inplace=True)
df2.drop('Section Number',axis=1,inplace=True)
df2.drop('Section Session Code',axis=1,inplace=True)
df2.drop('Section Year',axis=1,inplace=True)
df2.drop('First Name',axis=1,inplace=True)
df2.drop('Last Name',axis=1,inplace=True)
df2.drop('Concentration 1 Code',axis=1,inplace=True)
# uncomment this if citizenship should not be considered, see warning below
# df2.drop('Citizenship Description',axis=1,inplace=True)
# uncomment this if visa status should not be considered, see warning below
# df2.drop('Visa Description',axis=1,inplace=True)
df2.drop('EML1',axis=1,inplace=True)
df2_demographic = df2.copy()
# print(df2_demographic)

# create dictionary for penalties
# TODO: revise dictionaries to reflect penalties above for sensitivity analysis if not already done so
penalty_dict = {'1': PREF_COST_1, '2': PREF_COST_2, '3': PREF_COST_3, '4': PREF_COST_4, '5': PREF_COST_5}
# TODO: revise dictionary if value ever gets overwritten - SEE CAUTION ABOVE in sensitivity analysis section
revise_dict = {PREF_COST_4:str(int(float(PREF_COST_4))),PREF_COST_3:str(int(float(PREF_COST_3)))}

# manipulation of first dataframe to include only preferences
df_pref=df_original.iloc[:,1:num_projects+1].copy()
# print(df_pref)

# manipulation of preferences to map to penalties
df_penalty = df_pref.copy()
for name in project_names:
    df_penalty[name].replace(penalty_dict,inplace=True)
    df_penalty[name].replace(revise_dict,inplace=True)
# print(df_penalty)

# conversion of pandas dataframe into numpy array
df_penalty_np = df_penalty.values
# print(df_penalty_np)

# delete first row as it only has project names, which we don't need
penalty_matrix = np.delete(df_penalty_np,0,0)
# print(penalty_matrix)

# convert numpy array of strings to numpy array of floats/ints
penalties = penalty_matrix.astype(np.int)
# print(penalties)

# manipulation of dataframe to include only antipreferences
df_bullet = df_original.iloc[:,num_projects+1:num_projects+3].copy()
# NaN was a problem so replaced with zeroes
df_bullet.fillna(0,inplace=True)
# print(df_bullet)

# obtain tokens from index array
tokens = df_original.index.tolist()[1:]
token_index = dict()
for i in range(len(tokens)):
    token_index[tokens[i]] = i
# print(tokens)

# dictionary of antiprefs; index of token (student shooting bullet) to index of token (student receiving bullet)
antiprefs_dict_1 = {}
antiprefs_dict_2 = {}

for token in tokens:
    # track which token we are on using index
    token_row = token_index[token]
    # obtain antipref tokens
    a1 = df_bullet.at[token, 'bullets [1]']
    a2 = df_bullet.at[token, 'bullets [2]']
    # find the index at which the antiprefs reside
    # revise antiprefs accordingly
    if a1 != 0:
        token_col1 = token_index[a1]
        antiprefs_dict_1[token_row] = token_col1
    if a2 != 0:
        token_col2 = token_index[a2]
        antiprefs_dict_2[token_row] = token_col2

# extract other possibly relevant data to build upon
df_roles = df_original.iloc[:,num_projects+3:num_projects+7].copy()
# print(df_roles)

df_skills = df_original.iloc[:,num_projects+7:num_projects+13].copy()
# print(df_skills)

# extract majors
# if a mix of majors is preferred, can code up a solution using this data
df2_major = df2_demographic.iloc[:,2].copy()
# print(df2_major)
print(df2_major.loc[tokens])

# extract GPAs
df2_gpa = df2_demographic.iloc[:,1].copy()
# print(df2_gpa)

# reorder GPAs in the same order as token ID
gpa = df2_gpa.loc[tokens]
stu_gpas = [float(indiv_gpa) for indiv_gpa in gpa]
# print(stu_gpas)

# optionally alter MIN_GPA to 10th percentile of GPAs
# comment out if unnecessary
stu_gpas_np = np.array(stu_gpas)
# MIN_GPA = np.percentile(stu_gpas_np, 10)
# print(MIN_GPA)

# indicator function for whether a student GPA is < 3.0 or whatever MIN_GPA is set to be
stu_gpa_indic = [1 if indiv_gpa <= MIN_GPA else 0 for indiv_gpa in stu_gpas]
# print(stu_gpa_indic)

# extract citizenship description and visa status
df_ctzn_or_visa = df2_demographic.iloc[:,[3,4]].copy()

# add non-citizens or visa holder banned assignments
CITIZEN_BANS = []
for token in tokens:
    # track which token we are on using index
    token_row = token_index[token]
    # obtain citizenship and visa status
    ctzn_status = df_ctzn_or_visa.at[token, 'Citizenship Description']
    visa_status = df_ctzn_or_visa.at[token, 'Visa Description']
    # if not a citizen then ban from citizenship required projects
    if ctzn_status != 'Yes':
        for project in CITIZEN_REQ:
            CITIZEN_BANS.append((token_row,project))
    if (ctzn_status != 'Yes') and (visa_status != 'Yes'):
        for project in VISA_REQ:
            CITIZEN_BANS.append((token_row,project))
# utilize while loop to find solutions without duplicates
# counter initialized to 0, the actual optimization done in optimizeIP_repeat.py
count_solutions = 0
past_solns = []
scores = []
prob, stu_to_proj = optimize_repeat(project_index, token_index, penalties, MINSTAFF_PROJECTS, MAXSTAFF_PROJECTS,
                                antiprefs_dict_1, antiprefs_dict_2, stu_gpa_indic, LOCKED_STUDENTS,
                                BARRED_STUDENTS,CITIZEN_BANS)
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
        f.write('\n' + '>> ' + project_names[j] + ' ({index})'.format(index=j+1) + '\n')
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
        for i in range(num_students):
            if stu_to_proj[i, j].value[0] == 1:
                soln_assignment[i] = j
                curr_token = tokens[i]
                f.write(df_pref.at[curr_token,project_names[j]] + ' ' # preference code
                        + df_names.at[curr_token,'First Name'] + ' ' # first name
                        + df_names.at[curr_token,'Last Name'] + ' ' # last name
                        + ' '*(24-len(df_names.at[curr_token,'First Name'])-
                               len(df_names.at[curr_token,'Last Name'])) + '\t' # spacing
                        + df2_major.loc[tokens][i] +'\t' # major
                        + df_roles.at[curr_token,'role [1]'] + '\t' # primary role
                        # + df_roles.at[curr_token,'role [2]'] + '\t' # secondary role, suppressed for now
                        + "%.5f" % float(df2_gpa.loc[tokens][i]) + '\t' # GPA, rounded to 5 decimals
                        + '\u005B' + '\u005D' + '\t' # dummy code for violated antipreferences (NOT FUNCTIONAL)
                        )
                if df_skills.at[curr_token,'skills [MS]'] == 'Y':
                    f.write('MS' + ' ')
                    check_MS = 1
                if df_skills.at[curr_token,'skills [MD]'] == 'Y':
                    f.write('MD' + ' ')
                    check_MD = 1
                if df_skills.at[curr_token,'skills [P]'] == 'Y':
                    f.write('P' + ' ')
                    check_P = 1
                if df_skills.at[curr_token,'skills [ECE]'] == 'Y':
                    f.write('ECE' + ' ')
                    check_ECE = 1
                if df_skills.at[curr_token,'skills [MM]'] == 'Y':
                    f.write('MM' + ' ')
                    check_MM = 1
                if df_skills.at[curr_token,'skills [UOD]'] == 'Y':
                    f.write('UOD' + ' ')
                    check_UOD = 1
                if df_roles.at[curr_token,'role [1]'] == 'CREAT':
                    check_CREAT = 1
                if df_roles.at[curr_token,'role [1]'] == 'PUSH':
                    check_PUSH = 1
                if df_roles.at[curr_token,'role [1]'] == 'DOER':
                    check_DOER = 1
                if df_roles.at[curr_token,'role [1]'] == 'PLAN':
                    check_PLAN = 1
                f.write('\n')
        if check_MS + check_MD + check_P + check_ECE + check_MM + check_UOD != 6:
            warning = project_names[j] + ' is missing specialist(s) in:'
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
# methodology is to pick solution in dist_mtrx with largest row or column sum (these sums are the same)
# then pick solution in row/col with largest value of pairwise differences
# subsequent solutions chosen by picking solutions
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

# use dist_mtrx to draw up a graph using networkx to visualize swap distance
# incomplete/nonfunctional at the moment

# dt = [('len', float)]
# dist_mtrx = dist_mtrx.view(dt)
#
# G = nx.from_numpy_matrix(dist_mtrx)
# G = nx.relabel_nodes(G, dict(zip(range(len(G.nodes())),string.ascii_uppercase)))
#
# G = nx.drawing.nx_agraph.to_agraph(G)
#
# G.node_attr.update(color="red", style="filled")
# G.edge_attr.update(color="blue", width="2.0")
#
# G.draw('/tmp/out.png', format='png', prog='neato')

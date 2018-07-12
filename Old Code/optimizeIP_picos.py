import numpy as np
import picos as pic
import cvxopt as cvx
import pandas as pd

"""Optimization using integer programming formulation with PICOS
active comparison within process3.py yet to be established"""

# write out project names
project_names = ['project [1]', 'project [2]', 'project [3]', 'project [4]', 'project [5]', 'project [6]',
                 'project [7]', 'project [8]', 'project [9]', 'project [10]', 'project [11]', 'project [12]',
                 'project [13]', 'project [14]']
# relevant constants
num_projects = len(project_names)
num_students = 72
MINSTAFF = 5
MAXSTAFF = 6

# extract data from survey_anon.csv, token used as index column
df = pd.read_csv('Data/survey_anon.csv', index_col='Token',
                 names=['id', 'project [1]', 'project [2]', 'project [3]', 'project [4]', 'project [5]', 'project [6]',
                        'project [7]', 'project [8]', 'project [9]', 'project [10]', 'project [11]', 'project [12]',
                        'project [13]', 'project [14]', 'bullets [1]', 'bullets [2]',
                        'role [1]', 'role [2]', 'role [3]', 'role [4]',
                        'skills [MS]', 'skills [MD]', 'skills [P]', 'skills [ECE]', 'skills [MM]', 'skills [UOD]',
                        'major', 'major [comment]', 'comments', 'Email address', 'Token'])

# conversion of dataframe into 2D list if necessary, can comment back in
# lol = df.values.tolist()
# original in case I need it
df_original = df.copy()

# drop unnecessary columns
df.drop('id',axis=1,inplace=True)
df.drop('major',axis=1,inplace=True)
df.drop('major [comment]',axis=1,inplace=True)
df.drop('comments',axis=1,inplace=True)
df.drop('Email address',axis=1,inplace=True)
penalty_dict = {'1':'0', '2':'1', '3':'5.0', '4':'1000', '5':'10000'}
revise_dict = {'5.0':'5'}

# manipulation of dataframe to include only preferences
df_pref=df_original.iloc[:,1:num_projects+1].copy()
print(df_pref)

# manipulation of preferences to map to penalties
df_penalty = df_pref.copy()
for name in project_names:
    df_penalty[name].replace(penalty_dict,inplace=True)
    df_penalty[name].replace(revise_dict,inplace=True)
print(df_penalty)

# conversion of pandas dataframe into numpy array
df_penalty_np = df_penalty.values
print(df_penalty_np)

# delete first row as it only has project names, which we don't need
penalty_matrix = np.delete(df_penalty_np,0,0)
print(penalty_matrix)

# convert numpy array of strings to numpy array of floats/ints
penalties = penalty_matrix.astype(np.int)
print(penalties)

# manipulation of dataframe to include only antipreferences
df_bullet = df_original.iloc[:,num_projects+1:num_projects+3].copy()
# NaN was a problem so replaced with zeroes
df_bullet.fillna(0,inplace=True)
print(df_bullet)

# obtain tokens from index array
tokens = df_original.index.tolist()[1:]
print(tokens)

# preallocate a numpy array of dimension num_student x num_student
# we will preserve order in terms of tokens (row = from, col = to)
antiprefs = np.zeros((num_students,num_students),dtype=int)

for token in tokens:
    # track which token we are on using index
    token_row = tokens.index(token)
    # obtain antipref tokens
    a1 = df_bullet.at[token, 'bullets [1]']
    a2 = df_bullet.at[token, 'bullets [2]']
    # find the index at which the antiprefs reside
    # revise antiprefs accordingly
    if a1 != 0:
        token_col1 = tokens.index(a1)
        # can uncomment below to check that this works
        # print(token_row,",",token_col1)
        antiprefs[token_row,token_col1] = 100
    if a2 != 0:
        token_col2 = tokens.index(a2)
        # can uncomment below to check that this works
        # print(token_row,",",token_col2)
        antiprefs[token_row,token_col2] = 100

# antiprefs will look like a bunch of zeroes but inspection of
# individual coordinates as above will reveal its accuracy
print(antiprefs)

# extract other possibly relevant data to build upon
# TODO: (IDEA) incorporate roles into integer program so that no more than 1 role is duplicated/covered twice
df_roles = df_original.iloc[:,num_projects+3:num_projects+7].copy()
print(df_roles)

# TODO: (IDEA) incorporate skills into integer program so that no more than 1 skill is duplicated/covered twice
df_skills = df_original.iloc[:,num_projects+7:num_projects+13].copy()
print(df_skills)

# problem definition
# TODO: check syntax
prob = pic.Problem(solver='gurobi')


# convert list of list of penalties into 2D matrix for picos
penalty1 = pic.new_param('mat', penalties)
# convert list of list of antiprefs into 2D matrix for picos
penalty2 = pic.new_param('mat', antiprefs)

# add variable x_i,j matrix for students
stu_to_proj = prob.add_variable('x', (num_students,num_projects), vtype='binary')
# add variable y_i,i',j matrix dependent on x_i,j
stu_group = prob.add_variable('y', (num_students,num_students), vtype='binary')

# constraints setup
# sum of all entries x_ij over i (project allocated student count) should be in between MINSTAFF and MAXSTAFF
prob.add_list_of_constraints([sum(stu_to_proj[i]) >= MINSTAFF for i in range(num_students)])
prob.add_list_of_constraints([sum(stu_to_proj[i]) <= MAXSTAFF for i in range(num_students)])
# TODO: add specificity to MINSTAFF/MAXSTAFF constraints on a project-by-project basis
# this is because exceptions to the minimum/maximum can exist

# sum of all entries x_ij over j (student allocated project count) should be 1
prob.add_list_of_constraints([sum(stu_to_proj[:][j]) == 1 for j in range(num_projects)])

# IP constraints for y
# y_ii' >= x_ij + x_i'j - 1 for all j
prob.add_list_of_constraints([stu_group[i,k] >= stu_to_proj[i,j]+stu_to_proj[k,j]-1
                              for j in range(num_projects) for i in range(num_students) for k in range(num_students)])
# 0 <= y_ii'j <= 1
prob.add_list_of_constraints([stu_group[i,k] >= 0
                              for j in range(num_projects) for i in range(num_students) for k in range(num_students)])
prob.add_list_of_constraints([stu_group[i,k] <= 1
                              for j in range(num_projects) for i in range(num_students) for k in range(num_students)])

# objective function setup
prob.set_objective('min',pic.sum([penalty1[i,j]*stu_to_proj[i,j] for i in range(num_students) for j in range(num_projects)])
                   + pic.sum([penalty2[i,k]*stu_group[i,k] for j in range(num_projects) for i in range(num_students)
                              for k in range(num_students)]))

# print the problem setup summary
print(prob)
print('type:   '+prob.type)
print('status: '+prob.status)
# note that running using cvxopt encounters
# TODO: replace solver?
prob.solve(solver='gurobi',verbose=False)
print('status: '+prob.status)

# optimal value of objective function
print('the optimal value of this problem is:')
print(prob.obj_value())

# optimal value of x_i,j matrix variable
print('optimal solution for x')
print(stu_to_proj)

# optimal value of y_i,i',j list of matrices
print('optimal solution for y')
print(stu_group)

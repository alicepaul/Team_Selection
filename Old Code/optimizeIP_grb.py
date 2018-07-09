import numpy as np
from gurobipy import *
import pandas as pd

"""Optimization using integer programming formulation with gurobipy
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

# drop unnecessary columns; they've been redacted anyway
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

# actual gurobi optimization
try:
    # create new model
    m = Model('mip1')

    # create variables
    x = np.zeros((num_students,num_projects)).tolist()
    for j in range(num_projects):
        for i in range(num_students):
            x[i][j] = m.addVar(vtype=GRB.BINARY, name='x[{0},{1}]'.format(i,j))

    y = []
    for j in range(num_projects):
        y_sub = np.zeros((num_students,num_students)).tolist()
        for i in range(num_students):
            for k in range(num_students):
                y_sub[i][k] = m.addVar(vtype=GRB.BINARY, name='y[{0},{1},{2}]'.format(i,k,j))
        y.append(y_sub)

    # add constraints: sum of all entries x_ij over i  >= MINSTAFF, <= MAXSTAFF
    col_sum = np.sum(x,axis=1)
    for i in range(len(col_sum)):
        m.addConstr(col_sum[i] >= MINSTAFF, name='csum_min[{0}]'.format(i))
        m.addConstr(col_sum[i] <= MAXSTAFF, name='csum_max[{0}]'.format(i))

    # add constraints: sum of all entries x_ij over j == 1
    row_sum = np.sum(x, axis=0)
    for j in range(len(row_sum)):
        m.addConstr(row_sum[j] == 1, name='rsum[{0}]'.format(j))

    # add constraint: y_ii'j = x_ij + x_i'j - 1
    for j in range(num_projects):
        for i in range(num_students):
            for k in range(num_students):
                m.addConstr(y[j][i][k] == x[i][j]+x[k][j]-1, name='cyeq[{0}{1}{2}]'.format(i,k,j))

    # add constraints: 0 <= y_ii'j <= 1
    for j in range(num_projects):
        for i in range(num_students):
            for k in range(num_students):
                m.addConstr(y[j][i][k] >= 0, name='cygt[{0}{1}{2}]'.format(i,k,j))
                m.addConstr(y[j][i][k] <= 1, name='cylt[{0}{1}{2}]'.format(i,k,j))

    # set objective

    m.setObjective(sum([x[i][j]*penalties[i,j] for i in range(num_students) for j in range(num_projects)])
                   +sum([y[j][i][k]*antiprefs[i,k] for j in range(num_projects) for i in range(num_students)
                         for k in range(num_students)]),GRB.MINIMIZE)

    # attempt to optimize
    m.optimize()

    for v in m.getVars():
        print('%s %g' % (v.varName, v.x))

    print('Obj: %g' % m.objVal)


except GurobiError as e:
    print('Error code ' + str(e.errno) + ": " + str(e))

except AttributeError as e:
    print('Encountered an attribute error: ' + str(e))

import numpy as np
import pandas as pd
from optimizeIP_repeat import optimize_repeat
import time
import picos

"""Optimization using integer programming formulation with PICOS
does not have active comparison with process3.py """

# write out project names
# TODO: change if project data also changes
project_names = ['project [1]', 'project [2]', 'project [3]', 'project [4]', 'project [5]', 'project [6]',
                 'project [7]', 'project [8]', 'project [9]', 'project [10]', 'project [11]', 'project [12]',
                 'project [13]', 'project [14]']

# relevant constants
# TODO: change if project data also changes
num_projects = len(project_names)
num_students = 72
# minimum and maximum number of students per project
# TODO: change if project data also changes
MINSTAFF = 5
MAXSTAFF = 6
# projects allowed to go below the minimum
# TODO: change if project data also changes
MINSTAFF_EXCEPTIONS = {
    'project [1]': 4,
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
    'project [2]': 5,
}
# create dictionary for MAXSTAFF_PROJECTS according to exceptions
MAXSTAFF_PROJECTS = {}
for name in project_names:
    if name not in MAXSTAFF_EXCEPTIONS.keys():
        MAXSTAFF_PROJECTS[name] = MAXSTAFF
    else:
        MAXSTAFF_PROJECTS[name] = MAXSTAFF_EXCEPTIONS[name]

# projects that don't need allocation - feature omitted
LOCKED_PROJECT_NAMES = []

# TODO: implement locked students without modifying preferences
# students locked onto a project
LOCKED_STUDENTS = []

# TODO: implement barred students without modifying preferences
# students barred from a project
BARRED_STUDENTS = []
#    ("Student 1", 'project [2]'), # reason: non-US citizenship / visa expiry
# ]

# Cost constants
# TODO: change values for sensitivity analysis
PREF_COST_5 = 0
PREF_COST_4 = 1
PREF_COST_3 = 5
PREF_COST_2 = 1000
PREF_COST_1 = 10000
ANTIPREF_COST = 100
NONCITIZEN_COST = 1000
MIN_GPA = 3.0
GPA_COST = 100

# Maximum number of solutions to extract from the integer program
# this will ask gurobi to find the top # best solutions
# TODO: revise as desired
SOLUTION_LIMIT = 2

# extract data from survey_anon.csv, token used as index column
df = pd.read_csv('Data/survey_anon.csv', index_col='Token',
                 names=['id', 'project [1]', 'project [2]', 'project [3]', 'project [4]', 'project [5]', 'project [6]',
                        'project [7]', 'project [8]', 'project [9]', 'project [10]', 'project [11]', 'project [12]',
                        'project [13]', 'project [14]', 'bullets [1]', 'bullets [2]',
                        'role [1]', 'role [2]', 'role [3]', 'role [4]',
                        'skills [MS]', 'skills [MD]', 'skills [P]', 'skills [ECE]', 'skills [MM]', 'skills [UOD]',
                        'major', 'major [comment]', 'comments', 'Email address', 'Token'])

# extract data from students_anon.csv, ID Number (same as token) used as index column
df2 = pd.read_csv('Data/students_anon.csv', index_col='ID Number',
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
# WARNING: if citizenship / visa status dropped, then future indices should be changed
df2_demographic = df2.copy()
# print(df2_demographic.iloc[:,0].copy())

# create dictionary for penalties
penalty_dict = {'1':'10000', '2':'1000', '3':'5.0', '4':'1.0', '5':'0'}
revise_dict = {'1.0':'1','5.0':'5'}

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
print(tokens)

# preallocate a numpy array of dimension num_student x num_student
# we will preserve order in terms of tokens (row = from, col = to)
antiprefs = np.zeros((num_students,num_students),dtype=int)
# dictionary of antiprefs; index of token (student shooting bullet) to index of token (student receiving bullet)
antiprefs_dict_1 = {}
antiprefs_dict_2 = {}

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
        antiprefs_dict_1[token_row] = token_col1
        # can uncomment below to check that this works
        # print(token_row,",",token_col1)
        antiprefs[token_row,token_col1] = ANTIPREF_COST
    if a2 != 0:
        token_col2 = tokens.index(a2)
        antiprefs_dict_2[token_row] = token_col2
        # can uncomment below to check that this works
        # print(token_row,",",token_col2)
        antiprefs[token_row,token_col2] = ANTIPREF_COST

# antiprefs will look like a bunch of zeroes due to sparsity but coordinates above
# indicate where antiprefs[row,col] == ANTIPREF_COST. uncomment if necessary
# print(antiprefs)

# extract other possibly relevant data to build upon
# TODO: (IDEA) incorporate roles into integer program so that no more than 1 role is duplicated/covered twice
# TODO: create diversity score
df_roles = df_original.iloc[:,num_projects+3:num_projects+7].copy()
# print(df_roles)

# TODO: (IDEA) incorporate skills into integer program so that no more than 1 skill is duplicated/covered twice
# TODO: create diversity score
df_skills = df_original.iloc[:,num_projects+7:num_projects+13].copy()
# print(df_skills)

# extract gender
# if a mix of genders is preferred, can code up a solution using this data
df2_gender = df2_demographic.iloc[:,0].copy()
# print(df2_gender)

# extract majors
# if a mix of majors is preferred, can code up a solution using this data
df2_major = df2_demographic.iloc[:,2].copy()
# print(df2_major)

# extract GPAs
df2_gpa = df2_demographic.iloc[:,1].copy()
print(df2_gpa)

# reorder GPAs in the same order as token ID
gpa = df2_gpa.loc[tokens]
stu_gpas = [float(indiv_gpa) for indiv_gpa in gpa]

# indicator function for whether a student GPA is < 3.0 or whatever MIN_GPA is set to be
stu_gpa_indic = [1 if indiv_gpa < MIN_GPA else 0 for indiv_gpa in stu_gpas]
print(stu_gpa_indic)
# utilize while loop to find solutions without duplicates
# counter initialized to 0, the actual optimization done in optimizeIP_repeat.py
count_solutions = 0
past_solns = []
while count_solutions != SOLUTION_LIMIT:

    new_soln = optimize_repeat(num_students, num_projects, penalties, antiprefs, MINSTAFF_PROJECTS, MAXSTAFF_PROJECTS,
                    project_names, antiprefs_dict_1, antiprefs_dict_2, stu_gpa_indic, GPA_COST)
    # optimal value of objective function
    print('the optimal value of the objective function is:')
    print(new_soln[0])

    print('the optimal value of x (stu_to_proj matrix)')
    print(new_soln[1])

    # create a new solution file txt
    f = open('soln_no_{number}_{score}_{date}.txt'.format(number=count_solutions+1,
                                                          score=new_soln[0], date=time.strftime("%m%d%Y")),'w+')

    # in order to obtain names instead of tokens, find a way to map the tokens back to the names
    # then replace 'Student with token ' + tokens[i] with 'Student with name ' + name[i]
    # TODO: above suggested fix if confidentiality not an issue
    # TODO: edit project_names array to make more legible/sensible
    # TODO: reorder by student last name or school ID if arranging by projects is insufficient
    for j in range(num_projects):
        for i in range(num_students):
            if new_soln[1][i, j].value[0] == 1:
                print('Student with token ' + tokens[i] + ' works on project #' + str(j + 1) + " " + project_names[j])
                f.write('Student with token ' + tokens[i] + ' works on project #' + str(j + 1) + " " + project_names[j] + '\n')

    # close instance of file
    print('Solution saved as file ' +
          'soln_no_{number}_{score}_{date}.txt'.format(number=count_solutions+1,
                                                       score=new_soln[0], date=time.strftime("%m%d%Y")))
    f.close()

    # optimal value of y_i,i' arrays
    # uncomment if necessary
    # print('optimal solution for y')
    # print(new_soln[2])
    # print(new_soln[3])

    past_solns.append(new_soln[1])
    count_solutions += 1

print(type(past_solns[0].value))
print(past_solns[0].[5,15])

pairs = []

for i in range(num_students):
    for j in range(num_students):
        if past_solns[0][i,j] == 1:
            pairs.append([i,j])

print(pairs)



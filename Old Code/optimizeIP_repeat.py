import numpy as np
import picos as pic
import pandas as pd

def optimize_repeat(num_students, num_projects, penalties, antiprefs,MINSTAFF_PROJECTS, MAXSTAFF_PROJECTS,
                    project_names, antiprefs_dict_1, antiprefs_dict_2, stu_gpa_indic, GPA_COST):

    # problem definition
    prob = pic.Problem(solver='gurobi')

    # convert list of list of penalties into 2D matrix for picos
    penalty1 = pic.new_param('mat', penalties)
    # convert list of list of antiprefs into 2D matrix for picos
    penalty2 = pic.new_param('mat', antiprefs)

    # add variable x_i,j matrix for students
    stu_to_proj = prob.add_variable('x', (num_students,num_projects), vtype='binary')
    # add variable y_i,i' column vector dependent on x_i,j
    stu_group1 = prob.add_variable('y1', num_students, vtype='binary')
    stu_group2 = prob.add_variable('y2', num_students, vtype='binary')

    # add variable z_j column vector representing GPA violations, expected to be 0 column vector
    gpa_violation = prob.add_variable('z', num_projects, vtype='binary')

    # constraints setup
    # IP constraints for x (stu_to_proj)
    # sum of all entries x_ij over j (project allocated student count) should be between MINSTAFF and MAXSTAFF
    # for a given project; this is done using dictionaries initialized above
    prob.add_list_of_constraints([sum(stu_to_proj[:,j]) >= MINSTAFF_PROJECTS[project_names[j]] for j in range(num_projects)])
    prob.add_list_of_constraints([sum(stu_to_proj[:,j]) <= MAXSTAFF_PROJECTS[project_names[j]] for j in range(num_projects)])
    # this is because exceptions to the minimum/maximum can exist

    # sum of all entries x_ij over i (student allocated project count) should be 1
    prob.add_list_of_constraints([sum(stu_to_proj[i,:]) == 1 for i in range(num_students)])

    # IP constraint for y (stu_to_proj)
    # y1[i] = binary variable whether or not student @ index i is w/ first antipref; use antiprefs_dict_1
    prob.add_list_of_constraints([stu_group1[i] >= stu_to_proj[i,j]+stu_to_proj[antiprefs_dict_1[i],j]-1
                                  for j in range(num_projects) for i in antiprefs_dict_1.keys()])
    # y2[i] = binary variable whether or not student @ index i is w/ second antipref; use antiprefs_dict_2
    prob.add_list_of_constraints([stu_group2[i] >= stu_to_proj[i,j]+stu_to_proj[antiprefs_dict_2[i],j]-1
                                  for j in range(num_projects) for i in antiprefs_dict_2.keys()])

    # IP constraint for GPA
    gpa_sub_array = [indic-0.5 for indic in stu_gpa_indic]
    prob.add_list_of_constraints([gpa_violation[j] >= sum([a*b for a,b in zip(gpa_sub_array,stu_to_proj[:,j])])
                                  for j in range(num_projects)])

    # past solutions constraint
    # for past in past_solns:
    #     prob.add_constraint(stu_to_proj != past)
    # prob.add_list_of_constraints([stu_to_proj != past for past in past_solns])

    # objective function setup
    prob.set_objective('min',pic.sum([penalty1[i,j]*stu_to_proj[i,j] for i in range(num_students) for j in range(num_projects)])
                       + pic.sum([stu_group1[i] for i in range(num_students)])
                       + pic.sum([stu_group2[i] for i in range(num_students)])
                       + pic.sum([gpa_violation[j] * GPA_COST for j in range(num_projects)])
                       )

    # print the problem setup summary
    print(prob)
    print('type:   ' + prob.type)
    print('status: ' + prob.status)
    prob.solve(solver='gurobi', verbose=False)
    print('status: ' + prob.status)

    return [prob.obj_value(), stu_to_proj, stu_group1, stu_group2]
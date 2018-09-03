import picos as pic

"""
Integer programming formulation for team selection with PICOS

Author: Daniel Suh, Summer 2018
"""

ANTIPREF_COST = 100
GPA_COST = 100

def optimize_repeat(project_index, token_index, name_fuzzy, penalties, minstaff_projects, maxstaff_projects,
                                antiprefs_dict_1, antiprefs_dict_2, stu_gpa_indic, locked_students,
                                barred_students,citizen_bans, allow_antiprefs_gpa=False):

    num_students = len(token_index)
    num_projects = len(project_index)

    # problem definition
    prob = pic.Problem(solver='gurobi')

    # convert list of list of penalties into 2D matrix for picos
    penalty1 = pic.new_param('mat', penalties)

    # add variable x_i,j matrix for students
    stu_to_proj = prob.add_variable('x', (num_students,num_projects), vtype='binary')

    if allow_antiprefs_gpa:
        stu_group1 = prob.add_variable('y1', num_students, vtype='binary')
        stu_group2 = prob.add_variable('y2', num_students, vtype='binary')
        gpa_violation = prob.add_variable('z', num_projects, vtype='binary')
        
    # constraints setup
    # IP constraints for x (stu_to_proj)
    # sum of all entries x_ij over j (project allocated student count) should be between minstaff and maxstaff
    prob.add_list_of_constraints([sum(stu_to_proj[:,project_index[proj_name]]) >= minstaff_projects[proj_name]
                                      for proj_name in minstaff_projects.keys()])
    prob.add_list_of_constraints([sum(stu_to_proj[:,project_index[proj_name]]) <= maxstaff_projects[proj_name]
                                      for proj_name in maxstaff_projects.keys()])
    # this is because exceptions to the minimum/maximum can exist

    # sum of all entries x_ij over i (student allocated project count) should be 1
    prob.add_list_of_constraints([sum(stu_to_proj[i,:]) == 1 for i in range(num_students)])

    # IP constraint for anti-preferences: cannot violate
    if allow_antiprefs_gpa:
        prob.add_list_of_constraints([stu_group1[i] >= stu_to_proj[i,j]+stu_to_proj[antiprefs_dict_1[i],j]-1
                                      for j in range(num_projects) for i in antiprefs_dict_1.keys()])
        prob.add_list_of_constraints([stu_group1[i] >= stu_to_proj[i,j]+stu_to_proj[antiprefs_dict_2[i],j]-1
                                      for j in range(num_projects) for i in antiprefs_dict_2.keys()])
    else:
        prob.add_list_of_constraints([0 >= stu_to_proj[i,j]+stu_to_proj[antiprefs_dict_1[i],j]-1
                                      for j in range(num_projects) for i in antiprefs_dict_1.keys()])
        prob.add_list_of_constraints([0 >= stu_to_proj[i,j]+stu_to_proj[antiprefs_dict_2[i],j]-1
                                      for j in range(num_projects) for i in antiprefs_dict_2.keys()])

    # IP constraint for GPA: less than 1/2 students with low gpa on a project
    gpa_sub_array = [indic-0.5 for indic in stu_gpa_indic]
    if allow_antiprefs_gpa:
        prob.add_list_of_constraints([gpa_violation[j] >= sum([a*b for a,b in zip(gpa_sub_array,stu_to_proj[:,j])])
                                      for j in range(num_projects)])        
    else:
        prob.add_list_of_constraints([0 >= sum([a*b for a,b in zip(gpa_sub_array,stu_to_proj[:,j])])
                                      for j in range(num_projects)])

    # constraint for students locked into a project
    for (stu_name,project_name) in locked_students:
        # get student and project indices
        stu_index = token_index[name_fuzzy[stu_name]]
        proj_index = project_index[project_name]
        # constraint is that the student, project pair must equal 1
        prob.add_constraint(stu_to_proj[stu_index, proj_index] == 1)

    # constraint for students barred from a project
    for (stu_name,project_name) in barred_students:
        # get student and project indices
        stu_index = token_index[name_fuzzy[stu_name]]
        proj_index = project_index[project_name]
        # constraint is that the student, project pair must equal 0
        prob.add_constraint(stu_to_proj[stu_index,proj_index] == 0)

    # constraint for citizenship req projects
    for (token,project_name) in citizen_bans:
        # get student and project indices
        stu_index = token_index(token)
        proj_index = project_index(project_name)
        # constraint is that the student, project pair must equal 0
        prob.add_constraint(stu_to_proj[stu_index,proj_index] == 0)
        
    # objective function setup
    if allow_antiprefs_gpa:
        prob.set_objective('min',pic.sum([penalty1[i,j]*stu_to_proj[i,j] for i in range(num_students) for j in range(num_projects)])
                           + ANTIPREF_COST*pic.sum([stu_group1[i] for i in range(num_students)])
                           + ANTIPREF_COST*pic.sum([stu_group2[i] for i in range(num_students)])
                           + GPA_COST*pic.sum([gpa_violation[j] for j in range(num_projects)])
                           )
    else:
        prob.set_objective('min',pic.sum([penalty1[i,j]*stu_to_proj[i,j] for i in range(num_students) for j in range(num_projects)]))

    # print the problem setup summary - suppressed
    # print(prob)
    # print('type:   ' + prob.type)
    # print('status: ' + prob.status)
    # prob.solve(solver='gurobi', verbose=False)
    # print('status: ' + prob.status)
    return prob, stu_to_proj #[prob.obj_value(), stu_to_proj]

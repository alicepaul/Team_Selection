import picos as pic

"""
Integer programming formulation for team selection with PICOS

Author: Daniel Suh, Summer 2018
"""

def optimize_repeat(project_index, token_index, penalties, MINSTAFF_PROJECTS, MAXSTAFF_PROJECTS,
                                antiprefs_dict_1, antiprefs_dict_2, stu_gpa_indic, LOCKED_STUDENTS,
                                BARRED_STUDENTS,CITIZEN_BANS):

    num_students = len(token_index)
    num_projects = len(project_index)

    # problem definition
    prob = pic.Problem(solver='gurobi')

    # convert list of list of penalties into 2D matrix for picos
    penalty1 = pic.new_param('mat', penalties)

    # add variable x_i,j matrix for students
    stu_to_proj = prob.add_variable('x', (num_students,num_projects), vtype='binary')

    # constraints setup
    # IP constraints for x (stu_to_proj)
    # sum of all entries x_ij over j (project allocated student count) should be between MINSTAFF and MAXSTAFF
    prob.add_list_of_constraints([sum(stu_to_proj[:,project_index[proj_name]]) >= MINSTAFF_PROJECTS[proj_name]
                                      for proj_name in MINSTAFF_PROJECTS.keys()])
    prob.add_list_of_constraints([sum(stu_to_proj[:,project_index[proj_name]]) <= MAXSTAFF_PROJECTS[proj_name]
                                      for proj_name in MAXSTAFF_PROJECTS.keys()])
    # this is because exceptions to the minimum/maximum can exist

    # sum of all entries x_ij over i (student allocated project count) should be 1
    prob.add_list_of_constraints([sum(stu_to_proj[i,:]) == 1 for i in range(num_students)])

    # IP constraint for anti-preferences: cannot violate
    prob.add_list_of_constraints([0 >= stu_to_proj[i,j]+stu_to_proj[antiprefs_dict_1[i],j]-1
                                  for j in range(num_projects) for i in antiprefs_dict_1.keys()])
    prob.add_list_of_constraints([0 >= stu_to_proj[i,j]+stu_to_proj[antiprefs_dict_2[i],j]-1
                                  for j in range(num_projects) for i in antiprefs_dict_2.keys()])

    # IP constraint for GPA: less than 1/2 students with low gpa on a project
    gpa_sub_array = [indic-0.5 for indic in stu_gpa_indic]
    prob.add_list_of_constraints([0 >= sum([a*b for a,b in zip(gpa_sub_array,stu_to_proj[:,j])])
                                  for j in range(num_projects)])

    # constraint for students locked into a project
    for (token,project_name) in LOCKED_STUDENTS:
        # get student and project indices
        stu_index = token_index(token)
        proj_index = project_index(project_name)
        # constraint is that the student, project pair must equal 1
        prob.add_constraint(stu_to_proj[stu_index, proj_index] == 1)

    # constraint for students barred from a project
    for (token,project_name) in BARRED_STUDENTS:
        # get student and project indices
        stu_index = token_index(token)
        proj_index = project_index(project_name)
        # constraint is that the student, project pair must equal 0
        prob.add_constraint(stu_to_proj[stu_index,proj_index] == 0)

    # constraint for citizenship req projects
    for (token,project_name) in CITIZEN_BANS:
        # get student and project indices
        stu_index = token_index(token)
        proj_index = project_index(project_name)
        # constraint is that the student, project pair must equal 0
        prob.add_constraint(stu_to_proj[stu_index,proj_index] == 0)
        
    # objective function setup
    prob.set_objective('min',pic.sum([penalty1[i,j]*stu_to_proj[i,j] for i in range(num_students) for j in range(num_projects)]))

    # print the problem setup summary - suppressed
    # print(prob)
    # print('type:   ' + prob.type)
    # print('status: ' + prob.status)
    # prob.solve(solver='gurobi', verbose=False)
    # print('status: ' + prob.status)

    return prob, stu_to_proj #[prob.obj_value(), stu_to_proj]

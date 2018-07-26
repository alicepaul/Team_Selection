import picos as pic

def optimize_repeat(num_students, num_projects, penalties, MINSTAFF_PROJECTS, MAXSTAFF_PROJECTS,
                    project_names, antiprefs_dict_1, antiprefs_dict_2, stu_gpa_indic, GPA_COST, past_solns,
                    stu_visa, stu_other, citizenship_req_indices, visa_req_indices, LOCKED_STUDENTS,
                    BARRED_STUDENTS, tokens):

    # problem definition
    prob = pic.Problem(solver='gurobi')

    # convert list of list of penalties into 2D matrix for picos
    penalty1 = pic.new_param('mat', penalties)

    # add variable x_i,j matrix for students
    stu_to_proj = prob.add_variable('x', (num_students,num_projects), vtype='binary')

    # constraints setup
    # IP constraints for x (stu_to_proj)
    # sum of all entries x_ij over j (project allocated student count) should be between MINSTAFF and MAXSTAFF
    # for a given project; this is done using dictionaries initialized above
    prob.add_list_of_constraints([sum(stu_to_proj[:,j]) >= MINSTAFF_PROJECTS[project_names[j]] for j in range(num_projects)])
    prob.add_list_of_constraints([sum(stu_to_proj[:,j]) <= MAXSTAFF_PROJECTS[project_names[j]] for j in range(num_projects)])
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

    # IP constraint for citizens, visa holders, and other
    # citizens can access any project (hence no restrictions)
    # visa holders can access up to projects that require visas
    # other (aliens) can access only the projects that do not have citizenship or visa requirements

    # constraint for ctzn projects, that visa holder and alien/other students cannot join (set to 0)
    prob.add_list_of_constraints([stu_to_proj[stu_index,proj_index] == 0
                                  for stu_index in stu_visa for proj_index in citizenship_req_indices])
    prob.add_list_of_constraints([stu_to_proj[stu_index,proj_index] == 0
                                  for stu_index in stu_other for proj_index in citizenship_req_indices])

    # constraint for visa projects, that alien/other students cannot join (set to 0)
    prob.add_list_of_constraints([stu_to_proj[stu_index,proj_index] == 0
                                  for stu_index in stu_other for proj_index in visa_req_indices])

    # constraint for students locked into a project
    for key in LOCKED_STUDENTS.keys():
        # locked student token gives the index of which student
        stu_index = tokens.index(key)
        # project name gives the index of project
        proj_index = project_names.index(LOCKED_STUDENTS[key])
        # constraint is that the student, project pair must equal 1
        # note: this means that student preference is overridden so if student expresses non-5 preference
        # on a locked project, may result in changed optimality of outcomes or infeasibility
        prob.add_constraint(stu_to_proj[stu_index, proj_index] == 1)

    # constraint for students barred from a project
    for key in BARRED_STUDENTS.keys():
        # barred student token gives the index of which student
        stu_index = tokens.index(key)
        # project name gives the index of project
        proj_index = project_names.index(BARRED_STUDENTS[key])
        # constraint is that the student, project pair must equal 0
        # note: this means that student preference is overridden so if student expresses non-1 preference
        # on a locked project, may result in changed optimality of outcomes or infeasibility
        prob.add_constraint(stu_to_proj[stu_index,proj_index] == 0)

    # past solutions constraint
    for past in past_solns:
        pairs = []
        for i in range(num_students):
            for j in range(num_projects):
                if past.value[i, j] == 1:
                    pairs.append([i, j])
        prob.add_constraint(sum([stu_to_proj[i,j] for [i,j] in pairs]) <= num_students-1)

    # objective function setup
    prob.set_objective('min',pic.sum([penalty1[i,j]*stu_to_proj[i,j] for i in range(num_students) for j in range(num_projects)]))

    # print the problem setup summary - suppressed
    # print(prob)
    # print('type:   ' + prob.type)
    # print('status: ' + prob.status)
    prob.solve(solver='gurobi', verbose=False)
    # print('status: ' + prob.status)

    return [prob.obj_value(), stu_to_proj]

library(ompr)
library(ompr.roi)
library(ROI.plugin.glpk)
library(magrittr)

# Solves team assignment problem defined by file_proj and file_pers with staff constraints,
# user_constraints, and conflict constraints. Objective function for preferences set by pcosts
# Finds a diverse set of num_div solutions within gap_div of optimality 

optimizeTeams <- function(file_proj, file_pers, num_div, gap_div, user_constraints, pcosts){
  df_proj <- read.csv(file_proj)
  df_pers <- read.csv(file_pers)
  num_projects <- nrow(df_proj)
  num_people <- nrow(df_pers)
  
  # Create dictionaries from names to indices
  pers_index <- 1:num_people
  names(pers_index) <- df_pers[,'name']
  proj_index <- 1:num_projects
  names(proj_index) <- df_proj[,'project_name']
  
  # Create model and add in variables
  model <- MIPModel()
  model <- add_variable(model, x[i,j], i = 1:num_people, j = 1:num_projects, type='binary')
  
  # Add constraint that each person assigned to one team
  model <- add_constraint(model, sum_expr(x[i, j], j = 1:num_projects) == 1, i = 1:num_people)
  
  # If max_staff is a column, add that constraint
  if ('max_staff' %in% colnames(df_proj)){
    model <- add_constraint(model, sum_expr(x[i,j], i = 1:num_people) <= df_proj[j,'max_staff'], j = 1:num_projects)
  }
  
  # If min_staff is a column, add that constraint
  if ('min_staff' %in% colnames(df_proj)){
    model <- add_constraint(model, sum_expr(x[i,j], i = 1:num_people) >= df_proj[j,'min_staff'], j = 1:num_projects)
  }
  
  # If conflicts is a column, add those constraints
  if ('conflicts' %in% colnames(df_pers)){
    for (i in 1:num_people){
      if (is.na(df_pers[i,'conflicts'])==FALSE){
        name_list <- toString(df_pers[i,'conflicts'])
        if (grepl(',',name_list)){
          name_list <- strsplit(name_list,",")[[1]]
        }
        for (name in name_list){
          if (name %in% names(pers_index)){
            j <- pers_index[[name]]
            model <- add_constraint(model, x[i,k]+x[j,k]<=1, k = 1:num_projects)
          }
        }
      }
    }
  }
  
  # Add user-inputted constraints
  for (constraint in user_constraints){
    i <- pers_index[constraint$pers]
    j <- proj_index[constraint$proj]
    if (constraint$type == "on"){
      model <- add_constraint(model, x[i,j] == 1)
    }
    else{
      model <- add_constraint(model, x[i,j] == 0)
    }
  }
  
  # Set objective function based on preferences
  costs <- matrix(ncol=num_projects, nrow=num_people)
  for (i in 1:num_people){
    for (j in 1:num_projects){
      costs[i,j] <- pcosts[df_pers[i,toString(df_proj[j,"project_name"])]]
    }
  }
  model <- set_objective(model, sum_expr(costs[i,j]*x[i,j], i = 1:num_people, j = 1:num_projects), "min")
  result <- solve_model(model, with_ROI(solver = "glpk", verbose = FALSE))
  if (solver_status(result) == "infeasible"){
    result_list <- list("status"="infeasible")
    return(result_list)
  }
  
  # Solve and get optimal solution
  solution <- get_solution(result, x[i,j])
  soln_mat <- matrix(ncol=num_projects,nrow=num_people)
  for (k in 1:nrow(solution)){
    soln_mat[solution[k,'i'],solution[k,'j']] <- solution[k,'value']
  }
  
  df_team <- data.frame(matrix(ncol = 3, nrow = num_people))
  colnames(df_team) <- c("project","name","preference")
  k <- 1
  for (j in 1:num_projects){
    for (i in 1:num_people){
      if (soln_mat[i,j] == 1){
        df_team[k,"name"] <- toString(df_pers[i,"name"])
        df_team[k,"project"] <- toString(df_proj[j,"project_name"])
        df_team[k,"preference"] <- df_pers[i,toString(df_proj[j,"project_name"])]
        k <- k+1
      }
    }
  }
  
  # Now find diverse solutions within gap
  opt_value <- objective_value(result)
  max_obj <- (1+gap_div)*opt_value
  
  # First add constraint on objective function to be within gap
  model <- add_constraint(model, sum_expr(costs[i,j]*x[i,j], i = 1:num_people, j = 1:num_projects)<=max_obj)
  
  # New objective function will keep track of distance to previous solns
  div_costs <- soln_mat
  
  # We also ensure that we don't find the same solution again
  model <- add_constraint(model, sum_expr(soln_mat[i,j]*x[i,j], i = 1:num_people, j = 1:num_projects)<=num_people-1)
  
  # Save the most diverse set of solutions
  teams_list <- list()
  teams_list[[1]] <- df_team
  values_list <- list()
  values_list[[1]] <- opt_value
  solns_found <- 1
  continue <- solns_found < num_div
  while (continue){
    # Set objective function according to div_costs now
    model <- set_objective(model, sum_expr(div_costs[i,j]*x[i,j], i = 1:num_people, j = 1:num_projects), "min")
    result <- solve_model(model, with_ROI(solver = "glpk", verbose = FALSE))
    
    # Check if optimized and if we reached the solution limit
    if (solver_status(result) == "infeasible"){
      continue <- FALSE
      next
    }
    else{
      solns_found <- solns_found + 1
      if (solns_found >= num_div){
        continue <- FALSE
      }
    }
    # Update constraints and div_costs
    solution <- get_solution(result, x[i,j])
    soln_mat <- matrix(ncol=num_projects,nrow=num_people)
    for (k in 1:nrow(solution)){
      soln_mat[solution[k,'i'],solution[k,'j']] <- solution[k,'value']
    }
    div_costs <- div_costs + soln_mat
    model <- add_constraint(model, sum_expr(soln_mat[i,j]*x[i,j], i = 1:num_people, j = 1:num_projects)<=num_people-1)
    
    # Update stored solutions
    df_team <- data.frame(matrix(ncol = 3, nrow = num_people))
    obj_value <- 0
    colnames(df_team) <- c("project","name","preference")
    k <- 1
    for (j in 1:num_projects){
      for (i in 1:num_people){
        if (soln_mat[i,j] == 1){
          obj_value <- obj_value + costs[i,j]
          df_team[k,"name"] <- toString(df_pers[i,"name"])
          df_team[k,"project"] <- toString(df_proj[j,"project_name"])
          df_team[k,"preference"] <- df_pers[i,toString(df_proj[j,"project_name"])]
          k <- k+1
        }
      }
    }
    teams_list[[solns_found]] <- df_team
    values_list[[solns_found]] <- obj_value
  }
  return_list <- list("teams"=teams_list,"values"=values_list,"status"="opt")
  return(return_list)
}